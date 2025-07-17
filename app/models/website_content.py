import uuid

from sqlalchemy import Column, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.db.connection import Base


class WebsiteContent(Base):
    __tablename__ = "website_content"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_website_content_on_id", "id"),
        Index("idx_content_table_on_title", "title"),
        Index("idx_content_table_on_content", "content"),
    )
