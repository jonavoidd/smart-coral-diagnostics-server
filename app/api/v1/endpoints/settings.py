import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.connection import get_db
from app.schemas.settings import Settings
from app.services.coral_image_service import (
    change_all_user_coral_image_publicity_status,
    get_all_images_by_user_service,
)
from app.services.user_service import user_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{id}")
def get_settings(id: UUID, db: Session = Depends(get_db)):
    images = get_all_images_by_user_service(db, id)

    if not images:
        logger.warning(f"no image posted by the user with given id is found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no images found"
        )

    is_public_true = sum(img.is_public for img in images)
    is_public_false = len(images) - is_public_true

    majority_is_public = is_public_true > is_public_false

    return {"is_public": majority_is_public}


@router.patch("/u/{id}")
def change_settings(id: UUID, payload: Settings, db: Session = Depends(get_db)):
    try:
        if payload.is_public is not None:
            return change_all_user_coral_image_publicity_status(
                db, user_id=id, is_public=payload.is_public
            )
    except Exception as e:
        logger.error(f"Endpoint: error changing user settings: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to change user settings.",
        )
