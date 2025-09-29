from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.user import CreateUser, UserOut, UpdateUser
from app.services.admin_service import super_admin
from app.services.user_service import user_service


router = APIRouter()


@router.post("/")
def add_admin(
    payload: CreateUser,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    payload.role = UserRole.ADMIN

    return super_admin.create_admin(db, payload, current_user)


@router.patch("/{id}", response_model=UserOut)
def update_user_details(
    id: UUID,
    payload: UpdateUser,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    updated_user = user_service.update_user_details_service(
        db, id, payload, current_user
    )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="update failed"
        )
    return updated_user


@router.delete("/{id}")
def delete_admin(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.SUPER_ADMIN])),
):
    return super_admin.remove_admin(db, id, current_user)
