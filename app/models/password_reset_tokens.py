import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
    used_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_password_reset_tokens_token", "token"),
        Index("idx_password_reset_tokens_expires_at", "expires_at"),
        Index("idx_password_reset_tokens_user_id", "user_id"),
    )

    user = relationship("User", back_populates="reset_tokens")
