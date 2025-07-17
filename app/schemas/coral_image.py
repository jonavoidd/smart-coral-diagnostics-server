from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class BaseCoralImage(BaseModel):
    user_id: UUID
    file_url: Optional[str] = None
    filename: Optional[str] = None
    original_upload_name: Optional[str] = None
    uploaded_at: datetime = None
    processed: Optional[bool] = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CoralImageCreate(BaseCoralImage):
    pass


class CoralImageOut(BaseCoralImage):
    id: UUID

    class Config:
        from_attributes = True
