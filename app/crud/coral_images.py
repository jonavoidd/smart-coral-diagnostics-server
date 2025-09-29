import logging

from fastapi import HTTPException, status
from sqlalchemy import select, delete, update, and_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from typing import Dict, List, Optional
from uuid import UUID

from app.models.analysis_results import AnalysisResult
from app.models.analytics_events import AnalyticsEvent
from app.models.coral_images import CoralImages
from app.schemas.coral_image import (
    CoralImageCreate,
    CoralImageLocation,
    CoralImageOut,
    UpdateCoralImage,
)

logger = logging.getLogger(__name__)
LOG_MSG = "CRUD:"


def store_coral_image(db: Session, data: CoralImageCreate) -> Optional[CoralImages]:
    db_image = CoralImages(**data.model_dump())

    try:
        db.add(db_image)
        db.commit()
        db.refresh(db_image)

        return db_image
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error saving image to db: {str(e)}")
        return None


def save_analysis_results(
    db: Session,
    image_id: str,
    result_data: Dict,
    description: str,
    recommendations: str,
) -> AnalysisResult:
    image = AnalysisResult(
        image_id=image_id,
        confidence_score=result_data["confidence_score"],
        bleaching_percentage=result_data["bleaching_percentage"],
        classification_labels=result_data["classification_labels"],
        bounding_boxes=result_data["bounding_boxes"],
        model_version=result_data["model_version"],
        analysis_duration=result_data["analysis_duration"],
        description=description,
        recommendations=recommendations,
    )

    try:
        db.add(image)
        db.commit()
        db.refresh(image)

        return image
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error saving results to db: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to save analysis result to db",
        )


def log_analytics_event(
    db: Session, user_id: UUID, event_type: str, details: str
) -> AnalyticsEvent:
    event = AnalyticsEvent(user_id=user_id, event_type=event_type, details=details)

    try:
        db.add(event)
        db.commit()
        db.refresh(event)

        return event
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error saving analytics event to db: {str(e)}")
        return None


def get_all_images(db: Session) -> List[CoralImages]:
    try:
        query = select(CoralImages)
        result = db.execute(query).scalars().all()

        return result
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error gettings images: {str(e)}")
        return None


def get_all_images_with_results(db: Session) -> Optional[List[CoralImageOut]]:
    try:
        images = (
            db.query(CoralImages)
            .options(
                joinedload(CoralImages.user), joinedload(CoralImages.analysis_results)
            )
            .all()
        )

        filtered_images = [
            img
            for img in images
            if any(
                result.confidence_score is not None and result.confidence_score > 0.50
                for result in img.analysis_results
            )
        ]

        return filtered_images
        # return [CoralImageOut.model_validate(img) for img in filtered_images]
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting coral data: {str(e)}")
        return None


def get_public_images_with_results(db: Session) -> Optional[List[CoralImageOut]]:
    try:
        images = (
            db.query(CoralImages)
            .where(CoralImages.is_public == True)
            .options(
                joinedload(CoralImages.user), joinedload(CoralImages.analysis_results)
            )
            .all()
        )

        filtered_images = [
            img
            for img in images
            if any(
                result.confidence_score is not None and result.confidence_score > 0.50
                for result in img.analysis_results
            )
        ]

        return filtered_images
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting public coral data: {str(e)}")
        return None


def get_coral_location(db: Session) -> List[CoralImageLocation] | None:
    try:
        query = select(CoralImages.latitude, CoralImages.longitude)
        result = db.execute(query).all()

        locations = [
            CoralImageLocation(latitude=lat, longitude=lon) for lat, lon in result
        ]

        return locations
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting locations: {str(e)}")
        return None


def get_images_by_user(db: Session, id: UUID) -> Optional[List[CoralImages]]:
    try:
        query = select(CoralImages).where(CoralImages.user_id == id)
        result = db.execute(query).scalars().all()

        filtered_images = [
            img
            for img in result
            if any(
                results.confidence_score is not None and results.confidence_score > 0.50
                for results in img.analysis_results
            )
        ]

        return filtered_images
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting images: {str(e)}")
        return None


def get_all_images_by_user(db: Session, id: UUID) -> Optional[List[CoralImages]]:
    try:
        query = select(CoralImages).where(CoralImages.user_id == id)
        result = db.execute(query).scalars().all()

        return result
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting all images by user: {str(e)}")
        return None


def get_image_by_id(db: Session, id: UUID) -> CoralImages:
    try:
        query = select(CoralImages).where(CoralImages.id == id)
        result = db.execute(query).scalars().first()

        return result
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting images: {str(e)}")
        return None


def update_image_details(
    db: Session, id: UUID, payload: UpdateCoralImage
) -> Optional[CoralImages]:
    new_data = payload.model_dump(exclude_unset=True)
    query = (
        update(CoralImages)
        .where(CoralImages.id == id)
        .values(**new_data)
        .returning(CoralImages)
    )

    try:
        result = db.execute(query)
        db.commit()

        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error updating coral image data: {str(e)}")
        raise


def change_coral_image_public_status(db: Session, id: UUID, status: bool) -> bool:
    query = update(CoralImages).where(CoralImages.id == id).values(is_public=status)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error updating image public status")
        raise


def change_all_user_coral_image_status(db: Session, user_id: UUID, status: bool) -> int:
    query = (
        update(CoralImages)
        .where(and_(CoralImages.user_id == user_id, CoralImages.is_public != status))
        .values(is_public=status)
    )

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(
            f"{LOG_MSG} error updating all coral image publicity uploaded by user."
        )
        raise


def delete_image(db: Session, id: UUID):
    query = delete(CoralImages).where(CoralImages.id == id)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting image")
        raise


def delete_selected_images(db: Session, ids: List[UUID]) -> int:
    query = delete(CoralImages).where(CoralImages.id.in_(ids))

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting images")
        return 0
