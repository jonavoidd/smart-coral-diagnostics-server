from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class BaseCoralImage(BaseModel):
    file_url: Optional[str] = None
    filename: Optional[str] = None
    original_upload_name: Optional[str] = None
    uploaded_at: datetime = None
    processed = Optional[bool] = False


class CoralImageCreate(BaseCoralImage):
    id: UUID
