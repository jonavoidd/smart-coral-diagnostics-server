import logging
import markdown

from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import uuid4, UUID

from app.core.supabase_client import supabase
from app.crud.archived_image import store_archived_data
from app.crud.coral_images import (
    save_analysis_results,
    store_coral_image,
    get_all_images,
    get_all_images_with_results,
    get_public_images_with_results,
    get_coral_location,
    get_images_by_user,
    get_all_images_by_user,
    get_image_by_id,
    update_image_details,
    change_coral_image_public_status,
    change_all_user_coral_image_status,
    delete_image,
    delete_selected_images,
    log_analytics_event,
)
from app.crud.user import get_user_by_id
from app.schemas.archived_image import CreateArchivedImage
from app.schemas.audit_trail import CreateAuditTrail
from app.schemas.coral_image import CoralImageCreate, CoralImageOut, UpdateCoralImage
from app.schemas.user import UserOut
from app.services.ai_inference import run_inference, run_llm_inference
from app.services.audit_trail_service import audit_trail_service
from app.services.bleaching_alert_service import bleaching_alert_service

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"

# ALLOWED_IMAGE_TYPE = ["image/jpg", "image/jpeg", "image/png", "image/webp", "image/gif"]


def upload_image_to_supabase_service(
    db: Session,
    file_bytes: bytes,
    name: str,
    original_filename: str,
    latitude: float,
    longitude: float,
    water_temperature: str,
    water_depth: float,
    observation_date: datetime,
    is_public: bool,
    user: UserOut,
):
    unique_filename = f"{uuid4()}_{original_filename}"

    try:
        supabase.storage.from_("coral-images").upload(unique_filename, file_bytes)
    except Exception as e:
        logger.error(f"{LOG_MSG} supabase upload failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="image upload to supabase failed",
        )

    file_url = supabase.storage.from_("coral-images").get_public_url(unique_filename)

    image_data = CoralImageCreate(
        user_id=user.id,
        name=name,
        file_url=file_url,
        filename=unique_filename,
        original_upload_name=original_filename,
        processed=True,
        latitude=latitude,
        longitude=longitude,
        water_temperature=water_temperature,
        water_depth=water_depth,
        is_public=is_public,
        observatiton_date=observation_date,
        uploaded_at=datetime.now(timezone.utc),
    )
    stored_image = store_coral_image(db, image_data)

    try:
        result_data = run_inference(file_url)

        llm_response = run_llm_inference(
            latitude=image_data.latitude,
            longitude=image_data.longitude,
            classification=result_data["classification_labels"],
            bleaching_percentage=result_data["bleaching_percentage"],
            water_temp=water_temperature,
            water_depth=water_depth,
            observation_date=observation_date,
        )

        try:
            llm_res_cleaned = llm_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            llm_res_cleaned = "No explanation could be generated at this time."

        split_marker = "Recommended Actions:"
        if split_marker in llm_res_cleaned:
            description_text, recommended_text = llm_res_cleaned.split(split_marker, 1)
        else:
            description_text = llm_res_cleaned
            recommended_text = ""

        description_html = markdown.markdown(description_text.strip())

        bullet_lines = [
            line.strip()[2:].strip()
            for line in recommended_text.splitlines()
            if line.strip().startswith("- ")
        ]
        recommended_html = (
            "<ul>" + "".join(f"<li>{line}" for line in bullet_lines) + "</ul>"
            if bullet_lines
            else ""
        )

        analysis_result = save_analysis_results(
            db, stored_image.id, result_data, description_text, recommended_text
        )

        log_analytics_event(
            db,
            stored_image.user_id,
            event_type="coral_inference",
            details={
                "image_id": str(stored_image.id),
                "result_id": str(analysis_result.id),
                "label": result_data["classification_labels"],
            },
        )

        audit = CreateAuditTrail(
            actor_id=user.id,
            actor_role=user.role,
            action="AI Analysis & Upload to Storage",
            resource_type="coral image",
            description=f"user with the email '{user.email}' used the service to analyze a coral image",
        )
        audit_trail_service.insert_audit(db, audit)

        if (
            result_data["classification_labels"]
            in [
                "polar_white_bleaching",
                "polar white bleaching",
                "slight_pale_bleaching",
                "slight pale bleaching",
                "very_pale_bleaching",
                "very pale bleaching",
            ]
            and result_data["bleaching_percentage"] >= 30.0
        ):
            try:
                bleaching_alert_service.generate_alerts(
                    db,
                    min_bleached_count=200,
                    cluster_radius_km=50.0,
                    regenerate_existing=False,
                )
                logger.info(
                    f"{LOG_MSG} checked/updated bleaching alerts for new images."
                )
            except Exception as e:
                logger.warning(f"{LOG_MSG} failed to udpate alerts: {str(e)}")

        return {
            "message": "image processed successfully",
            "result": {
                "label": result_data["classification_labels"],
                "confidence": result_data["confidence_score"],
                "bleaching_percentage": result_data["bleaching_percentage"],
                "model_version": result_data["model_version"],
            },
            "image_id": stored_image.id,
            "result_id": analysis_result.id,
            "stored_image": stored_image,
            "llm_response_description": description_text.strip(),
            "llm_response_recommended": recommended_text.strip(),
            "llm_response_description_html": description_html,
            "llm_response_recommended_html": recommended_html,
            # "stored_image": CoralImageOut.model_validate(stored_image),
        }
    except Exception as e:
        logger.error(f"{LOG_MSG} error running inference on image: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="running inference on image failed",
        )


