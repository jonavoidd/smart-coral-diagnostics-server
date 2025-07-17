import logging

from datetime import datetime, timedelta, timezone
from sqlalchemy import insert, select, update, delete, and_
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.password_reset_tokens import PasswordResetToken

logger = logging.getLogger(__name__)


def store_reset_token(db: Session, id: UUID, token: str, expires_at: datetime) -> bool:
    """
    Stores a new password reset token for a user in the database.

    Args:
        db (Session): SQLAlchemy database session.
        id (UUID): UUID of the user.
        token (str): The reset token to store.
        expires_at (datetime): Expiration datetime of the token.

    Returns:
        bool: True if the token was stored successfully, False otherwise.

    Raises:
        Exception: If an error occurs during the database transaction.
    """

    cleaned = cleanup_user_token(db, id)

    if cleaned:
        logger.info(f"old reset tokens for {id} were cleaned up")

    reset_token = PasswordResetToken(user_id=id, token=token, expires_at=expires_at)

    try:
        db.add(reset_token)
        db.commit()
        db.refresh(reset_token)

        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error storing reset tokens: {e}")
        raise


def get_reset_token(db: Session, token: str) -> Optional[PasswordResetToken]:
    """
    Retrieves a valid and unused password reset token from the database.

    Args:
        db (Session): SQLAlchemy database session.
        token (str): The reset token to retrieve.

    Returns:
        Optional[PasswordResetToken]: The matching PasswordResetToken object if found and valid, else None.

    Raises:
        Exception: If an error occurs during the query.
    """

    query = select(PasswordResetToken).where(
        and_(
            PasswordResetToken.token == token,
            PasswordResetToken.expires_at > datetime.now(timezone.utc),
            PasswordResetToken.used_at.is_(None),
        )
    )

    try:
        result = db.execute(query)
        token = result.scalar_one_or_none()

        return token
    except Exception as e:
        logger.error(f"Error getting the reset token: {e}")
        raise


def mark_reset_token_as_used(db: Session, token: str) -> bool:
    """
    Marks a password reset token as used by setting the 'used_at' timestamp.

    Args:
        db (Session): SQLAlchemy database session.
        token (str): The reset token to mark as used.

    Returns:
        bool: True if the token was found and marked, False otherwise.

    Raises:
        Exception: If an error occurs during the database transaction.
    """

    query = select(PasswordResetToken).where(PasswordResetToken.token == token)

    try:
        result = db.execute(query)
        reset_token = result.scalar_one_or_none()

        if reset_token:
            reset_token.used_at = datetime.now(timezone.utc)
            db.commit()
            return True
        else:
            return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating reset_token: {e}")
        raise


def cleanup_user_token(db: Session, id: UUID) -> bool:
    """
    Deletes all expired password reset tokens for a specific user.

    Args:
        db (Session): SQLAlchemy database session.
        id (UUID): UUID of the user whose expired tokens should be removed.

    Returns:
        bool: True if tokens were deleted successfully, False otherwise.
    """

    query = delete(PasswordResetToken).where(
        and_(
            PasswordResetToken.user_id == id,
            PasswordResetToken.expires_at < datetime.now(timezone.utc),
        )
    )

    try:
        db.execute(query)
        db.commit()

        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting token: {e}")
        return False


def cleanup_expired_token(db: Session) -> bool:
    """
    Deletes all expired password reset tokens from the database, regardless of user.

    Args:
        db (Session): SQLAlchemy database session.

    Returns:
        bool: True if expired tokens were deleted successfully, False otherwise.
    """

    query = delete(PasswordResetToken).where(
        PasswordResetToken.expires_at < datetime.now(timezone.utc)
    )

    try:
        db.execute(query)
        db.commit()

        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting token: {e}")
        return False
