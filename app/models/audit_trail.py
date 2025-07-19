import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base
from app.models.users import UserRole


class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_role = Column(Integer, nullable=False, default=UserRole.USER)
    action = Column(String(255), nullable=False, default="")
    resource_type = Column(String(255), nullable=False, default="")
    resource_id = Column(PG_UUID(as_uuid=True), nullable=True)
    description = Column(Text, nullable=False, default="")
    timestamp = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="audit_trail")

    __table_args__ = (
        Index("idx_audit_trail_on_id", "id"),
        Index("idx_audit_trail_on_actor_id", "actor_id"),
        Index("idx_audit_trail_on_resource_type", "resource_type"),
        Index("idx_audit_trail_on_timestamp", "timestamp"),
    )