def get_all_images_service(db: Session):
    try:
        all_images = get_all_images(db)

        if not all_images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no image found"
            )

        return all_images
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting all images: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting images failed",
        )


def get_all_coral_data(db: Session) -> List[CoralImageOut]:
    try:
        all_data = get_all_images_with_results(db)

        if not all_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no data found"
            )

        return all_data
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting all coral data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting coral data failed.",
        )


def get_public_coral_data(db: Session) -> List[CoralImageOut]:
    try:
        data = get_public_images_with_results(db)

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no data found"
            )

        return data
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting all public data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting public coral data failed.",
        )


def get_all_coral_locations(db: Session):
    try:
        return get_coral_location(db)
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting all coral locations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting coral locations failed",
        )


def get_image_for_user_service(db: Session, id: UUID):
    try:
        image_by_user = get_images_by_user(db, id)

        if not image_by_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="images by user not found"
            )

        return image_by_user
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting image by user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting images failed",
        )


def get_all_images_by_user_service(
    db: Session, id: UUID
) -> Optional[List[CoralImageOut]]:
    try:
        images = get_all_images_by_user(db, id)

        if not images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no image by user found"
            )

        return images
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting images uploaded by user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get all images by user",
        )


def get_single_image_service(db: Session, id: UUID):
    try:
        image = get_image_by_id(db, id)

        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="image not found"
            )

        return image
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting single image by id: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="getting image failed",
        )


def edit_image_details(db: Session, id: UUID, payload: UpdateCoralImage):
    try:
        result = update_image_details(db, id, payload)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="image not found"
            )
        return result
    except Exception as e:
        logger.error(f"{LOG_MSG} error updating image details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to update image details",
        )


def change_coral_image_publicity(db: Session, id: UUID, is_public: bool):
    try:
        existing = get_image_by_id(db, id)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="image not found"
            )

        return change_coral_image_public_status(db, id, is_public)
    except Exception as e:
        logger.error(f"{LOG_MSG} error updating image publicity status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to update image publicity status",
        )


def change_all_user_coral_image_publicity_status(
    db: Session, user_id: UUID, is_public: bool
):
    try:
        existing_user = get_user_by_id(db, user_id)

        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
            )

        return change_all_user_coral_image_status(db, user_id, is_public)
    except Exception as e:
        logger.error(
            f"{LOG_MSG} error updating all image publicity status uploaded by user: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to change all coral image publicity status.",
        )


def delete_single_image_service(db: Session, id: UUID, user: UserOut):
    image = get_image_by_id(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    filename = image.filename

    try:
        analysis = image.analysis_results[0] if image.analysis_results else None

        archived_payload = CreateArchivedImage(
            name=image.name,
            file_url=image.file_url,
            filename=image.filename,
            original_upload_name=image.original_upload_name,
            latitude=image.latitude,
            longitude=image.longitude,
            water_temperature=image.water_temperature,
            water_depth=image.water_depth,
            uploaded_at=image.uploaded_at,
            confidence_score=analysis.confidence_score if analysis else None,
            bleaching_percentage=analysis.bleaching_percentage if analysis else None,
            classification_labels=analysis.classification_labels if analysis else None,
            model_version=analysis.model_version if analysis else None,
            description=analysis.model_version if analysis else None,
            recommendations=analysis.recommendations if analysis else None,
        )
        store_archived_data(db, archived_payload)
    except Exception as e:
        logger.error(f"{LOG_MSG} error archiving data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"error archiving: {str(e)}",
        )

    # try:
    #     supabase.storage.from_("coral-images").remove([filename])
    # except Exception as e:
    #     logger.error(f"{LOG_MSG} error deleting image from supabase storage: {str(e)}")
    #     raise HTTPException(
    #         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    #         detail="Deleting image from storage failed",
    #     )

    audit = CreateAuditTrail(
        actor_id=user.id,
        actor_role=user.role,
        action="DELETE",
        resource_type="coral image",
        resource_id=id,
        description=f"user with the email '{user.email}' deleted the selected image with the id: '{id}'",
    )
    audit_trail_service.insert_audit(db, audit)

    try:
        return delete_image(db, id)
    except Exception as e:
        logger.error(f"{LOG_MSG} error deleting image from db: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="deleting image from db failed",
        )


def delete_multiple_images_service(db: Session, ids: List[UUID], user: UserOut) -> int:
    images = [get_image_by_id(db, id) for id in ids]
    filenames = [img.filename for img in images if img]

    try:
        supabase.storage.from_("coral-images").remove(filenames)
    except Exception as e:
        logger.error(
            f"{LOG_MSG} error in deleting images from supabase storage: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deleting images from storage failed",
        )

    audit = CreateAuditTrail(
        actor_id=user.id,
        actor_role=user.role,
        action="DELETE",
        resource_type="coral image",
        description=f"user with the email '{user.email}' deleted the multiple images",
    )
    audit_trail_service.insert_audit(db, audit)

    try:
        return delete_selected_images(db, ids)
    except Exception as e:
        logger.error(f"{LOG_MSG} error deleting images from db: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="deleting images from db failed",
        )
