from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Float,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
import uuid
from app.db.connection import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(PG_UUID(as_uuid=True), ForeignKey("coral_images.id"))
    condifence_score = Column(Float, nullable=True)
    classification_labels = Column(String(100), nullable=True, index=True)
    bounding_boxes = Column(JSONB, nullable=True)
    model_version = Column(String(50), nullable=True)
    analysis_time = Column(DateTime, server_default=func.now(), nullable=False)
