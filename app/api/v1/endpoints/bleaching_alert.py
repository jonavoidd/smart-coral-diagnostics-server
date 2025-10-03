import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.bleaching_alert import (
    BleachingAlertOut,
    CreateBleachingAlert,
    UpdateBleachingAlert,
    BleachingAlertSummary,
    AlertFilterParams,
)
from app.schemas.user import UserOut
from app.services.bleaching_alert_service import bleaching_alert_service
from app.crud.bleaching_alert import (
    get_alert_by_id,
    get_all_alerts,
    get_active_alerts,
    resolve_alert,
    delete_alert,
)

router = APIRouter()
logger = logging.getLogger(__name__)
LOG_MSG = "Endpoint:"


@router.post("/generate", response_model=List[BleachingAlertOut])
def generate_alerts(
    min_bleached_count: int = Query(
        default=200, ge=1, description="Minimum bleached corals to trigger alert"
    ),
    cluster_radius_km: float = Query(
        default=50.0, ge=0.1, le=200, description="Cluster radius in kilometers"
    ),
    regenerate_existing: bool = Query(
        default=False, description="Regenerate existing alerts"
    ),
    db: Session = Depends(get_db),
    # current_user: UserOut = Depends(
    #     require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    # ),
):
    """
    Generate bleaching alerts based on current coral image data.
    Requires admin privileges.
    """
    try:
        return bleaching_alert_service.generate_alerts(
            db,
            min_bleached_count=min_bleached_count,
            cluster_radius_km=cluster_radius_km,
            regenerate_existing=regenerate_existing,
        )
    except Exception as e:
        logger.error(f"{LOG_MSG} error generating alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate alerts",
        )


@router.post("/generate-test", response_model=List[BleachingAlertOut])
def generate_test_alerts(
    min_bleached_count: int = Query(
        default=5, ge=1, description="Minimum bleached corals for testing"
    ),
    cluster_radius_km: float = Query(
        default=50.0, ge=0.1, le=200, description="Cluster radius in kilometers"
    ),
    db: Session = Depends(get_db),
):
    """
    Generate bleaching alerts with lower thresholds for testing purposes.
    This endpoint allows any authenticated user to test alert generation.
    """
    try:
        logger.info(
            f"{LOG_MSG} generating test alerts with threshold of {min_bleached_count}"
        )
        return bleaching_alert_service.generate_alerts(
            db,
            min_bleached_count=min_bleached_count,
            cluster_radius_km=cluster_radius_km,
            regenerate_existing=True,  # Always regenerate for testing
        )
    except Exception as e:
        logger.error(f"{LOG_MSG} error generating test alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate test alerts: {str(e)}",
        )


@router.get("/debug/raw-data")
def get_raw_bleaching_data(db: Session = Depends(get_db)):
    """
    Debug endpoint to see ALL coral images and their analysis results
    No authentication required for testing
    """
    try:
        from app.models.coral_images import CoralImages
        from app.models.analysis_results import AnalysisResult

        # Get ALL coral images with analysis results
        query = db.query(
            CoralImages.id,
            CoralImages.latitude,
            CoralImages.longitude,
            CoralImages.is_public,
            AnalysisResult.bleaching_percentage,
            AnalysisResult.classification_labels,
            AnalysisResult.confidence_score,
        ).outerjoin(AnalysisResult, CoralImages.id == AnalysisResult.image_id)

        all_corals = query.all()

        # Categorize the data
        with_location = []
        without_location = []
        with_analysis = []
        without_analysis = []
        potentially_bleached = []

        for coral in all_corals:
            coral_data = {
                "id": str(coral.id),
                "latitude": coral.latitude,
                "longitude": coral.longitude,
                "is_public": coral.is_public,
                "bleaching_percentage": coral.bleaching_percentage,
                "classification": coral.classification_labels,
                "confidence": coral.confidence_score,
            }

            # Check location
            if coral.latitude is not None and coral.longitude is not None:
                with_location.append(coral_data)
            else:
                without_location.append(coral_data)

            # Check analysis
            if coral.classification_labels is not None:
                with_analysis.append(coral_data)
            else:
                without_analysis.append(coral_data)

            # Check if potentially bleached
            if coral.classification_labels and coral.bleaching_percentage is not None:
                potentially_bleached.append(coral_data)

        return {
            "summary": {
                "total_corals": len(all_corals),
                "with_location": len(with_location),
                "without_location": len(without_location),
                "with_analysis": len(with_analysis),
                "without_analysis": len(without_analysis),
                "potentially_bleached": len(potentially_bleached),
            },
            "sample_data": {
                "with_location": with_location[:5],
                "with_analysis": with_analysis[:5],
                "potentially_bleached": potentially_bleached[:5],
            },
            "all_classifications": list(
                set(
                    [
                        c.classification_labels
                        for c in all_corals
                        if c.classification_labels
                    ]
                )
            ),
            "bleaching_percentages": [
                c.bleaching_percentage
                for c in all_corals
                if c.bleaching_percentage is not None
            ][:10],
        }

    except Exception as e:
        logger.error(f"{LOG_MSG} error getting raw data: {str(e)}")
        import traceback

        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/", response_model=List[BleachingAlertOut])
def get_alerts(
    severity_level: Optional[str] = Query(None, description="Filter by severity level"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    min_bleached_count: Optional[int] = Query(
        None, ge=0, description="Minimum bleached count"
    ),
    limit: Optional[int] = Query(100, ge=1, le=1000),
    offset: Optional[int] = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Get all bleaching alerts with optional filtering.
    Public endpoint.
    """
    try:
        filters = AlertFilterParams(
            severity_level=severity_level,
            is_active=is_active,
            min_bleached_count=min_bleached_count,
        )

        alerts = get_all_alerts(db, filters=filters, limit=limit, offset=offset)
        return [BleachingAlertOut.model_validate(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alerts",
        )


@router.get("/active", response_model=List[BleachingAlertOut])
def get_active_alerts_endpoint(db: Session = Depends(get_db)):
    """
    Get all active bleaching alerts.
    Public endpoint.
    """
    try:
        alerts = get_active_alerts(db)
        return [BleachingAlertOut.model_validate(alert) for alert in alerts]
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting active alerts: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve active alerts",
        )


@router.get("/summary", response_model=BleachingAlertSummary)
def get_alert_summary_endpoint(db: Session = Depends(get_db)):
    """
    Get comprehensive alert summary with statistics.
    Public endpoint.
    """
    try:
        return bleaching_alert_service.get_alert_summary(db)
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting alert summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert summary",
        )


@router.get("/{alert_id}", response_model=BleachingAlertOut)
def get_alert(alert_id: UUID, db: Session = Depends(get_db)):
    """
    Get a specific alert by ID.
    Public endpoint.
    """
    try:
        alert = get_alert_by_id(db, alert_id)
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )
        return BleachingAlertOut.model_validate(alert)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert",
        )


@router.patch("/{alert_id}/resolve")
def resolve_alert_endpoint(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """
    Mark an alert as resolved.
    Requires admin privileges.
    """
    try:
        success = resolve_alert(db, alert_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )
        return {"message": "Alert resolved successfully", "alert_id": str(alert_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_MSG} error resolving alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve alert",
        )


@router.delete("/{alert_id}")
def delete_alert_endpoint(
    alert_id: UUID,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    """
    Delete an alert.
    Requires super admin privileges.
    """
    try:
        success = delete_alert(db, alert_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
            )
        return {"message": "Alert deleted successfully", "alert_id": str(alert_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"{LOG_MSG} error deleting alert: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert",
        )
