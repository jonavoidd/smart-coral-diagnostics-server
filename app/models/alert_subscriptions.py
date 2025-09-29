import uuid
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    Float,
    Integer,
    func,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.db.connection import Base


class AlertSubscription(Base):
    __tablename__ = "alert_subscriptions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(150), nullable=False, index=True)

    # Geographic preferences
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    radius_km = Column(Float, nullable=True, default=50.0)  # Alert radius in kilometers
    country = Column(String(150), nullable=True)
    city = Column(String(150), nullable=True)

    # Alert preferences
    bleaching_threshold = Column(
        Integer, nullable=False, default=200
    )  # Cases threshold
    alert_frequency = Column(
        String(50), nullable=False, default="immediate"
    )  # immediate, daily, weekly
    weekly_reports = Column(Boolean, nullable=False, default=True)
    monthly_reports = Column(Boolean, nullable=False, default=True)

    # System fields
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_alert_subscriptions_user_id", "user_id"),
        Index("idx_alert_subscriptions_email", "email"),
        Index("idx_alert_subscriptions_location", "latitude", "longitude"),
        Index("idx_alert_subscriptions_active", "is_active"),
    )


class AlertHistory(Base):
    __tablename__ = "alert_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscription_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    alert_type = Column(
        String(50), nullable=False
    )  # threshold_reached, weekly_report, monthly_report
    title = Column(String(255), nullable=False)
    message = Column(String(1000), nullable=True)

    # Alert data
    bleaching_count = Column(Integer, nullable=True)
    affected_area = Column(String(255), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Delivery status
    email_sent = Column(Boolean, nullable=False, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    delivery_status = Column(String(50), nullable=True)  # sent, failed, pending

    # System fields
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_alert_history_subscription", "subscription_id"),
        Index("idx_alert_history_type", "alert_type"),
        Index("idx_alert_history_created", "created_at"),
    )
