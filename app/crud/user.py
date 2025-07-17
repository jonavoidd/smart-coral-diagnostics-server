import logging

from sqlalchemy import select, delete, update, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional, List
from uuid import UUID

from app.models.users import User, UserRole
from app.schemas.user import CreateUser, UpdateUser, UserOut

logger = logging.getLogger(__name__)
LOG_MSG = "Crud:"


def create_user(
    db: Session, payload: CreateUser, hashed_password: str
) -> Optional[UserOut]:
    user = User(
        **payload.model_dump(exclude={"password", "provider"}),
        password=hashed_password,
        provider="local",
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    except Exception as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error creating new user: {str(e)}")
        raise


def create_social_user(
    db: Session,
    first_name: str,
    last_name: str,
    email: str,
    provider: str,
    provider_id: str,
) -> Optional[UserOut]:
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=None,
        birthdate=None,
        agree_to_terms=True,
        provider=provider,
        provider_id=provider_id,
        is_verified=True,
        role=1,
        is_active=False,
        last_login=None,
        profile=None,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error creating new social user: {str(e)}")
        raise


def get_user_by_email(db: Session, email: str) -> Optional[UserOut]:
    query = select(User).where(User.email == email)

    try:
        result = db.execute(query)
        user = result.scalar_one_or_none()

        return user
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} database error occurred: {str(e)}")
        return None


def get_user_by_id(db: Session, id: UUID) -> Optional[UserOut]:
    query = select(User).where(User.id == id)

    try:
        result = db.execute(query)
        user = result.scalar_one_or_none()

        return user
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} database error occurred: {str(e)}")
        return None


def get_all_users(db: Session) -> Optional[List[UserOut]]:
    try:
        users = db.query(User).all()
        return users
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} database error occurred: {str(e)}")
        return None


def get_all_admin(db: Session) -> Optional[List[UserOut]] | None:
    query = select(User).where(
        or_(User.role == UserRole.ADMIN, User.role == UserRole.SUPER_ADMIN)
    )

    try:
        result = db.execute(query)
        admins = result.scalars().all()

        return admins
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting all admin: {str(e)}")
        return None


def update_user_details(db: Session, payload: UpdateUser) -> Optional[UserOut] | None:
    new_data = payload.model_dump(exclude_unset=True)
    query = update(User).where(User.id == id).values(**new_data).returning(User)

    try:
        result = db.execute(query)
        db.commit()

        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error updating user data: {str(e)}")
        raise


def delete_user(db: Session, id: UUID) -> bool:
    query = delete(User).where(User.id == id)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting user: {str(e)}")
        raise


def change_password(db: Session, id: UUID, new_password: str) -> Optional[UserOut]:
    query = (
        update(User).where(User.id == id).values(password=new_password).returning(User)
    )

    try:
        result = db.execute(query)
        db.commit()

        updated_user = result.scalar_one_or_none()
        return updated_user
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error changing password: {str(e)}")
        return None
