from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class PartialUserData(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str


class PartialAnalysisResult(BaseModel):
    id: UUID
    image_id: UUID
    confidence_score: float
    bleaching_percentage: Optional[float]
    classification_labels: str
    analysis_duration: float
    analyzed_at: datetime
    description: Optional[str]
    recommendations: Optional[str]


class BaseCoralImage(BaseModel):
    user_id: UUID
    name: Optional[str] = None
    file_url: Optional[str] = None
    filename: Optional[str] = None
    original_upload_name: Optional[str] = None
    processed: Optional[bool] = False
    is_public: Optional[bool] = True
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    water_temperature: Optional[str] = None
    water_depth: Optional[float] = None
    observation_date: Optional[datetime] = None
    uploaded_at: datetime = None


class UpdateCoralImage(BaseModel):
    latitude: Optional[float]
    longitude: Optional[float]
    water_temperature: Optional[str]
    water_depth: Optional[float]


class CoralImageCreate(BaseCoralImage):
    pass


class CoralImageOut(BaseCoralImage):
    id: UUID
    user: Optional[PartialUserData] = None
    name: Optional[str] = None
    analysis_results: Optional[List[PartialAnalysisResult]] = []

    class Config:
        from_attributes = True


class CoralImageLocation(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    class Config:
        from_attributes = True
