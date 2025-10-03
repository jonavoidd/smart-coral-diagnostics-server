import logging

from datetime import datetime, timezone
from sqlalchemy import select, delete, update, and_, or_, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from uuid import UUID

from app.models.bleaching_alerts import BleachingAlert
from app.schemas.bleaching_alert import (
    CreateBleachingAlert,
    UpdateBleachingAlert,
    AlertFilterParams,
)

logger = logging.getLogger(__name__)
LOG_MSG = "CRUD:"


def create_alert(
    db: Session, payload: CreateBleachingAlert
) -> Optional[BleachingAlert]:
    """Create a new bleaching alert"""

    # Convert the payload to dict
    alert_data = payload.model_dump()

    # CRITICAL: Ensure affected_coral_ids are strings for JSONB storage
    if alert_data.get("affected_coral_ids"):
        # Convert each item to string, handling both UUID objects and strings
        coral_ids = alert_data["affected_coral_ids"]
        if isinstance(coral_ids, list):
            alert_data["affected_coral_ids"] = [str(cid) for cid in coral_ids]
        elif coral_ids is not None:
            # If it's a single value, convert to list of string
            alert_data["affected_coral_ids"] = [str(coral_ids)]
    else:
        alert_data["affected_coral_ids"] = []

    # Log for debugging
    logger.info(
        f"{LOG_MSG} Creating alert with coral_ids type: {type(alert_data.get('affected_coral_ids'))}"
    )
    if alert_data.get("affected_coral_ids"):
        logger.info(
            f"{LOG_MSG} First coral_id type: {type(alert_data['affected_coral_ids'][0])}"
        )

    alert = BleachingAlert(**alert_data)

    try:
        db.add(alert)
        db.commit()
        db.refresh(alert)

        logger.info(
            f"{LOG_MSG} created new bleaching alert at ({alert.latitude}, {alert.longitude})"
        )
        return alert
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error creating bleaching alert: {str(e)}")
        import traceback

        logger.error(traceback.format_exc())
        raise


def get_alert_by_id(db: Session, alert_id: UUID) -> Optional[BleachingAlert]:
    """Get a single alert by ID"""
    query = select(BleachingAlert).where(BleachingAlert.id == alert_id)

    try:
        result = db.execute(query)
        return result.scalar_one_or_none()
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting alert by id: {str(e)}")
        return None


def get_all_alerts(
    db: Session,
    filters: Optional[AlertFilterParams] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = 0,
) -> List[BleachingAlert]:
    """Get all alerts with optional filtering"""
    query = select(BleachingAlert)

    if filters:
        conditions = []

        if filters.severity_level:
            conditions.append(BleachingAlert.severity_level == filters.severity_level)

        if filters.is_active is not None:
            conditions.append(BleachingAlert.is_active == filters.is_active)

        if filters.min_bleached_count:
            conditions.append(
                BleachingAlert.bleached_count >= filters.min_bleached_count
            )

        if filters.min_bleaching_percentage:
            conditions.append(
                BleachingAlert.average_bleaching_percentage
                >= filters.min_bleaching_percentage
            )

        if filters.latitude_min is not None:
            conditions.append(BleachingAlert.latitude >= filters.latitude_min)

        if filters.latitude_max is not None:
            conditions.append(BleachingAlert.latitude <= filters.latitude_max)

        if filters.longitude_min is not None:
            conditions.append(BleachingAlert.longitude >= filters.longitude_min)

        if filters.longitude_max is not None:
            conditions.append(BleachingAlert.longitude <= filters.longitude_max)

        if filters.start_date:
            conditions.append(BleachingAlert.first_detected_at >= filters.start_date)

        if filters.end_date:
            conditions.append(BleachingAlert.first_detected_at <= filters.end_date)

        if conditions:
            query = query.where(and_(*conditions))

    query = query.order_by(BleachingAlert.last_updated_at.desc())

    if limit:
        query = query.limit(limit).offset(offset)

    try:
        result = db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting all alerts: {str(e)}")
        return []


def get_active_alerts(db: Session) -> List[BleachingAlert]:
    """Get all active alerts"""
    query = select(BleachingAlert).where(BleachingAlert.is_active == True)

    try:
        result = db.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting active alerts: {str(e)}")
        return []


