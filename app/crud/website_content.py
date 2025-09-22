import logging

from sqlalchemy import asc, select, update, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.models.website_content import WebsiteContent
from app.schemas.website_content import (
    WebsiteContentCreate,
    WebsiteContentOut,
    WebsiteContentUpdate,
)

logger = logging.getLogger(__name__)
LOG_MSG = "Crud:"


def select_content(db: Session, id: UUID) -> Optional[WebsiteContentOut]:
    query = select(WebsiteContent).where(WebsiteContent.id == id)

    try:
        result = db.execute(query)
        content = result.scalar_one_or_none()

        return content
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error reading content: {str(e)}")
        return None


def select_all_content(db: Session) -> Optional[List[WebsiteContentOut]]:
    try:
        content = db.query(WebsiteContent).all()
        return content
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting all content: {str(e)}")
        return None


def select_content_by_section(
    db: Session, section: str
) -> Optional[List[WebsiteContentOut]]:
    query = (
        select(WebsiteContent)
        .where(WebsiteContent.section == section)
        .order_by(asc(WebsiteContent.created_at))
    )

    try:
        result = db.execute(query)
        contents = result.scalars().all()

        return [WebsiteContentOut.model_validate(c) for c in contents]
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error reading content: {str(e)}")
        return None


def store_content(db: Session, payload: WebsiteContentCreate):
    content = WebsiteContent(**payload.model_dump())

    try:
        db.add(content)
        db.commit()
        db.refresh(content)

        return content
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error storing content: {str(e)}")
        raise


def update_content(db: Session, id: UUID, payload: WebsiteContentUpdate):
    new_data = payload.model_dump(exclude_unset=True)
    query = (
        update(WebsiteContent)
        .where(WebsiteContent.id == id)
        .values(**new_data)
        .returning(WebsiteContent)
    )

    try:
        result = db.execute(query)
        db.commit()

        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error updating content: {str(e)}")
        raise


def delete_content(db: Session, id: UUID):
    query = delete(WebsiteContent).where(WebsiteContent.id == id)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting content: {str(e)}")
        raise
