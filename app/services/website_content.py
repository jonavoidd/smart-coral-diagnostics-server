import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from uuid import UUID

from app.core.auth import require_role
from app.crud.website_content import (
    select_content,
    select_all_content,
    store_content,
    update_content as update,
    delete_content,
)
from app.models.users import UserRole
from app.schemas.audit_trail import CreateAuditTrail
from app.schemas.user import UserOut
from app.schemas.website_content import (
    WebsiteContentCreate,
    WebsiteContentOut,
    WebsiteContentUpdate,
)
from app.services.audit_trail_service import audit_trail_service

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"
RSC_TYPE = "website content"


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
        self, db: Session, payload: WebsiteContentCreate, user: UserOut
    ) -> Dict[str, str]:
        try:
            content = store_content(db, payload)

            audit = CreateAuditTrail(
                actor_id=user.id,
                actor_role=user.role,
                action="CREATE",
                resource_type=RSC_TYPE,
                description=f"user with the email '{user.email}' created a new website content",
            )
            audit_trail_service.insert_audit(db, audit)

            return {"message": "successfully inserted new content", "data": content}
        except Exception as e:
            logger.error(f"{LOG_MSG} error adding new content: {str(e)}")
            return None

    def update_content(
        self, db: Session, id: UUID, payload: WebsiteContentUpdate, user: UserOut
    ) -> Dict[str, str]:
        try:
            update(db, id, payload)

            audit = CreateAuditTrail(
                actor_id=user.id,
                actor_role=user.role,
                action="UPDATE",
                resource_type=RSC_TYPE,
                description=f"user with the email '{user.email}' updated the website content with the id '{id}'",
            )
            audit_trail_service.insert_audit(db, audit)

            return {"message": "successfully updated content data"}
        except Exception as e:
            logger.error(f"{LOG_MSG} error updating content: {str(e)}")
            return None

    def remove_content(self, db: Session, id: UUID, user: UserOut) -> Dict[str, str]:
        try:
            delete_content(db, id)

            audit = CreateAuditTrail(
                actor_id=user.id,
                actor_role=user.role,
                action="DELETE",
                resource_type=RSC_TYPE,
                description=f"user with the email '{user.email}' deleted the website content with the id '{id}'",
            )
            audit_trail_service.insert_audit(db, audit)

            return {"message": "successfully deleted content data"}
        except Exception as e:
            logger.error(f"{LOG_MSG} error adding new content: {str(e)}")
            return None


website_content_service = WebsiteContentService()
