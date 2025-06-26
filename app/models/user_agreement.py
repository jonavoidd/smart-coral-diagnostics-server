from sqlalchemy import (
    Table,
    Column,
    DateTime,
    ForeignKey,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid
from app.db.connection import Base


class UserAgreement(Base):
    __tablename__ = "user_agreements"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    terms_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("terms_agreements.id"), nullable=False
    )
    agreed_at = Column(DateTime, server_default=func.now(), nullable=False)
