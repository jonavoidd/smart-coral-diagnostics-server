from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.auth import require_role
from app.crud.user import get_all_admin
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.website_content import (
    WebsiteContentCreate,
    WebsiteContentUpdate,
    WebsiteContentOut,
)
from app.schemas.user import UserOut
from app.services.email_service import send_web_update_email_to_admins
from app.services.website_content import website_content_service

router = APIRouter()


@router.get("/id/{id}", response_model=WebsiteContentOut)
def select(id: UUID, db: Session = Depends(get_db)):
    return website_content_service.get_content(db, id)


@router.get("/", response_model=List[WebsiteContentOut])
def select_all(db: Session = Depends(get_db)):
    return website_content_service.get_all_contents(db)


@router.get("/section/{section}", response_model=Optional[List[WebsiteContentOut]])
def select_content_by_section(section: str, db: Session = Depends(get_db)):
    content = website_content_service.get_content_by_section(db, section)
    if content is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no content found"
        )
    return content


@router.post("/")
def store(
    payload: WebsiteContentCreate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN]),
    ),
):
    return website_content_service.insert_content(db, payload, current_user)


@router.patch("/id/{id}")
async def update(
    id: UUID,
    payload: WebsiteContentUpdate,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])
    ),
):
    all_admin = get_all_admin(db)
    admin_list = all_admin if isinstance(all_admin, list) else list(all_admin)

    if not admin_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no admin found"
        )

    for admin in admin_list:
        name = f"{admin.first_name} {admin.last_name}"
        success = await send_web_update_email_to_admins(
            emails=admin.email, name=name, title=payload.title, content=payload.content
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error sending email to {admin.email}",
            )

    return website_content_service.update_content(db, id, payload, current_user)


@router.delete("/id/{id}")
def delete(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.SUPER_ADMIN, UserRole.ADMIN])
    ),
):
    return website_content_service.remove_content(db, id, current_user)
