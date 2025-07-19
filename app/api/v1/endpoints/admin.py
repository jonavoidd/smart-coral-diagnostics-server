from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.user import CreateUser, UserOut
from app.services.admin_service import super_admin


router = APIRouter()


@router.post("/", response_model=UserOut)
def add_admin(
    payload: CreateUser,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    payload.role = UserRole.ADMIN

    return super_admin.create_admin(db, payload, current_user)


@router.delete("/{id}")
def delete_admin(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    return super_admin.remove_admin(db, id, current_user)
