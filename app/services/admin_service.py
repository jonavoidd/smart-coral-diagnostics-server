from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import Hasher
from app.crud.user import create_user, delete_user
from app.schemas.user import CreateUser


class SuperAdmin:
    def create_admin(self, db: Session, payload: CreateUser):
        hashed_password = Hasher.hash_password(payload.password)
        user = create_user(db, payload, hashed_password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error creating new admin",
            )
        return {"message": "admin successfully created", "user": user}

    def remove_admin(self, db: Session, id: UUID):
        deleted = delete_user(db, id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
            )
        return {"message": f"deleted user with id {id}"}


super_admin = SuperAdmin()
