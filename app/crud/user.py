from sqlalchemy import insert, select, delete, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone
from uuid import UUID
import logging

from app.models.users import User
from app.db.connection import engine

logger = logging.getLogger(__name__)


def create_user(
    db: Session,
    name: str,
    email: str,
    password: str,
    provider: str,
    age: int,
    role: int = None,
    company: str = None,
    position: str = None,
):
    user = User(
        name=name,
        email=email,
        password=password,
        provider=provider,
        provider_id=None,
        is_verified=False,
        agree_to_terms=True,
        age=age,
        role=role,
        is_active=False,
        last_login=None,
        profile=None,
        company=company,
        position=position,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    except Exception as e:
        db.rollback()
        logger.error(f"error creating new user: {e}")
        raise


def create_social_user(
    db: Session, name: str, email: str, provider: str, provider_id: str
):
    user = User(
        name=name,
        email=email,
        password=None,
        age=None,
        agree_to_terms=True,
        provider=provider,
        provider_id=provider_id,
        is_verified=True,
        role=2,
        is_active=False,
        last_login=None,
        profile=None,
        company=None,
        position=None,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

        return user
    except Exception as e:
        db.rollback()
        logger.error(f"error creating new social user: {e}")
        raise


def get_user_by_email(db: Session, email: str):
    query = select(User).where(User.email == email)

    try:
        result = db.execute(query)
        user = result.scalar_one_or_none()

        return user
    except SQLAlchemyError as e:
        logger.error(f"database error occured: {e}")
        return None


def get_user_by_id(db: Session, id: UUID):
    query = select(User).where(User.id == id)

    try:
        result = db.execute(query)
        user = result.scalar_one_or_none()

        return user
    except SQLAlchemyError as e:
        logger.error(f"database error occured: {e}")
        return None


def get_all_users(db: Session):
    try:
        users = db.query(User).all()
        return users
    except SQLAlchemyError as e:
        logger.error(f"database error occured: {e}")
        return None


def update_user_details(
    db: Session,
    id: UUID,
    name: str,
    password: str,
    provider: str,
    provider_id: str,
    is_verified: bool,
    age: int,
    role: int,
    profile: str,
    company: str,
    position: str,
    updated_at: datetime = None,
):
    new_data = {
        "name": name,
        "password": password,
        "provider": provider,
        "provider_id": provider_id,
        "is_verified": is_verified,
        "age": age,
        "role": role,
        "profile": profile,
        "company": company,
        "position": position,
        "updated_at": updated_at or datetime.now(timezone.utc),
    }
    query = update(User).where(User.id == id).values(**new_data).returning(User)

    try:
        db.execute(query)
        db.commit()
        updated_user = db.query(User).filter(User.id == id).one_or_none()

        return updated_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user data: {e}")
        raise


def delete_user(db: Session, id: UUID):
    query = delete(User).where(User.id == id)

    try:
        result = db.execute(query)
        db.commit()

        return result.rowcount > 0
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting user: {e}")
        raise
