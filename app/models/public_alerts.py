import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Float,
    Integer,
    Text,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class PublicBleachingAlert(Base):
    __tablename__ = "public_bleaching_alerts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Alert information
    area_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    bleaching_count = Column(Integer, nullable=False)
    threshold = Column(Integer, nullable=False, default=200)
    severity_level = Column(String(50), nullable=False, default="medium")
    affected_radius_km = Column(Float, nullable=False, default=50.0)
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # System fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_updated = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_public_alerts_active", "is_active"),
        Index("idx_public_alerts_severity", "severity_level"),
        Index("idx_public_alerts_location", "latitude", "longitude"),
        Index("idx_public_alerts_created", "created_at"),
    )


class PublicAlertHistory(Base):
    __tablename__ = "public_alert_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)

    # Change information
    change_type = Column(
        String(50), nullable=False
    )  # created, updated, severity_changed, deactivated
    old_value = Column(String(255), nullable=True)
    new_value = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # System fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_public_alert_history_alert", "alert_id"),
        Index("idx_public_alert_history_type", "change_type"),
        Index("idx_public_alert_history_created", "created_at"),
    )
