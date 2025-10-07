from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings
from app.models import *


DATABASE_URL = settings.TRANSACTION_POOLER

if not DATABASE_URL:
    raise ValueError("DatabaseUrl is not set on .env")

# DATABASE_URL = (
#     "postgresql://postgres:postgres@localhost:5432/smart_coral?sslmode=disable"
# )

engine: Engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
