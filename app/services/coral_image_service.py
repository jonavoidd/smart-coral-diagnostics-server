import logging
import markdown

from datetime import datetime, timezone
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import uuid4, UUID

from app.core.supabase_client import supabase
from app.crud.coral_images import (
    save_analysis_results,
    store_coral_image,
    get_all_images,
    get_all_images_with_results,
    get_coral_location,
    get_images_by_user,
    get_image_by_id,
    delete_image,
    delete_selected_images,
    log_analytics_event,
)
from app.schemas.audit_trail import CreateAuditTrail
from app.schemas.coral_image import CoralImageCreate, CoralImageOut
from app.schemas.user import UserOut
from app.services.ai_inference import run_inference, run_llm_inference
from app.services.audit_trail_service import audit_trail_service

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"

# ALLOWED_IMAGE_TYPE = ["image/jpg", "image/jpeg", "image/png", "image/webp", "image/gif"]


def upload_image_to_supabase_service(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    latitude: float,
    longitude: float,
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
        file_url=file_url,
        filename=unique_filename,
        original_upload_name=original_filename,
        uploaded_at=datetime.now(timezone.utc),
        processed=True,
        latitude=latitude,
        longitude=longitude,
    )
    stored_image = store_coral_image(db, image_data)

    try:
        result_data = run_inference(file_url)
        analysis_result = save_analysis_results(db, stored_image.id, result_data)

        llm_response = run_llm_inference(
            image_data.latitude,
            image_data.longitude,
            result_data["classification_labels"],
        )

        try:
            llm_res_cleaned = llm_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            llm_res_cleaned = "No explanation cound be generated at this time."

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

        return {
            "message": "image processed successfully",
            "result": {
                "label": result_data["classification_labels"],
                "confidence": result_data["confidence_score"],
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
            detail="gettin coral data failed",
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


def delete_single_image_service(db: Session, id: UUID, user: UserOut):
    image = get_image_by_id(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    filename = image.filename

    try:
        supabase.storage.from_("coral-images").remove([filename])
    except Exception as e:
        logger.error(f"{LOG_MSG} error deleting image from supabase storage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deleting image from storage failed",
        )

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
