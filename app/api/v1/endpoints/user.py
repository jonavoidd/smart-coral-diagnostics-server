from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.db.connection import get_db
from app.schemas.user import CreateUser, UserOut, UpdateUser
from app.services import user as user_service

router = APIRouter()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user: CreateUser, db: Session = Depends(get_db)):
    return user_service.create_user_service(user, db)


@router.get("/email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_email_service(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/id/{id}", response_model=UserOut)
def get_user_by_id(id: UUID, db: Session = Depends(get_db)):
    user = user_service.get_user_by_id_service(id, db)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    return user_service.get_all_users_service(db)


@router.patch("/{id}", response_model=UserOut)
def update_user_details(
    id: UUID, update_data: UpdateUser, db: Session = Depends(get_db)
):
    user_update = user_service.update_user_details_service(id, update_data, db)
    if not user_update:
        raise HTTPException(status_code=400, detail="update failed")
    return user_update


@router.delete("/")
def delete_user(id: UUID, db: Session = Depends(get_db)):
    user_delete = user_service.delete_user_service(id, db)
    if not user_delete:
        raise HTTPException(status_code=400, detail="delete failed")
    return user_delete
