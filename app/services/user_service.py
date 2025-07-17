import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from uuid import UUID

from app.core.security import Hasher
from app.crud import user as user_crud
from app.db.connection import get_db
from app.schemas.user import CreateUser, UpdateUser, UserOut
from app.schemas.password_reset import PasswordChangeRequest
from app.services.email_service import email_service


logger = logging.getLogger(__name__)
LOG_MSG = "Service:"


class UserService:
    def create_user_service(self, user_data: CreateUser, db: Session) -> Dict[str, str]:
        """
        Creates a new user in the database.

        Args:
            user_data (CreateUser): Data required to create a user.
            db (Session): SQLAlchemy database session.

        Returns:
            dict: Success message indicating the user was created.
        """

        user_crud.create_user(db, **user_data.model_dump())
        return {"message": "Service: user successfully created"}

    def get_user_by_email_service(self, email: str, db: Session) -> UserOut:
        """
        Retrieves user details using the provided email.

        Args:
            email (str): The email of the user to retrieve.
            db (Session): SQLAlchemy database session.

        Returns:
            UserOut: The user details.
        """

        user_details = user_crud.get_user_by_email(db, email)
        return user_details

    def get_user_by_id_service(self, id: UUID, db: Session) -> UserOut:
        """
        Retrieves user details by user ID.

        Args:
            id (UUID): The UUID of the user.
            db (Session): SQLAlchemy database session.

        Returns:
            UserOut: The user details.
        """

        user_details = user_crud.get_user_by_id(db, id)
        return user_details

    def get_all_users_service(self, db: Session) -> List[UserOut]:
        """
        Retrieves a list of all users.

        Args:
            db (Session): SQLAlchemy database session.

        Returns:
            list[UserOut]: A list of all users.
        """

        return user_crud.get_all_users(db)

    def get_all_admin_service(self, db: Session) -> List[UserOut]:
        all_admin = user_crud.get_all_admin(db)

        if not all_admin:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no admin found"
            )

        return all_admin

    def update_user_details_service(
        self, id: UUID, update_data: UpdateUser, db: Session
    ) -> Dict[str, str]:
        """
        Updates user details for a given user ID.

        Args:
            id (UUID): The UUID of the user to update.
            update_data (UpdateUser): Fields to update.
            db (Session): SQLAlchemy database session.

        Returns:
            dict: Success message indicating the user details were updated.
        """

        user_crud.update_user_details(db, id, **update_data.model_dump())
        return {"message": "Service: successfully updated user details"}

    def delete_user_service(self, id: UUID, db: Session) -> Dict[str, str]:
        """
        Deletes a user by their UUID.

        Args:
            id (UUID): The UUID of the user to delete.
            db (Session): SQLAlchemy database session.

        Returns:
            dict: Success message indicating the user was deleted.
        """

        try:
            user_crud.delete_user(db, id)
        except Exception as e:
            logger.error(f"{LOG_MSG} error deleting user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to delete user",
            )

        return {"message": "Service: user successfully deleted"}

    async def change_password_service(
        self, id: UUID, payload: PasswordChangeRequest, db: Session
    ) -> Dict[str, str]:
        """
        Changes a user's password after verifying the old password.

        Args:
            id (UUID): The UUID of the user.
            payload (PasswordChangeRequest): Contains the old and new passwords.
            db (Session): SQLAlchemy database session.

        Raises:
            HTTPException: If user is not found or old password is incorrect.

        Returns:
            dict: Success message indicating the password was changed.
        """

        user = user_crud.get_user_by_id(db, id)

        if not user:
            raise HTTPException(status_code=404, detail="user not found")

        verify = Hasher.verify_password(payload.old_password, user.password)

        if not verify:
            raise HTTPException(status_code=400, detail="wrong password")

        if payload.new_password != payload.confirm_new_password:
            raise HTTPException(
                status_code=400,
                detail="new password and confirm new password does not match",
            )

        hashed_pwd = Hasher.hash_password(payload.new_password)
        user_crud.change_password(db, id, hashed_pwd)

        await email_service.send_password_changed_confirmation(user.email, user.name)

        return {"message": "Service: successfully changed password"}


user_service = UserService()
