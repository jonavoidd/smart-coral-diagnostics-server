from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.connection import get_db
from app.models.alert_subscriptions import AlertSubscription, AlertHistory
from app.schemas.alert_subscription import (
    AlertSubscriptionCreate,
    AlertSubscriptionUpdate,
    AlertSubscriptionResponse,
    AlertHistoryResponse,
)
from app.core.auth import get_current_user
from app.models.users import User

router = APIRouter()


@router.post("/subscribe", response_model=AlertSubscriptionResponse)
async def create_alert_subscription(
    subscription_data: AlertSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new alert subscription for the current user"""
    try:
        # Check if user already has an active subscription
        existing_subscription = (
            db.query(AlertSubscription)
            .filter(
                and_(
                    AlertSubscription.user_id == current_user.id,
                    AlertSubscription.is_active == True,
                )
            )
            .first()
        )

        if existing_subscription:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User already has an active alert subscription",
            )

        # Create new subscription
        subscription = AlertSubscription(
            user_id=current_user.id,
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

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create alert subscription: {str(e)}",
        )


@router.get("/my-subscription", response_model=AlertSubscriptionResponse)
async def get_my_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get the current user's alert subscription"""
    subscription = (
        db.query(AlertSubscription)
        .filter(
            and_(
                AlertSubscription.user_id == current_user.id,
                AlertSubscription.is_active == True,
            )
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alert subscription found",
        )

    return subscription


@router.put("/my-subscription", response_model=AlertSubscriptionResponse)
async def update_my_subscription(
    subscription_update: AlertSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the current user's alert subscription"""
    subscription = (
        db.query(AlertSubscription)
        .filter(
            and_(
                AlertSubscription.user_id == current_user.id,
                AlertSubscription.is_active == True,
            )
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alert subscription found",
        )

    try:
        # Update fields that are provided
        update_data = subscription_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(subscription, field, value)

        db.commit()
        db.refresh(subscription)

        return subscription

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update alert subscription: {str(e)}",
        )


@router.delete("/my-subscription")
async def deactivate_my_subscription(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Deactivate the current user's alert subscription"""
    subscription = (
        db.query(AlertSubscription)
        .filter(
            and_(
                AlertSubscription.user_id == current_user.id,
                AlertSubscription.is_active == True,
            )
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alert subscription found",
        )

    try:
        subscription.is_active = False
        db.commit()

        return {"message": "Alert subscription deactivated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate alert subscription: {str(e)}",
        )


@router.get("/my-alert-history", response_model=List[AlertHistoryResponse])
async def get_my_alert_history(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the current user's alert history"""
    # Get user's subscription
    subscription = (
        db.query(AlertSubscription)
        .filter(
            and_(
                AlertSubscription.user_id == current_user.id,
                AlertSubscription.is_active == True,
            )
        )
        .first()
    )

    if not subscription:
        return []

    # Get alert history for this subscription
    alert_history = (
        db.query(AlertHistory)
        .filter(AlertHistory.subscription_id == subscription.id)
        .order_by(AlertHistory.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return alert_history


@router.get("/subscription-stats")
async def get_subscription_stats(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get statistics for the current user's alert subscription"""
    # Get user's subscription
    subscription = (
        db.query(AlertSubscription)
        .filter(
            and_(
                AlertSubscription.user_id == current_user.id,
                AlertSubscription.is_active == True,
            )
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active alert subscription found",
        )

    # Get alert statistics
    total_alerts = (
        db.query(AlertHistory)
        .filter(AlertHistory.subscription_id == subscription.id)
        .count()
    )

    alerts_sent = (
        db.query(AlertHistory)
        .filter(
            and_(
                AlertHistory.subscription_id == subscription.id,
                AlertHistory.email_sent == True,
            )
        )
        .count()
    )

    recent_alerts = (
        db.query(AlertHistory)
        .filter(AlertHistory.subscription_id == subscription.id)
        .order_by(AlertHistory.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "subscription_id": str(subscription.id),
        "total_alerts": total_alerts,
        "alerts_sent": alerts_sent,
        "delivery_rate": (alerts_sent / total_alerts * 100) if total_alerts > 0 else 0,
        "recent_alerts": [
            {
                "id": str(alert.id),
                "type": alert.alert_type,
                "title": alert.title,
                "created_at": alert.created_at,
                "email_sent": alert.email_sent,
            }
            for alert in recent_alerts
        ],
    }


# Admin endpoints for managing all subscriptions
@router.get("/admin/all-subscriptions", response_model=List[AlertSubscriptionResponse])
async def get_all_subscriptions(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get all alert subscriptions (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    subscriptions = db.query(AlertSubscription).all()
    return subscriptions


@router.get("/admin/alert-statistics")
async def get_alert_statistics(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Get overall alert system statistics (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

    # Get statistics
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
