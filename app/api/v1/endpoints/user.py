from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.auth import get_current_user
from app.db.connection import get_db
from app.schemas.password_reset import ForgotPasswordRequest, PasswordChangeRequest
from app.schemas.user import CreateUser, UpdateUser, UserOut
from app.services.user_service import user_service

router = APIRouter()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUser, db: Session = Depends(get_db)):
    """
    Creates a new user with the provided details.

    Args:
        user (CreateUser): The user data to be created (name, email, password, etc.).
        db (Session): Database session dependency.

    Returns:
        UserOut: The newly created user's data.
    """

    return user_service.create_user_service(payload, db)


@router.get("/email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    Retrieves a user by their email address.

    Args:
        email (str): The email of the user to retrieve.
        db (Session): Database session dependency.

    Returns:
        UserOut: The user's information.

    Raises:
        HTTPException: If the user is not found.
    """

    user = user_service.get_user_by_email_service(email, db)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/id/{id}", response_model=UserOut)
def get_user_by_id(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Retrieves a user by their UUID.

    Args:
        id (UUID): The UUID of the user to retrieve.
        db (Session): Database session dependency.

    Returns:
        UserOut: The user's information.

    Raises:
        HTTPException: If the user is not found.
    """

    if current_user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden method")

    user = user_service.get_user_by_id_service(id, db)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.get("/", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    """
    Retrieves all users from the database.

    Args:
        db (Session): Database session dependency.

    Returns:
        List[UserOut]: A list of all users.
    """

    return user_service.get_all_users_service(db)


@router.patch("/id/{id}", response_model=UserOut)
def update_user_details(
    id: UUID,
    payload: UpdateUser,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Updates an existing user's information by ID.

    Args:
        id (UUID): The ID of the user to update.
        update_data (UpdateUser): Fields to update in the user record.
        db (Session): Database session dependency.

    Returns:
        UserOut: The updated user data.

    Raises:
        HTTPException: If the update operation fails.
    """

    if current_user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden method")

    user_update = user_service.update_user_details_service(id, payload, db)
    if not user_update:
        raise HTTPException(status_code=400, detail="update failed")
    return user_update


@router.delete("/id/{id}")
def delete_user(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Deletes a user by their UUID.

    Args:
        id (UUID): The ID of the user to delete.
        db (Session): Database session dependency.

    Returns:
        dict: A message indicating successful deletion.

    Raises:
        HTTPException: If the deletion fails.
    """

    if current_user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden method")

    user_delete = user_service.delete_user_service(id, db)
    if not user_delete:
        raise HTTPException(status_code=400, detail="delete failed")
    return user_delete


@router.patch("/id/{id}/password")
async def update_password(
    id: UUID,
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(get_current_user),
):
    """
    Updates the password of the user with the given ID.

    This endpoint allows an authenticated user to change their own password.
    It verifies that the authenticated user matches the provided user ID,
    then delegates the password change to the service layer.

    Parameters:
        id (UUID): The ID of the user whose password is to be changed.
        payload (PasswordChangeRequest): An object containing the old and new passwords.
        db (Session): The database session dependency.
        current_user (UserOut): The currently authenticated user.

    Returns:
        UserOut: The updated user information upon successful password change.

    Raises:
        HTTPException:
            - 403 Forbidden if the authenticated user ID does not match the path ID.
            - 400 Bad Request if the password change fails in the service layer.
    """

    if current_user.id != id:
        raise HTTPException(status_code=403, detail="Forbidden method")

    update_password = await user_service.change_password_service(id, payload, db)
    if not update_password:
        raise HTTPException(status_code=400, detail="failed to change password")

    return update_password
