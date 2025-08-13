import uuid

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.connection import Base


class ArchivedImages(Base):
    __tablename__ = "archived_images"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_url = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    original_upload_name = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    water_temperature = Column(String(124), nullable=True)
    water_depth = Column(Float, nullable=True)
    uploaded_at = Column(DateTime, nullable=True)
    confidence_score = Column(Float, nullable=True)
    classification_labels = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    recommendations = Column(Text, nullable=True)
