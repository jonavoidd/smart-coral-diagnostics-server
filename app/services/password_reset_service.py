import logging
import secrets

from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.config import settings
from app.core.security import Hasher
from app.crud.password_reset import (
    cleanup_user_token,
    cleanup_expired_token,
    get_reset_token,
    mark_reset_token_as_used,
    store_reset_token,
)
from app.crud.user import get_user_by_email, get_user_by_id, change_password
from app.services.email_service import email_service
from app.schemas.password_reset import (
    GetToken,
    PasswordChangeRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)

logger = logging.getLogger(__name__)


class PasswordResetService:
    @staticmethod
    async def initiate_password_reset(
        db: Session, payload: ForgotPasswordRequest
    ) -> bool:
        """
        Initiates the password reset process for a given user's email.

        This method verifies the existence of a user associated with the provided email,
        generates a secure reset token, stores it in the database with an expiration time,
        and sends a reset email to the user.

        Args:
            db (Session): SQLAlchemy database session.
            payload (ForgotPasswordRequest): The request payload containing the user's email.

        Returns:
            bool: True if the reset process was initiated successfully, False otherwise.
        """

        from datetime import datetime, timezone, timedelta

        try:
            user = get_user_by_email(db, payload.email)

            if not user:
                logger.info(
                    f"Service: password reset requested for non-existent email: {payload.email}"
                )
                return False

            cleanup_user_token(db, user.id)

            token = secrets.token_urlsafe(32)
            # current_time = datetime.now(timezone.utc)
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
            )

            store_reset_token(db, user.id, token, expires_at)

            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            name = f"{user.first_name} {user.last_name}"

            await email_service.send_password_reset_email(
                user.email, name, reset_url, expires_at
            )

            logger.info(f"Service: password reset initiated for user: {user}")
            return True
        except Exception as e:
            logger.error(f"Service: ")
            logger.error(
                f"Service: error initiating password reset for the email: {payload.email}: {str(e)}"
            )
            return False

    @staticmethod
    def validate_reset_token(db: Session, payload: GetToken) -> Optional[dict]:
        """
        Validates a password reset token and retrieves associated metadata.

        Args:
            db (Session): SQLAlchemy database session.
            payload (ResetPasswordRequest): The request payload containing the token.

        Returns:
            Optional[dict]: A dictionary containing token metadata (user ID, creation time,
            expiration time) if the token is valid, None otherwise.
        """

        try:
            token_data = get_reset_token(db, payload.token)

            if not token_data:
                logger.warning(f"Service: invalid token used: {payload.token}")
                return None

            return {
                "user_id": token_data.user_id,
                "expires_at": token_data.expires_at,
                "created_at": token_data.created_at,
            }
        except Exception as e:
            logger.error(f"Service: error validating reset token: {str(e)}")
            return None

    @staticmethod
    async def reset_password(db: Session, payload: ResetPasswordRequest) -> bool:
        """
        Resets the user's password using a valid reset token and new password.

        This method validates the reset token, hashes the new password, updates the user's
        password in the database, marks the token as used, and sends a confirmation email.

        Args:
            db (Session): SQLAlchemy database session.
            payload (ResetPasswordRequest): The request payload with token and new password.

        Returns:
            bool: True if the password was successfully reset, False otherwise.
        """

        try:
            token_data = get_reset_token(db, payload.token)

            if not token_data:
                logger.warning(
                    f"Service: invalid reset token used for password reset: {payload.token}"
                )
                return False

            user = get_user_by_id(db, token_data.user_id)
            if not user:
                logger.error(f"Service: user not found for token: {payload.token}")
                return False

            password_hash = Hasher.hash_password(payload.new_password)

            success = change_password(db, user.id, password_hash)
            if not success:
                logger.error(f"Service: error updating password for: {user.email}")
                return False

            mark_reset_token_as_used(db, payload.token)
            await email_service.send_password_changed_confirmation(
                user.email, user.name
            )

            logger.info(f"Service: password changed successfully for {user.email}")
            return True
        except Exception as e:
            logger.error(
                f"Service: error resetting password for {payload.token}: {str(e)}"
            )
            return False

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Deletes expired password reset tokens from the database.

        Args:
            db (Session): SQLAlchemy database session.

        Returns:
            int: The number of expired tokens deleted.
        """

        try:
            deleted_account = cleanup_expired_token(db)
            logger.info(f"Service: cleaned up {deleted_account} expired reset token")
            return deleted_account
        except Exception as e:
            logger.error(f"Service: error cleaning up expired tokens: {str(e)}")
            return 0

    @staticmethod
    def revoke_user_tokens(db: Session, id: UUID) -> bool:
        """
        Revokes all active password reset tokens for a specific user.

        Args:
            db (Session): SQLAlchemy database session.
            id (UUID): The UUID of the user whose tokens should be revoked.

        Returns:
            bool: True if tokens were successfully revoked, False otherwise.
        """

        try:
            cleanup_user_token(db, id)
            logger.info(f"Service: revoked all reset tokens for user: {id}")
            return True
        except Exception as e:
            logger.error(f"Service: Error revoking reset tokens for user: {id}")
            return False


password_reset_service = PasswordResetService()
