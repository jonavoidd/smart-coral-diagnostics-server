import uuid

from enum import IntEnum
from sqlalchemy import (
    Column,
    Integer,
    Index,
    String,
    DateTime,
    Boolean,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class UserRole(IntEnum):
    USER = 1
    ADMIN = 2


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=True)

    provider = Column(String(255), nullable=True, default="local")
    provider_id = Column(String(255), nullable=True)
    is_verified = Column(Boolean, nullable=True, default=False)

    agree_to_terms = Column(Boolean, nullable=False)
    age = Column(Integer, nullable=False)
    role = Column(Integer, nullable=True, default=UserRole.USER)

    is_active = Column(Boolean, nullable=False, server_default="false")
    last_login = Column(DateTime, nullable=True)

    profile = Column(String(255), nullable=True)
    company = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    reset_tokens = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )

    verification_tokens = relationship(
        "VerificationToken", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="unique_provider_user"),
        Index("idx_users_on_id", "id"),
        Index("idx_users_on_email", "email"),
        Index("idx_users_on_is_active", "is_active"),
        Index("idx_users_on_provider", "provider"),
        Index("idx_users_on_provider_id", "provider_id"),
    )
