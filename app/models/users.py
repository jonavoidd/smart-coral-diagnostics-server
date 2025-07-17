import uuid

from enum import IntEnum
from sqlalchemy import (
    ARRAY,
    Column,
    Integer,
    Index,
    String,
    Date,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class UserRole(IntEnum):
    USER = 1
    ADMIN = 2
    SUPER_ADMIN = 3


class User(Base):
    __tablename__ = "users"

    # core fields
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=True)
    provider = Column(String(255), nullable=True, default="local")
    provider_id = Column(String(255), nullable=True)
    contact_number = Column(String(50), nullable=True)

    # user preference
    agree_to_terms = Column(Boolean, nullable=False)
    subscribe_to_newsletter = Column(Boolean, nullable=True, server_default="false")

    # location
    city = Column(String(150), nullable=True)
    country = Column(String(150), nullable=True)

    # profile fields
    birthdate = Column(Date, nullable=False)
    bio = Column(String(500), nullable=True)
    experience = Column(String(50), nullable=True)
    diving_certification = Column(String(100), nullable=True)
    research_experience = Column(String(50), nullable=True)

    # professional info
    organization = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)

    # array fields
    primary_interests = Column(ARRAY(String), default=[])
    contribution_types = Column(ARRAY(String), default=[])

    # system fields
    role = Column(Integer, nullable=True, default=UserRole.USER)
    profile = Column(String(255), nullable=True)
    is_verified = Column(Boolean, nullable=True, default=False)
    is_active = Column(Boolean, nullable=False, server_default="false")
    last_login = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    analytics_events = relationship(
        "AnalyticsEvent",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )

    reset_tokens = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )

    verification_tokens = relationship(
        "VerificationToken",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )

    coral_images = relationship(
        "CoralImages", back_populates="user", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_users_on_id", "id"),
        Index("idx_users_on_email", "email"),
        Index("idx_users_on_is_active", "is_active"),
        Index("idx_users_on_provider", "provider"),
        Index("idx_users_on_provider_id", "provider_id"),
    )
