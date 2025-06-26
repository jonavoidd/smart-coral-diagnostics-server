from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import uuid

from app.db.connection import Base


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    agree_to_terms = Column(Boolean, nullable=False)
    age = Column(Integer, nullable=False)
    role = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True, server_default="false")
    last_login = Column(DateTime, nullable=True)
    profile = Column(String(255), nullable=True)
    company = Column(String(100), nullable=True)
    position = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
