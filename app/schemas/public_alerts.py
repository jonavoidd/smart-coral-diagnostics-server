from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID


class PublicBleachingAlert(BaseModel):
    """Public bleaching alert data for display to all users"""

    id: UUID
    area_name: str
    latitude: float
    longitude: float
    bleaching_count: int
    threshold: int
    severity_level: str  # low, medium, high, critical
    affected_radius_km: float
    created_at: datetime
    last_updated: datetime
    is_active: bool = True


class PublicAlertSummary(BaseModel):
    """Summary of all active public alerts"""

    total_active_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    last_updated: datetime


class PublicAlertStats(BaseModel):
    """Public statistics about bleaching cases"""

    total_bleaching_cases_today: int
    total_bleaching_cases_this_week: int
    total_bleaching_cases_this_month: int
    most_affected_areas: List[dict]  # [{"area": "Manila, Philippines", "cases": 150}]
    severity_distribution: dict  # {"high": 10, "medium": 25, "low": 15}
    last_updated: datetime


class PublicAlertCreate(BaseModel):
    """Schema for creating public alerts (admin only)"""

    area_name: str
    latitude: float
    longitude: float
    bleaching_count: int
    threshold: int
    affected_radius_km: float = 50.0
    severity_level: str = "medium"
    description: Optional[str] = None


class PublicAlertUpdate(BaseModel):
    """Schema for updating public alerts (admin only)"""

    area_name: Optional[str] = None
    bleaching_count: Optional[int] = None
    severity_level: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None
