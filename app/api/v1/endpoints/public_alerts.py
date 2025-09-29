from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, desc

from app.db.connection import get_db
from app.models.public_alerts import PublicBleachingAlert, PublicAlertHistory
from app.models.coral_images import CoralImages
from app.models.analysis_results import AnalysisResult
from app.schemas.public_alerts import (
    PublicBleachingAlert as PublicBleachingAlertSchema,
    PublicAlertSummary,
    PublicAlertStats,
    PublicAlertCreate,
    PublicAlertUpdate,
)
from app.core.auth import get_current_user
from app.models.users import User

router = APIRouter()


# Public endpoints (no authentication required)
@router.get("/alerts", response_model=List[PublicBleachingAlertSchema])
async def get_public_alerts(
    active_only: bool = True,
    severity_level: Optional[str] = None,
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Get all public bleaching alerts (no authentication required)"""
    query = db.query(PublicBleachingAlert)

    if active_only:
        query = query.filter(PublicBleachingAlert.is_active == True)

    if severity_level:
        query = query.filter(PublicBleachingAlert.severity_level == severity_level)

    alerts = (
        query.order_by(desc(PublicBleachingAlert.created_at))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return alerts


@router.get("/alerts/summary", response_model=PublicAlertSummary)
async def get_public_alert_summary(db: Session = Depends(get_db)):
    """Get summary of all public alerts (no authentication required)"""
    # Get active alerts count
    total_active = (
        db.query(PublicBleachingAlert)
        .filter(PublicBleachingAlert.is_active == True)
        .count()
    )

    # Get alerts by severity
    critical_alerts = (
        db.query(PublicBleachingAlert)
        .filter(
            and_(
                PublicBleachingAlert.is_active == True,
                PublicBleachingAlert.severity_level == "critical",
            )
        )
        .count()
    )

    high_alerts = (
        db.query(PublicBleachingAlert)
        .filter(
            and_(
                PublicBleachingAlert.is_active == True,
                PublicBleachingAlert.severity_level == "high",
            )
        )
        .count()
    )

    medium_alerts = (
        db.query(PublicBleachingAlert)
        .filter(
            and_(
                PublicBleachingAlert.is_active == True,
                PublicBleachingAlert.severity_level == "medium",
            )
        )
        .count()
    )

    low_alerts = (
        db.query(PublicBleachingAlert)
        .filter(
            and_(
                PublicBleachingAlert.is_active == True,
                PublicBleachingAlert.severity_level == "low",
            )
        )
        .count()
    )

    return PublicAlertSummary(
        total_active_alerts=total_active,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        medium_alerts=medium_alerts,
        low_alerts=low_alerts,
        last_updated=datetime.utcnow(),
    )


@router.get("/alerts/stats", response_model=PublicAlertStats)
async def get_public_alert_stats(db: Session = Depends(get_db)):
    """Get public bleaching statistics (no authentication required)"""
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Get bleaching cases for different time periods
    today_cases = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= today,
                AnalysisResult.bleaching_percentage > 0,
            )
        )
        .scalar()
    )

    week_cases = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= week_ago,
                AnalysisResult.bleaching_percentage > 0,
            )
        )
        .scalar()
    )

    month_cases = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= month_ago,
                AnalysisResult.bleaching_percentage > 0,
            )
        )
        .scalar()
    )

    # Get severity distribution for the last 30 days
    high_severity = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= month_ago,
                AnalysisResult.bleaching_percentage >= 50,
            )
        )
        .scalar()
    )

    medium_severity = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= month_ago,
                AnalysisResult.bleaching_percentage >= 25,
                AnalysisResult.bleaching_percentage < 50,
            )
        )
        .scalar()
    )

    low_severity = (
        db.query(func.count(AnalysisResult.id))
        .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
        .filter(
            and_(
                AnalysisResult.analyzed_at >= month_ago,
                AnalysisResult.bleaching_percentage > 0,
                AnalysisResult.bleaching_percentage < 25,
            )
        )
        .scalar()
    )

    # Get most affected areas (simplified - would need more complex query for real implementation)
    most_affected_areas = [
        {"area": "Manila Bay, Philippines", "cases": 150},
        {"area": "Great Barrier Reef, Australia", "cases": 89},
        {"area": "Caribbean Sea", "cases": 67},
    ]

    return PublicAlertStats(
        total_bleaching_cases_today=today_cases or 0,
        total_bleaching_cases_this_week=week_cases or 0,
        total_bleaching_cases_this_month=month_cases or 0,
        most_affected_areas=most_affected_areas,
        severity_distribution={
            "high": high_severity or 0,
            "medium": medium_severity or 0,
            "low": low_severity or 0,
        },
        last_updated=datetime.utcnow(),
    )


@router.get("/alerts/{alert_id}", response_model=PublicBleachingAlertSchema)
async def get_public_alert_by_id(alert_id: str, db: Session = Depends(get_db)):
    """Get a specific public alert by ID (no authentication required)"""
    alert = (
        db.query(PublicBleachingAlert)
        .filter(PublicBleachingAlert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public alert not found",
        )

    return alert


# Admin endpoints (authentication required)
@router.post("/admin/alerts", response_model=PublicBleachingAlertSchema)
async def create_public_alert(
    alert_data: PublicAlertCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new public alert (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        alert = PublicBleachingAlert(
            area_name=alert_data.area_name,
            latitude=alert_data.latitude,
            longitude=alert_data.longitude,
            bleaching_count=alert_data.bleaching_count,
            threshold=alert_data.threshold,
            affected_radius_km=alert_data.affected_radius_km,
            severity_level=alert_data.severity_level,
            description=alert_data.description,
        )

        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Create history record
        history = PublicAlertHistory(
            alert_id=alert.id,
            change_type="created",
            description=f"Public alert created for {alert_data.area_name}",
        )
        db.add(history)
        db.commit()

        return alert

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create public alert: {str(e)}",
        )


@router.put("/admin/alerts/{alert_id}", response_model=PublicBleachingAlertSchema)
async def update_public_alert(
    alert_id: str,
    alert_update: PublicAlertUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a public alert (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    alert = (
        db.query(PublicBleachingAlert)
        .filter(PublicBleachingAlert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public alert not found",
        )

    try:
        # Track changes for history
        changes = []
        update_data = alert_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            old_value = getattr(alert, field)
            if old_value != value:
                changes.append(f"{field}: {old_value} -> {value}")
                setattr(alert, field, value)

        if changes:
            alert.last_updated = datetime.utcnow()
            db.commit()
            db.refresh(alert)

            # Create history record
            history = PublicAlertHistory(
                alert_id=alert.id,
                change_type="updated",
                description=f"Alert updated: {', '.join(changes)}",
            )
            db.add(history)
            db.commit()

        return alert

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update public alert: {str(e)}",
        )


@router.delete("/admin/alerts/{alert_id}")
async def deactivate_public_alert(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Deactivate a public alert (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    alert = (
        db.query(PublicBleachingAlert)
        .filter(PublicBleachingAlert.id == alert_id)
        .first()
    )

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public alert not found",
        )

    try:
        alert.is_active = False
        alert.last_updated = datetime.utcnow()
        db.commit()

        # Create history record
        history = PublicAlertHistory(
            alert_id=alert.id,
            change_type="deactivated",
            description=f"Alert deactivated for {alert.area_name}",
        )
        db.add(history)
        db.commit()

        return {"message": "Public alert deactivated successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deactivate public alert: {str(e)}",
        )


@router.get("/admin/alerts", response_model=List[PublicBleachingAlertSchema])
async def get_all_public_alerts_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all public alerts (admin only)"""
    # Check if user is admin
    if current_user.role < 2:  # Assuming 2 is admin role
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    alerts = (
        db.query(PublicBleachingAlert)
        .order_by(desc(PublicBleachingAlert.created_at))
        .all()
    )

    return alerts
