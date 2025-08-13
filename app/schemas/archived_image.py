from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID


class BaseArchivedImages(BaseModel):
    file_url: str
    filename: str
    original_upload_name: str
    latitude: float
    longitude: float
    water_temperature: str
    water_depth: float
    uploaded_at: datetime
    confidence_score: Optional[float]
    classification_labels: Optional[str]
    model_version: Optional[str]
    description: Optional[str]
    recommendations: Optional[str]


class CreateArchivedImage(BaseArchivedImages):
    pass

    class Config:
        from_attributes = True


class ArchivedImageOut(BaseArchivedImages):
    id: UUID

    class Config:
        from_attributes = True
