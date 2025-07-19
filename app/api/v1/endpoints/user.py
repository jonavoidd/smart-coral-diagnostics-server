from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.password_reset import PasswordChangeRequest
from app.schemas.user import CreateUser, UpdateUser, UserOut
from app.services.user_service import user_service

router = APIRouter()


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUser, db: Session = Depends(get_db)):
    """
    Creates a new user with the provided details.

    <b>Args</b>:
        user (CreateUser): The user data to be created (name, email, password, etc.).
        db (Session): Database session dependency.

    <b>Returns</b>:
        UserOut: The newly created user's data.
    """

    return user_service.create_user_service(db, payload)


@router.get("/email/{email}", response_model=UserOut)
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    """
    Retrieves a user by their email address.

    <b>Args</b>:
        email (str): The email of the user to retrieve.
        db (Session): Database session dependency.

    <b>Returns</b>:
        UserOut: The user's information.

    <b>Raises</b>:
        HTTPException: If the user is not found.
    """

    user = user_service.get_user_by_email_service(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return user


@router.get("/id/{id}", response_model=UserOut)
def get_user_by_id(id: UUID, db: Session = Depends(get_db)):
    """
    Retrieves a user by their UUID.

    <b>Args</b>:
        id (UUID): The UUID of the user to retrieve.
        db (Session): Database session dependency.

    <b>Returns</b>:
        UserOut: The user's information.

    <b>Raises</b>:
        HTTPException: If the user is not found.
    """

    user = user_service.get_user_by_id_service(db, id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
        )
    return user


@router.get("/", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    """
    Retrieves all users from the database.

    <b>Args</b>:
        db (Session): Database session dependency.

    <b>Returns</b>:
        List[UserOut]: A list of all users.
    """

    return user_service.get_all_users_service(db)


@router.get("/admin/")
def get_all_admin(db: Session = Depends(get_db)):
    return user_service.get_all_admin_service(db)


@router.patch("/id/{id}", response_model=UserOut)
def update_user_details(
    id: UUID,
    payload: UpdateUser,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.USER])),
):
    """
    Updates an existing user's information by ID.

    <b>Args</b>:
        id (UUID): The ID of the user to update.
        update_data (UpdateUser): Fields to update in the user record.
        db (Session): Database session dependency.

    <b>Returns</b>:
        UserOut: The updated user data.

    <b>Raises</b>:
        HTTPException: If the update operation fails.
    """

    if current_user.id != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden method"
        )

    user_update = user_service.update_user_details_service(db, id, payload)
    if not user_update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="update failed"
        )
    return user_update


@router.delete("/id/{id}")
def delete_user(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.USER, UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """
    Deletes a user by their UUID.

    <b>Args</b>:
        id (UUID): The ID of the user to delete.
        db (Session): Database session dependency.

    <b>Returns</b>:
        dict: A message indicating successful deletion.

    <b>Raises</b>:
        HTTPException: If the deletion fails.
    """

    user_delete = user_service.delete_user_service(db, id, current_user)
    if not user_delete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="delete failed"
        )

    return user_delete


@router.patch("/id/{id}/password")
async def update_password(
    id: UUID,
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(require_role([UserRole.USER, UserRole.ADMIN])),
):
    """
    Updates the password of the user with the given ID.

    This endpoint allows an authenticated user to change their own password.
    It verifies that the authenticated user matches the provided user ID,
    then delegates the password change to the service layer.

    <b>Parameters</b>:
        id (UUID): The ID of the user whose password is to be changed.
        payload (PasswordChangeRequest): An object containing the old and new passwords.
        db (Session): The database session dependency.
        current_user (UserOut): The currently authenticated user.

    <b>Returns</b>:
        UserOut: The updated user information upon successful password change.

    <b>Raises</b>:
        HTTPException:
            - 403 Forbidden if the authenticated user ID does not match the path ID.
            - 400 Bad Request if the password change fails in the service layer.
    """

    if current_user.id != id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden method"
        )

    update_password = await user_service.change_password_service(
        db, id, payload, current_user
    )
    if not update_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="failed to change password"
        )

    return update_password
