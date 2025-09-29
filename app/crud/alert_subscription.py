from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.alert_subscriptions import AlertSubscription, AlertHistory
from app.schemas.alert_subscription import (
    AlertSubscriptionCreate,
    AlertSubscriptionUpdate,
)


def create_alert_subscription(
    db: Session, subscription_data: AlertSubscriptionCreate, user_id: UUID
) -> AlertSubscription:
    """Create a new alert subscription"""
    subscription = AlertSubscription(
        user_id=user_id,
        email=subscription_data.email,
        latitude=subscription_data.latitude,
        longitude=subscription_data.longitude,
        radius_km=subscription_data.radius_km,
        country=subscription_data.country,
        city=subscription_data.city,
        bleaching_threshold=subscription_data.bleaching_threshold,
        alert_frequency=subscription_data.alert_frequency,
        weekly_reports=subscription_data.weekly_reports,
        monthly_reports=subscription_data.monthly_reports,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_alert_subscription_by_user_id(
    db: Session, user_id: UUID, active_only: bool = True
) -> Optional[AlertSubscription]:
    """Get alert subscription by user ID"""
    query = db.query(AlertSubscription).filter(AlertSubscription.user_id == user_id)

    if active_only:
        query = query.filter(AlertSubscription.is_active == True)

    return query.first()


def get_alert_subscription_by_id(
    db: Session, subscription_id: UUID
) -> Optional[AlertSubscription]:
    """Get alert subscription by ID"""
    return (
        db.query(AlertSubscription)
        .filter(AlertSubscription.id == subscription_id)
        .first()
    )


def update_alert_subscription(
    db: Session, subscription_id: UUID, subscription_update: AlertSubscriptionUpdate
) -> Optional[AlertSubscription]:
    """Update an alert subscription"""
    subscription = (
        db.query(AlertSubscription)
        .filter(AlertSubscription.id == subscription_id)
        .first()
    )

    if not subscription:
        return None

    # Update fields that are provided
    update_data = subscription_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)
    return subscription


def deactivate_alert_subscription(db: Session, subscription_id: UUID) -> bool:
    """Deactivate an alert subscription"""
    subscription = (
        db.query(AlertSubscription)
        .filter(AlertSubscription.id == subscription_id)
        .first()
    )

    if not subscription:
        return False

    subscription.is_active = False
    db.commit()
    return True


def get_all_active_subscriptions(db: Session) -> List[AlertSubscription]:
    """Get all active alert subscriptions"""
    return db.query(AlertSubscription).filter(AlertSubscription.is_active == True).all()


def get_subscriptions_by_location(
    db: Session, latitude: float, longitude: float, radius_km: float
) -> List[AlertSubscription]:
    """Get subscriptions within a geographic radius"""
    # This would need to be implemented with proper geographic queries
    # For now, return all active subscriptions
    return get_all_active_subscriptions(db)


def create_alert_history(
    db: Session,
    subscription_id: UUID,
    alert_type: str,
    title: str,
    message: Optional[str] = None,
    bleaching_count: Optional[int] = None,
    affected_area: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> AlertHistory:
    """Create a new alert history record"""
    alert_history = AlertHistory(
        subscription_id=subscription_id,
        alert_type=alert_type,
        title=title,
        message=message,
        bleaching_count=bleaching_count,
        affected_area=affected_area,
        latitude=latitude,
        longitude=longitude,
        delivery_status="pending",
    )

    db.add(alert_history)
    db.commit()
    db.refresh(alert_history)
    return alert_history


def get_alert_history_by_subscription(
    db: Session, subscription_id: UUID, limit: int = 50, offset: int = 0
) -> List[AlertHistory]:
    """Get alert history for a subscription"""
    return (
        db.query(AlertHistory)
        .filter(AlertHistory.subscription_id == subscription_id)
        .order_by(AlertHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def update_alert_delivery_status(
    db: Session, alert_id: UUID, email_sent: bool, delivery_status: str
) -> bool:
    """Update alert delivery status"""
    alert = db.query(AlertHistory).filter(AlertHistory.id == alert_id).first()

    if not alert:
        return False

    alert.email_sent = email_sent
    alert.delivery_status = delivery_status

    if email_sent:
        from datetime import datetime

        alert.email_sent_at = datetime.utcnow()

    db.commit()
    return True


def get_alert_statistics(db: Session) -> dict:
    """Get alert system statistics"""
    total_subscriptions = (
        db.query(AlertSubscription).filter(AlertSubscription.is_active == True).count()
    )

    total_alerts = db.query(AlertHistory).count()

    alerts_sent = db.query(AlertHistory).filter(AlertHistory.email_sent == True).count()

    # Get alerts by type
    threshold_alerts = (
        db.query(AlertHistory)
        .filter(AlertHistory.alert_type == "threshold_reached")
        .count()
    )

    weekly_reports = (
        db.query(AlertHistory)
        .filter(AlertHistory.alert_type == "weekly_report")
        .count()
    )

    monthly_reports = (
        db.query(AlertHistory)
        .filter(AlertHistory.alert_type == "monthly_report")
        .count()
    )

    return {
        "total_active_subscriptions": total_subscriptions,
        "total_alerts_generated": total_alerts,
        "alerts_successfully_sent": alerts_sent,
        "delivery_success_rate": (
            (alerts_sent / total_alerts * 100) if total_alerts > 0 else 0
        ),
        "alerts_by_type": {
            "threshold_reached": threshold_alerts,
            "weekly_reports": weekly_reports,
            "monthly_reports": monthly_reports,
        },
    }
