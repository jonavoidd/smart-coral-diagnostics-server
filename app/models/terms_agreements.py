from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from app.db.connection import Base


class TermsAgreement(Base):
    __tablename__ = "terms_agreements"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(50), nullable=True)
    content = Column(Text, nullable=True)
    published_at = Column(DateTime, server_default=func.now(), nullable=True)
