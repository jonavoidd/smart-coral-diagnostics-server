import logging
from datetime import datetime, timedelta
from celery import shared_task
from sqlalchemy.orm import Session

from app.db.connection import get_db
from app.services.alert_service import alert_service

logger = logging.getLogger(__name__)


@shared_task
def check_bleaching_thresholds():
    """
    Check for areas that have reached bleaching thresholds and send alerts.
    This task should run frequently (every 15-30 minutes) to provide near real-time alerts.
    """
    try:
        db = next(get_db())

        # Get all areas that have reached thresholds
        alert_data_list = alert_service.check_bleaching_thresholds(db)

        if not alert_data_list:
            logger.info("No bleaching thresholds reached")
            return {"status": "success", "alerts_sent": 0}

        # Create/update public alerts for public display
        public_alerts_created = 0
        for alert_data in alert_data_list:
            public_alert = alert_service.create_or_update_public_alert(db, alert_data)
            if public_alert:
                public_alerts_created += 1
                logger.info(f"Public alert created/updated for {alert_data.area_name}")

                # Broadcast real-time notification to WebSocket clients
                try:
                    from app.api.v1.websocket_alerts import broadcast_new_alert
                    import asyncio

                    # Prepare alert data for WebSocket broadcast
                    websocket_alert_data = {
                        "id": str(public_alert.id),
                        "area_name": public_alert.area_name,
                        "latitude": public_alert.latitude,
                        "longitude": public_alert.longitude,
                        "bleaching_count": public_alert.bleaching_count,
                        "threshold": public_alert.threshold,
                        "severity_level": public_alert.severity_level,
                        "affected_radius_km": public_alert.affected_radius_km,
                        "created_at": public_alert.created_at.isoformat(),
                        "last_updated": public_alert.last_updated.isoformat(),
                        "is_active": public_alert.is_active,
                    }

                    # Broadcast to WebSocket clients
                    asyncio.create_task(broadcast_new_alert(websocket_alert_data))
                    logger.info(
                        f"Real-time alert broadcast sent for {alert_data.area_name}"
                    )

                except Exception as e:
                    logger.error(f"Failed to broadcast real-time alert: {str(e)}")

        # Get all active subscriptions
        from app.models.alert_subscriptions import AlertSubscription

        subscriptions = (
            db.query(AlertSubscription)
            .filter(AlertSubscription.is_active == True)
            .all()
        )

        alerts_sent = 0
        for subscription in subscriptions:
            # Check if this subscription's area has reached threshold
            for alert_data in alert_data_list:
                if (
                    subscription.latitude
                    and subscription.longitude
                    and alert_data.latitude
                    and alert_data.longitude
                ):

                    # Calculate distance between subscription and alert area
                    distance = alert_service.calculate_distance(
                        subscription.latitude,
                        subscription.longitude,
                        alert_data.latitude,
                        alert_data.longitude,
                    )

                    # If within monitoring radius, send alert
                    if distance <= (subscription.radius_km or 50.0):
                        success = await alert_service.send_bleaching_alert(
                            db, subscription, alert_data
                        )
                        if success:
                            alerts_sent += 1
                            logger.info(f"Alert sent to {subscription.email}")

        logger.info(
            f"Bleaching threshold check completed. {alerts_sent} alerts sent, {public_alerts_created} public alerts created/updated."
        )
        return {
            "status": "success",
            "alerts_sent": alerts_sent,
            "public_alerts_created": public_alerts_created,
        }

    except Exception as e:
        logger.error(f"Error checking bleaching thresholds: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def send_weekly_bleaching_reports():
    """
    Send weekly bleaching reports to all subscribers.
    This task runs every Sunday at 9 AM.
    """
    try:
        db = next(get_db())

        success = await alert_service.send_weekly_report(db)

        if success:
            logger.info("Weekly bleaching reports sent successfully")
            return {"status": "success", "message": "Weekly reports sent"}
        else:
            logger.error("Failed to send weekly reports")
            return {"status": "error", "message": "Failed to send weekly reports"}

    except Exception as e:
        logger.error(f"Error sending weekly reports: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def send_monthly_bleaching_reports():
    """
    Send monthly bleaching reports to all subscribers.
    This task runs on the 1st of every month at 10 AM.
    """
    try:
        db = next(get_db())

        success = await alert_service.send_monthly_report(db)

        if success:
            logger.info("Monthly bleaching reports sent successfully")
            return {"status": "success", "message": "Monthly reports sent"}
        else:
            logger.error("Failed to send monthly reports")
            return {"status": "error", "message": "Failed to send monthly reports"}

    except Exception as e:
        logger.error(f"Error sending monthly reports: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def cleanup_old_alert_history():
    """
    Clean up old alert history records to keep the database size manageable.
    Keeps only the last 6 months of alert history.
    """
    try:
        db = next(get_db())

        # Delete alert history older than 6 months
        cutoff_date = datetime.utcnow() - timedelta(days=180)

        from app.models.alert_subscriptions import AlertHistory

        deleted_count = (
            db.query(AlertHistory)
            .filter(AlertHistory.created_at < cutoff_date)
            .delete()
        )

        db.commit()

        logger.info(f"Cleaned up {deleted_count} old alert history records")
        return {"status": "success", "deleted_count": deleted_count}

    except Exception as e:
        logger.error(f"Error cleaning up alert history: {str(e)}")
        return {"status": "error", "message": str(e)}


@shared_task
def generate_bleaching_statistics():
    """
    Generate comprehensive bleaching statistics for reporting.
    This can be used for dashboard data and trend analysis.
    """
    try:
        db = next(get_db())

        # Get statistics for the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        from app.models.coral_images import CoralImages
        from app.models.analysis_results import AnalysisResult
        from sqlalchemy import func

        # Total bleaching cases in last 30 days
        total_cases = (
            db.query(func.count(AnalysisResult.id))
            .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
            .filter(
                AnalysisResult.analyzed_at >= thirty_days_ago,
                AnalysisResult.bleaching_percentage > 0,
            )
            .scalar()
        )

        # Cases by severity
        high_severity = (
            db.query(func.count(AnalysisResult.id))
            .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
            .filter(
                AnalysisResult.analyzed_at >= thirty_days_ago,
                AnalysisResult.bleaching_percentage >= 50,
            )
            .scalar()
        )

        medium_severity = (
            db.query(func.count(AnalysisResult.id))
            .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
            .filter(
                AnalysisResult.analyzed_at >= thirty_days_ago,
                AnalysisResult.bleaching_percentage >= 25,
                AnalysisResult.bleaching_percentage < 50,
            )
            .scalar()
        )

        low_severity = (
            db.query(func.count(AnalysisResult.id))
            .join(CoralImages, AnalysisResult.image_id == CoralImages.id)
            .filter(
                AnalysisResult.analyzed_at >= thirty_days_ago,
                AnalysisResult.bleaching_percentage > 0,
                AnalysisResult.bleaching_percentage < 25,
            )
            .scalar()
        )

        statistics = {
            "total_cases": total_cases or 0,
            "high_severity": high_severity or 0,
            "medium_severity": medium_severity or 0,
            "low_severity": low_severity or 0,
            "period_days": 30,
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Generated bleaching statistics: {statistics}")
        return {"status": "success", "statistics": statistics}

    except Exception as e:
        logger.error(f"Error generating bleaching statistics: {str(e)}")
        return {"status": "error", "message": str(e)}
