import logging

from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.models.verification_tokens import VerificationToken
from app.models.users import User

logger = logging.getLogger(__name__)
LOG_MSG = "CRUD:"


def store_verification_token(
    db: Session, id: UUID, token: str, expires_at: datetime
) -> bool:
    cleaned = cleanup_user_verification_token(db, id)
    if cleaned:
        logger.info(f"{LOG_MSG} existing verification tokens for {id} were cleaned up")

    verification_token = VerificationToken(
        user_id=id, token=token, expires_at=expires_at
    )

    try:
        db.add(verification_token)
        db.commit()
        db.refresh(verification_token)

        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error storing verification token")
        return False


def get_verification_token(db: Session, token: str) -> Optional[VerificationToken]:
    """
    Get a verification token by token string.
    Only validates the token exists and hasn't expired - does NOT verify the user.
    """
    query = select(VerificationToken).where(
        and_(
            VerificationToken.token == token,
            VerificationToken.expires_at > datetime.now(timezone.utc),
            VerificationToken.used_at.is_(None),
        )
    )

    try:
        result = db.execute(query)
        verification_token = result.scalar_one_or_none()

        if verification_token is None:
            logger.info(f"{LOG_MSG} token not found, expired, or already used")
            return None

        logger.info(
            f"{LOG_MSG} valid verification token found for user {verification_token.user_id}"
        )
        return verification_token
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting verification token: {str(e)}")
        raise


def verify_token_and_mark_used(
    db: Session, verification_token: VerificationToken
) -> bool:
    try:
        success = verify_user(db, verification_token.user_id)

        if success:
            db.execute(
                update(VerificationToken)
                .where(VerificationToken.id == verification_token.id)
                .values(used_at=datetime.now(timezone.utc))
            )
            db.commit()
            logger.info(
                f"{LOG_MSG} user {verification_token.user_id} verified and token marked as used."
            )
            return True
        else:
            logger.error(
                f"{LOG_MSG} user failed to verify user {verification_token.user_id}."
            )
            return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error verifying user and marking token: {str(e)}")
        return False


def verify_user(db: Session, id: UUID) -> bool:
    query = update(User).where(User.id == id).values(is_verified=True, is_active=True)

    try:
        result = db.execute(query)
        if result.rowcount == 0:
            return False

        db.commit()

        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error verifying user: {str(e)}")
        return False


def cleanup_user_verification_token(db: Session, id: UUID) -> bool:
    query = delete(VerificationToken).where(
        VerificationToken.user_id == id,
        or_(
            VerificationToken.expires_at < datetime.now(timezone.utc),
            VerificationToken.used_at.is_not(None),
        ),
    )

    try:
        result = db.execute(query)
        deleted_count = result.rowcount
        db.commit()

        if deleted_count:
            logger.info(
                f"{LOG_MSG} cleaned up {deleted_count} verifications tokens found for user {id}"
            )

        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting tokens: {str(e)}")
        return False


def cleanup_verification_tokens(db: Session) -> bool:
    query = delete(VerificationToken).where(
        or_(
            VerificationToken.expires_at < datetime.now(timezone.utc),
            VerificationToken.used_at.is_not(None),
        )
    )

    try:
        result = db.execute(query)
        deleted_count = result.rowcount
        db.commit()

        logger.info(
            f"{LOG_MSG} cleaned up {deleted_count} expired/used verification tokens."
        )
        return True
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting tokens: {e}")
        return False
