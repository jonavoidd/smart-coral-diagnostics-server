import logging
import os

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
    get_images_by_user,
    get_image_by_id,
    delete_image,
    delete_selected_images,
    log_analytics_event,
)
from app.schemas.coral_image import CoralImageCreate, CoralImageOut
from app.services.ai_inference import run_inference

logger = logging.getLogger(__name__)
LOG_SMG = "Service:"

ALLOWED_IMAGE_TYPE = ["image/jpeg", "image/png", "image/webp", "image/gif"]


def upload_image_to_supabase_service(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    user_id: UUID,
    latitude: float,
    longitude: float,
):
    content_type = "image/jpeg"

    if content_type not in ALLOWED_IMAGE_TYPE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="invalid image type"
        )

    unique_filename = f"{uuid4()}_{original_filename}"

    try:
        supabase.storage.from_("coral-images").upload(unique_filename, file_bytes)
    except Exception as e:
        logger.error(f"{LOG_SMG} supabase upload failed")
        raise

    file_url = supabase.storage.from_("coral-images").get_public_url(unique_filename)

    image_data = CoralImageCreate(
        user_id=user_id,
        file_url=file_url,
        filename=unique_filename,
        original_upload_name=original_filename,
        uploaded_at=datetime.now(timezone.utc),
        processed=True,
        latitude=latitude,
        longitude=longitude,
    )
    stored_image = store_coral_image(db, image_data)

    result_data = run_inference(file_url)
    analysis_result = save_analysis_results(db, stored_image.id, result_data)

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
        # "stored_image": CoralImageOut.model_validate(stored_image),
    }


def get_all_images_service(db: Session):
    return get_all_images(db)


def get_image_for_user_service(db: Session, id: UUID):
    return get_images_by_user(db, id)


def get_single_image_service(db: Session, id: UUID):
    return get_image_by_id(db, id)


def delete_single_image_service(db: Session, id: UUID):
    image = get_image_by_id(db, id)
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    filename = image.filename

    try:
        supabase.storage.from_("coral-images").remove([filename])
    except Exception as e:
        logger.error(f"{LOG_SMG} error deleting image from supabase storage: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deleting image from storage failed",
        )

    return delete_image(db, id)


def delete_multiple_images_service(db: Session, ids: List[UUID]) -> int:
    images = [get_image_by_id(db, id) for id in ids]
    filenames = [img.filename for img in images if img]

    try:
        supabase.storage.from_("coral-image").remove(filenames)
    except Exception as e:
        logger.error(
            f"{LOG_SMG} error in deleting images from supabase storage: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Deleting images from storage failed",
        )

    return delete_selected_images(db, ids)
