import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    used_at = Column(DateTime, nullable=True, index=True)

    user = relationship("User", back_populates="verification_tokens")

    __table_args__ = (
        Index("idx_verification_tokens_id", "id"),
        Index("idx_verification_tokens_user_id", "user_id"),
        Index("idx_verification_tokens_token", "token"),
    )
