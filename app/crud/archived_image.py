import logging

from fastapi import HTTPException, status
from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.models.archived_images import ArchivedImages
from app.schemas.archived_image import ArchivedImageOut, CreateArchivedImage

logger = logging.getLogger(__name__)
LOG_MSG = "CRUD:"


def select_archived_by_id(db: Session, id: UUID) -> Optional[ArchivedImageOut]:
    pass


def select_archived_data(db: Session) -> Optional[List[ArchivedImages]]:
    try:
        data = db.query(ArchivedImages).all()
        return data
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error reading archived data: {str(e)}")
        return None


def store_archived_data(db: Session, payload: CreateArchivedImage) -> ArchivedImageOut:
    data = ArchivedImages(**payload.model_dump())

    try:
        db.add(data)
        db.commit()
        db.refresh(data)

        return data
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error storing data into archive: {str(e)}")
        raise


def delete_archived_data(db: Session, id: UUID):
    query = delete(ArchivedImages).where(ArchivedImages.id == id)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting archived data: {str(e)}")
        raise
