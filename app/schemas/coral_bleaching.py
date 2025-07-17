from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import UUID


class BleachingStatus(BaseModel):
    HEALTHY: str = "healthy"
    BLEACHED: str = "bleached"
    PARTIALLY_BLEACHED: str = "partially_bleached"
    UNCERTAIN: str = "uncertain"


class BleachingPrediction(BaseModel):
    status: BleachingStatus
    confidence: float = Field(..., ge=0.0, le=1.0)
    healthy_probability: float = Field(..., ge=0.0, le=1.0)
    bleached_probability: float = Field(..., ge=0.0, le=1.0)


class BleachingInferenceRequest(BaseModel):
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    save_analytics_event: bool = Field(default=True)


class BleachingInferenceResult(BaseModel):
    prediction: BleachingPrediction
    processing_time: float
    model_version: str
    image_metadata: Dict[str, Any]


class BleachingAnalysisResponse(BaseModel):
    coral_image_id: UUID
    analysis_result_id: UUID
    prediction: BleachingPrediction
    file_url: str
    processed: bool
    created_at: datetime
