import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from uuid import UUID

from app.crud.website_content import (
    select_content,
    select_all_content,
    store_content,
    update_content as update,
    delete_content,
)
from app.schemas.website_content import (
    WebsiteContentCreate,
    WebsiteContentOut,
    WebsiteContentUpdate,
)

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"


class WebsiteContentService:
    def get_content(self, db: Session, id: UUID) -> Optional[WebsiteContentOut]:
        try:
            content = select_content(db, id)

            if not content:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="content not found"
                )

            return content
        except Exception as e:
            logger.error(f"{LOG_MSG} error getting content: {str(e)}")
            return None

    def get_all_contents(self, db: Session) -> Optional[List[WebsiteContentOut]]:
        try:
            all_content = select_all_content(db)

            if not all_content:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="error getting all contents",
                )

            return all_content
        except Exception as e:
            logger.error(f"{LOG_MSG} error getting all content: {str(e)}")
            return None

    def insert_content(
        self, db: Session, payload: WebsiteContentCreate
    ) -> Dict[str, str]:
        try:
            content = store_content(db, payload)
            return {"message": "successfully inserted new content", "data": content}
        except Exception as e:
            logger.error(f"{LOG_MSG} error adding new content: {str(e)}")
            return None

    def update_content(
        self, db: Session, id: UUID, payload: WebsiteContentUpdate
    ) -> Dict[str, str]:
        try:
            update(db, id, payload)
            return {"message": "successfully updated content data"}
        except Exception as e:
            logger.error(f"{LOG_MSG} error updating content: {str(e)}")
            return None

    def remove_content(self, db: Session, id: UUID) -> Dict[str, str]:
        try:
            delete_content(db, id)
            return {"message": "successfully deleted content data"}
        except Exception as e:
            logger.error(f"{LOG_MSG} error adding new content: {str(e)}")
            return None


website_content_service = WebsiteContentService()
