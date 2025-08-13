import uuid

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class CoralImages(Base):
    __tablename__ = "coral_images"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_url = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    original_upload_name = Column(String(255), nullable=False)
    processed = Column(Boolean, server_default="false", nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    water_temperature = Column(String(124), nullable=True)
    water_depth = Column(Float, nullable=True)
    observation_date = Column(DateTime, nullable=True)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)

    analysis_results = relationship(
        "AnalysisResult",
        back_populates="coral_images",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    user = relationship("User", back_populates="coral_images")
