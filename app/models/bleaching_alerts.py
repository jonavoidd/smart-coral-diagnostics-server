import uuid

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Integer,
    Boolean,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import relationship

from app.db.connection import Base


class BleachingAlert(Base):
    __tablename__ = "bleaching_alerts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Location information
    latitude = Column(Float, nullable=False, index=True)
    longitude = Column(Float, nullable=False, index=True)
    location_name = Column(String(255), nullable=True)

    # Alert severity and statistics
    severity_level = Column(
        String(50), nullable=False, index=True
    )  # critical, high, moderate, low
    total_images_analyzed = Column(Integer, nullable=False, default=0)
    bleached_count = Column(Integer, nullable=False, default=0)
    average_bleaching_percentage = Column(Float, nullable=False)

    # Alert status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    alert_threshold = Column(Integer, nullable=False, default=100)

    # Time tracking
    first_detected_at = Column(DateTime, nullable=False, server_default=func.now())
    last_updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    resolved_at = Column(DateTime, nullable=True)

    # Additional metadata
    affected_coral_ids = Column(JSONB, nullable=True)  # List of coral image IDs
    description = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)

    # Geographic clustering info
    cluster_radius_km = Column(Float, nullable=True)  # radius in kilometers

    def __repr__(self):
        return f"<BleachingAlert {self.id} - {self.severity_level} at ({self.latitude}, {self.longitude})>"
