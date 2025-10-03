from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from uuid import UUID


class CoralLocationStats(BaseModel):
    """Statistics for a specific location"""

    latitude: float
    longitude: float
    total_images: int
    bleached_count: int
    average_bleaching_percentage: float
    coral_image_ids: List[UUID]


class SeverityLevel(BaseModel):
    """Alert severity classification"""

    CRITICAL: str = "critical"  # >= 80% average bleaching, >= 150 bleached corals
    HIGH: str = "high"  # >= 60% average bleaching, >= 100 bleached corals
    MODERATE: str = "moderate"  # >= 40% average bleaching, >= 100 bleached corals
    LOW: str = "low"  # < 40% average bleaching, >= 100 bleached corals


class BaseBleachingAlert(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    location_name: Optional[str] = None
    severity_level: str
    total_images_analyzed: int = Field(..., ge=0)
    bleached_count: int = Field(..., ge=0)
    average_bleaching_percentage: float = Field(..., ge=0, le=100)
    is_active: bool = True
    alert_threshold: int = Field(default=100, ge=1)
    cluster_radius_km: Optional[float] = Field(default=5.0, ge=0)
    affected_coral_ids: Optional[List[UUID]] = []
    description: Optional[str] = None
    recommendations: Optional[str] = None


class CreateBleachingAlert(BaseBleachingAlert):
    """Schema for creating a new bleaching alert"""

    @field_validator("affected_coral_ids", mode="before")
    @classmethod
    def convert_uuids_to_strings(cls, v):
        """Convert UUID objects to strings for JSONB storage"""
        if v is None:
            return []
        if isinstance(v, list):
            return [str(item) if not isinstance(item, str) else item for item in v]
        return v

    class Config:
        from_attributes = True


class UpdateBleachingAlert(BaseModel):
    """Schema for updating an existing alert"""

    location_name: Optional[str] = None
    severity_level: Optional[str] = None
    total_images_analyzed: Optional[int] = None
    bleached_count: Optional[int] = None
    average_bleaching_percentage: Optional[float] = None
    is_active: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    affected_coral_ids: Optional[List[UUID]] = None
    description: Optional[str] = None
    recommendations: Optional[str] = None

    class Config:
        from_attributes = True


class BleachingAlertOut(BaseBleachingAlert):
    """Schema for bleaching alert output"""

    id: UUID
    first_detected_at: datetime
    last_updated_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BleachingAlertSummary(BaseModel):
    """Summary statistics for all alerts"""

    total_alerts: int
    active_alerts: int
    resolved_alerts: int
    critical_alerts: int
    high_alerts: int
    moderate_alerts: int
    low_alerts: int
    total_affected_corals: int
    average_bleaching_percentage: float
    most_affected_locations: List[BleachingAlertOut]


class AlertGenerationRequest(BaseModel):
    """Request parameters for generating alerts"""

    min_bleached_count: int = Field(
        default=100,
        ge=1,
        description="Minimum number of bleached corals to trigger alert",
    )
    cluster_radius_km: float = Field(
        default=5.0,
        ge=0.1,
        le=100,
        description="Radius in kilometers for location clustering",
    )
    min_bleaching_percentage: float = Field(
        default=30.0, ge=0, le=100, description="Minimum average bleaching percentage"
    )
    regenerate_existing: bool = Field(
        default=False, description="Whether to regenerate existing alerts"
    )


class AlertFilterParams(BaseModel):
    """Parameters for filtering alerts"""

    severity_level: Optional[str] = None
    is_active: Optional[bool] = None
    min_bleached_count: Optional[int] = None
    min_bleaching_percentage: Optional[float] = None
    latitude_min: Optional[float] = Field(None, ge=-90, le=90)
    latitude_max: Optional[float] = Field(None, ge=-90, le=90)
    longitude_min: Optional[float] = Field(None, ge=-180, le=180)
    longitude_max: Optional[float] = Field(None, ge=-180, le=180)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