def get_alerts_by_location(
    db: Session, latitude: float, longitude: float, radius_km: float = 50.0
) -> List[BleachingAlert]:
    """
    Get alerts within a radius of a location using simple bounding box
    For accurate distance calculation, we do it in the service layer
    """
    # Approximate degrees per kilometer
    # At the equator: 1 degree latitude ≈ 111 km
    lat_range = radius_km / 111.0

    # For longitude, we need to account for latitude
    # At the equator, 1 degree longitude ≈ 111 km
    # As we move away from equator, this decreases by cos(latitude)
    import math

    lon_range = radius_km / (111.0 * abs(math.cos(math.radians(latitude))))

    query = select(BleachingAlert).where(
        and_(
            BleachingAlert.latitude.between(latitude - lat_range, latitude + lat_range),
            BleachingAlert.longitude.between(
                longitude - lon_range, longitude + lon_range
            ),
        )
    )

    try:
        result = db.execute(query)
        alerts = result.scalars().all()

        # Now filter by actual distance using Haversine formula
        from app.services.bleaching_alert_service import BleachingAlertService

        filtered_alerts = []
        for alert in alerts:
            distance = BleachingAlertService.calculate_distance(
                latitude, longitude, alert.latitude, alert.longitude
            )
            if distance <= radius_km:
                filtered_alerts.append(alert)

        return filtered_alerts
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting alerts by location: {str(e)}")
        return []


def update_alert(
    db: Session, alert_id: UUID, payload: UpdateBleachingAlert
) -> Optional[BleachingAlert]:
    """Update an existing alert"""
    update_data = payload.model_dump(exclude_unset=True)
    update_data["last_updated_at"] = datetime.now(timezone.utc)

    # CRITICAL: Ensure affected_coral_ids are strings for JSONB storage
    if "affected_coral_ids" in update_data and update_data["affected_coral_ids"]:
        coral_ids = update_data["affected_coral_ids"]
        if isinstance(coral_ids, list):
            update_data["affected_coral_ids"] = [str(cid) for cid in coral_ids]

    query = (
        update(BleachingAlert)
        .where(BleachingAlert.id == alert_id)
        .values(**update_data)
        .returning(BleachingAlert)
    )

    try:
        result = db.execute(query)
        db.commit()

        updated_alert = result.scalar_one_or_none()
        if updated_alert:
            logger.info(f"{LOG_MSG} updated bleaching alert {alert_id}")
        return updated_alert
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error updating alert: {str(e)}")
        raise


def resolve_alert(db: Session, alert_id: UUID) -> bool:
    """Mark an alert as resolved"""
    query = (
        update(BleachingAlert)
        .where(BleachingAlert.id == alert_id)
        .values(
            is_active=False,
            resolved_at=datetime.now(timezone.utc),
            last_updated_at=datetime.now(timezone.utc),
        )
    )

    try:
        result = db.execute(query)
        db.commit()

        if result.rowcount > 0:
            logger.info(f"{LOG_MSG} resolved alert {alert_id}")
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error resolving alert: {str(e)}")
        return False


def delete_alert(db: Session, alert_id: UUID) -> bool:
    """Delete an alert"""
    query = delete(BleachingAlert).where(BleachingAlert.id == alert_id)

    try:
        result = db.execute(query)
        db.commit()

        if result.rowcount > 0:
            logger.info(f"{LOG_MSG} deleted alert {alert_id}")
            return True
        return False
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"{LOG_MSG} error deleting alert: {str(e)}")
        return False


def get_alert_statistics(db: Session) -> dict:
    """Get summary statistics for all alerts"""
    try:
        total_alerts = db.query(func.count(BleachingAlert.id)).scalar()
        active_alerts = (
            db.query(func.count(BleachingAlert.id))
            .filter(BleachingAlert.is_active == True)
            .scalar()
        )

        severity_counts = (
            db.query(BleachingAlert.severity_level, func.count(BleachingAlert.id))
            .group_by(BleachingAlert.severity_level)
            .all()
        )

        severity_dict = {level: count for level, count in severity_counts}

        avg_bleaching = (
            db.query(func.avg(BleachingAlert.average_bleaching_percentage)).scalar()
            or 0.0
        )

        total_affected = db.query(func.sum(BleachingAlert.bleached_count)).scalar() or 0

        return {
            "total_alerts": total_alerts or 0,
            "active_alerts": active_alerts or 0,
            "resolved_alerts": (total_alerts or 0) - (active_alerts or 0),
            "critical_alerts": severity_dict.get("critical", 0),
            "high_alerts": severity_dict.get("high", 0),
            "moderate_alerts": severity_dict.get("moderate", 0),
            "low_alerts": severity_dict.get("low", 0),
            "total_affected_corals": total_affected,
            "average_bleaching_percentage": round(float(avg_bleaching), 2),
        }
    except SQLAlchemyError as e:
        logger.error(f"{LOG_MSG} error getting alert statistics: {str(e)}")
        return {}
