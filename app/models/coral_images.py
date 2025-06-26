from sqlalchemy import (
    Table,
    Column,
    DateTime,
    String,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from app.db.connection import Base


class CoralImages(Base):
    __tablename__ = "coral_images"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_url = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    original_upload_name = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, server_default=func.now(), nullable=False)
    processed = Column(Boolean, server_default="false", nullable=False)
