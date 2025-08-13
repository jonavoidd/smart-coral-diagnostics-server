import logging

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.coral_images import get_all_images_with_results


logger = logging.getLogger(__name__)


def trend_result(db: Session):
    try:
        coral_images = get_all_images_with_results(db)
        if not coral_images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no coral data found"
            )

        now = datetime.now()
        one_month_ago = now - timedelta(days=30)

        total_images = len(coral_images)
        healthy_count = 0
        bleached_count = 0
        other_count = 0
        recent_images_count = 0
        recent_healthy = 0
        recent_bleached = 0

        locations = defaultdict(
            lambda: {
                "total": 0,
                "healthy": 0,
                "bleached": 0,
                "other": 0,
                "coordinates": None,
            }
        )

        for image in coral_images:
            if image.latitude is not None and image.longitude is not None:
                lat = round(image.latitude, 4)
                lng = round(image.longitude, 4)
                loc_key = f"{lat}, {lng}"

                if loc_key not in locations:
                    locations[loc_key]["coordinates"] = {
                        "latitude": lat,
                        "longitude": lng,
                    }

                locations[loc_key]["total"] += 1

            is_recent = image.uploaded_at and image.uploaded_at >= one_month_ago
            if is_recent:
                recent_images_count += 1

            if image.analysis_results:
                result = image.analysis_results[0]
                label = result.classification_labels.lower()

                if label == "healthy":
                    healthy_count += 1

                    if is_recent:
                        recent_healthy += 1
                    if loc_key:
                        locations["loc_key"]["healthy"] += 1

                elif label in ("unhealthy", "bleached", "dead"):
                    bleached_count += 1

                    if is_recent:
                        recent_bleached += 1
                    if loc_key:
                        locations[loc_key]["bleached"] += 1

                else:
                    other_count += 1
                    if loc_key:
                        locations[loc_key]["other"] += 1

        # calculate percentages on this part
        healthy_percent = (
            (healthy_count / total_images) * 100 if total_images > 0 else 0
        )
        bleached_percent = (
            (bleached_count / total_images) * 100 if total_images > 0 else 0
        )
        other_percent = (other_count / total_images) * 100 if total_images > 0 else 0
        recent_percent = (
            (recent_images_count / total_images) * 100 if total_images > 0 else 0
        )

        active_locations = []
        for loc_data in locations.values():
            if loc_data["coordinates"]:
                active_locations.append(
                    {
                        "coordinates": loc_data["coordinates"],
                        "total_images": loc_data["total"],
                        "healthy": loc_data["healthy"],
                        "bleached": loc_data["bleached"],
                        "other": loc_data["other"],
                        "health_percentage": (
                            round((loc_data["healthy"] / loc_data["total"]) * 100, 2)
                            if loc_data["total"] > 0
                            else 0
                        ),
                    }
                )

        return {
            "total_images": total_images,
            "healthy_count": healthy_count,
            "bleached_count": bleached_count,
            "other_count": other_count,
            "healthy_percent": round(healthy_percent, 2),
            "bleached_percent": round(bleached_percent, 2),
            "other_percent": round(other_percent, 2),
            "recent_images": {
                "count": recent_images_count,
                "percent": round(recent_percent, 2),
                "healthy": recent_healthy,
                "bleached": recent_bleached,
            },
            "active_locations": active_locations,
            "health_trend": (
                "improving" if healthy_percent > bleached_percent else "declining"
            ),
        }

    except Exception as e:
        logger.error(f"Service: error calculating for trend results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to calculate for trend",
        )
