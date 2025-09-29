from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from uuid import UUID


class AlertSubscriptionBase(BaseModel):
    email: EmailStr
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 50.0
    country: Optional[str] = None
    city: Optional[str] = None
    bleaching_threshold: int = 200
    alert_frequency: str = "immediate"  # immediate, daily, weekly
    weekly_reports: bool = True
    monthly_reports: bool = True


class AlertSubscriptionCreate(AlertSubscriptionBase):
    pass


class AlertSubscriptionUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = None
    country: Optional[str] = None
    city: Optional[str] = None
    bleaching_threshold: Optional[int] = None
    alert_frequency: Optional[str] = None
    weekly_reports: Optional[bool] = None
    monthly_reports: Optional[bool] = None
    is_active: Optional[bool] = None


class AlertSubscriptionResponse(AlertSubscriptionBase):
    id: UUID
    user_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    id: UUID
    subscription_id: UUID
    alert_type: str
    title: str
    message: Optional[str] = None
    bleaching_count: Optional[int] = None
    affected_area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    email_sent: bool
    email_sent_at: Optional[datetime] = None
    delivery_status: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class BleachingAlertData(BaseModel):
    """Data structure for bleaching alert information"""

    area_name: str
    latitude: float
    longitude: float
    bleaching_count: int
    threshold: int
    affected_radius_km: float
    recent_cases: list  # List of recent bleaching cases
    severity_level: str  # low, medium, high, critical
