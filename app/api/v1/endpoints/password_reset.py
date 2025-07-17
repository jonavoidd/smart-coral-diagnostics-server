from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.auth import get_current_user
from app.db.connection import get_db
from app.schemas.password_reset import (
    GetToken,
    ForgotPasswordRequest,
    PasswordChangeRequest,
    ResetPasswordRequest,
)
from app.schemas.password_reset import RequestResponse
from app.schemas.user import UserOut
from app.services.password_reset_service import password_reset_service

router = APIRouter()


@router.post("/")
async def send_password_request(
    payload: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """
    Initiates a password reset request by sending a reset token to the user.

    <b>Args</b>:
        payload (ForgotPasswordRequest): The request containing user information and
                                          the email address to initiate the reset.
        db (Session): The database session for interaction with the database.

    <b>Returns</b>:
        RequestResponse: A response indicating whether the password reset request was
                         successfully initiated.
    """

    return await password_reset_service.initiate_password_reset(db, payload)


@router.get("/")
def validate_reset_token(payload: GetToken, db: Session = Depends(get_db)):
    """
    Validates a reset token to ensure it's valid for a password reset.

    <b>Args</b>:
        payload (ResetPasswordRequest): The request containing the reset token
                                        to be validated.
        db (Session): The database session for interaction with the database.

    <b>Returns</b>:
        RequestResponse: A response indicating whether the reset token is valid.
    """

    return password_reset_service.validate_reset_token(payload, db)


@router.patch("/")
async def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Resets the user's password using a valid reset token.

    <b>Args</b>:
        payload (ResetPasswordRequest): The request containing the new password
                                        and the reset token.
        db (Session): The database session for interaction with the database.

    <b>Returns</b>:
        RequestResponse: A response indicating whether the password reset was
                         successful.
    """

    return await password_reset_service.reset_password(db, payload)


@router.delete("/")
def cleanup_expired_token(db: Session = Depends(get_db)):
    """
    Cleans up expired password reset tokens from the database.

    <b>Args</b>:
        db (Session): The database session for interaction with the database.

    <b>Returns</b>:
        Response: A confirmation of the expired token cleanup.
    """

    return password_reset_service.cleanup_expired_tokens(db)


@router.delete("/id/{id}")
def revoke_user_tokens(id: UUID, db: Session = Depends(get_db)):
    """
    Revokes all password reset tokens for a specific user identified by their ID.

    <b>Args</b>:
        id (UUID): The UUID of the user whose tokens will be revoked.
        db (Session): The database session for interaction with the database.

    <b>Returns</b>:
        Response: A confirmation of token revocation for the user.
    """

    return password_reset_service.revoke_user_tokens(db, id)
