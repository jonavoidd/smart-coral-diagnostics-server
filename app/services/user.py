from fastapi import Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.db.connection import get_db
from app.crud import user as user_crud
from app.schemas.user import CreateUser, UpdateUser, UserOut


def create_user_service(user_data: CreateUser, db: Session = Depends(get_db)):
    user_crud.create_user(db, **user_data.model_dump())
    return {"message": "user successfully created"}


def get_user_by_email_service(email: str, db: Session = Depends(get_db)) -> UserOut:
    user_details = user_crud.get_user_by_email(db, email)
    return user_details


def get_user_by_id_service(id: UUID, db: Session = Depends(get_db)) -> UserOut:
    user_details = user_crud.get_user_by_id(db, id)
    return user_details


def get_all_users_service(db: Session = Depends(get_db)) -> list[UserOut]:
    return user_crud.get_all_users(db)


def update_user_details_service(
    id: UUID, update_data: UpdateUser, db: Session = Depends(get_db)
):
    user_crud.update_user_details(db, id, **update_data.model_dump())
    return {"message": "successfully updated user details"}


def delete_user_service(id: UUID, db: Session = Depends(get_db)):
    user_crud.delete_user(db, id)
    return {"message": "user successfully deleted"}
