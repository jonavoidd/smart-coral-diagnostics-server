import logging

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.coral_images import get_public_images_with_results


logger = logging.getLogger(__name__)


def trend_result(db: Session):
    try:
        coral_images = get_public_images_with_results(db)
        if not coral_images:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="no coral data found"
            )

        now = datetime.now()
        one_month_ago = now - timedelta(days=30)

        total_images = len(coral_images)
        healthy_count = 0
        bleached_count = 0
        partially_bleached_count = 0
        uncertain_count = 0
        recent_images_count = 0
        recent_healthy = 0
        recent_bleached = 0

        # Track all unique coordinates for easy access
        all_coordinates = []

        locations = defaultdict(
            lambda: {
                "total": 0,
                "healthy": 0,
                "bleached": 0,
                "partially_bleached": 0,
                "uncertain": 0,
                "coordinates": None,
                "id": None,
                "confidence_scores": [],
                "latest_analysis": None,
                "latest_upload_date": None,
            }
        )

        # Map AI model's 5 classes to schema's 4 categories
        AI_MODEL_TO_SCHEMA_MAPPING = {
            # Healthy category
            "healthy": "healthy",
            "tabular_hard_coral": "healthy",
            "tabular hard coral": "healthy",
            # Bleached categories (severe bleaching)
            "polar_white_bleaching": "bleached",
            "polar white bleaching": "bleached",
            # Partially bleached (mild to moderate bleaching)
            "slight_pale_bleaching": "partially_bleached",
            "slight pale bleaching": "partially_bleached",
            "very_pale_bleaching": "partially_bleached",
            "very pale bleaching": "partially_bleached",
        }

        processed_images = 0  # Track images with analysis results

        for image in coral_images:
            lat = None
            lng = None
            loc_key = None

            if image.latitude is not None and image.longitude is not None:
                lat = round(image.latitude, 4)
                lng = round(image.longitude, 4)
                loc_key = f"{lat},{lng}"

                # Add to all coordinates list if not already present
                coord_tuple = (lat, lng)
                if coord_tuple not in all_coordinates:
                    all_coordinates.append(coord_tuple)

                if loc_key not in locations:
                    locations[loc_key]["coordinates"] = {
                        "latitude": lat,
                        "longitude": lng,
                    }
                    locations[loc_key]["id"] = f"loc_{lat}_{lng}_{len(locations)}"

                locations[loc_key]["total"] += 1

                # Track latest upload date for this location
                upload_date = image.uploaded_at
                if (
                    locations[loc_key]["latest_upload_date"] is None
                    or upload_date > locations[loc_key]["latest_upload_date"]
                ):
                    locations[loc_key]["latest_upload_date"] = upload_date

            is_recent = image.uploaded_at and image.uploaded_at >= one_month_ago
            if is_recent:
                recent_images_count += 1

            # Process analysis results
            if image.analysis_results and len(image.analysis_results) > 0:
                processed_images += 1
                result = image.analysis_results[0]

                # Extract the raw AI model classification
                raw_classification = (
                    result.classification_labels.lower().strip()
                    if result.classification_labels
                    else ""
                )

                # Extract confidence - this might be stored differently depending on your schema
                confidence_score = getattr(result, "confidence_score", None)
                if confidence_score is None:
                    # Try to get confidence from prediction object if it exists
                    prediction = getattr(result, "prediction", None)
                    if prediction:
                        confidence_score = getattr(prediction, "confidence", 0)
                    else:
                        confidence_score = 0

                # Convert confidence to percentage if it's a decimal (0-1 range)
                if 0 <= confidence_score <= 1:
                    confidence_percentage = confidence_score * 100
                else:
                    confidence_percentage = confidence_score

                # Map AI model classification to schema category
                schema_category = AI_MODEL_TO_SCHEMA_MAPPING.get(
                    raw_classification, "uncertain"
                )

                # Store confidence score for location average
                if loc_key and confidence_percentage:
                    locations[loc_key]["confidence_scores"].append(
                        confidence_percentage
                    )

                # Store latest analysis info for the location
                if loc_key:
                    current_analysis_date = getattr(
                        result, "analyzed_at", image.uploaded_at
                    )
                    if locations[loc_key][
                        "latest_analysis"
                    ] is None or current_analysis_date > locations[loc_key][
                        "latest_analysis"
                    ].get(
                        "analyzed_at", datetime.min
                    ):
                        locations[loc_key]["latest_analysis"] = {
                            "id": getattr(result, "id", f"analysis_{image.id}"),
                            "ai_classification": raw_classification,  # Original AI model output
                            "schema_category": schema_category,  # Mapped to schema
                            "confidence_score": confidence_percentage,
                            "analyzed_at": current_analysis_date,
                            "bleaching_status": getattr(
                                result, "bleaching_status", raw_classification
                            ),
                            "model_version": getattr(
                                result, "model_version", "coral-classifier-v1.0"
                            ),
                            # Include coordinates in analysis data
                            "coordinates": (
                                {"latitude": lat, "longitude": lng}
                                if lat is not None and lng is not None
                                else None
                            ),
                            "is_public": image.is_public,
                        }

                # Count based on schema categories
                if schema_category == "healthy":
                    healthy_count += 1
                    if is_recent:
                        recent_healthy += 1
                    if loc_key:
                        locations[loc_key]["healthy"] += 1

                elif schema_category == "bleached":
                    bleached_count += 1
                    if is_recent:
                        recent_bleached += 1
                    if loc_key:
                        locations[loc_key]["bleached"] += 1

                elif schema_category == "partially_bleached":
                    partially_bleached_count += 1
                    if loc_key:
                        locations[loc_key]["partially_bleached"] += 1

                else:  # uncertain or unknown
                    uncertain_count += 1
                    if loc_key:
                        locations[loc_key]["uncertain"] += 1
                    if raw_classification:
                        logger.warning(
                            f"Unknown AI classification '{raw_classification}' mapped to 'uncertain' for image {image.id}"
                        )

        # Calculate percentages based on processed images
        total_analyzed = processed_images if processed_images > 0 else total_images
        healthy_percent = (
            (healthy_count / total_analyzed) * 100 if total_analyzed > 0 else 0
        )
        bleached_percent = (
            (bleached_count / total_analyzed) * 100 if total_analyzed > 0 else 0
        )
        partially_bleached_percent = (
            (partially_bleached_count / total_analyzed) * 100
            if total_analyzed > 0
            else 0
        )
        uncertain_percent = (
            (uncertain_count / total_analyzed) * 100 if total_analyzed > 0 else 0
        )
        recent_percent = (
            (recent_images_count / total_images) * 100 if total_images > 0 else 0
        )

        # Build active locations list with confidence scores
        active_locations = []
        for loc_key, loc_data in locations.items():
            if loc_data["coordinates"]:
                # Calculate average confidence score for this location
                avg_confidence = (
                    round(
                        sum(loc_data["confidence_scores"])
                        / len(loc_data["confidence_scores"]),
                        2,
                    )
                    if loc_data["confidence_scores"]
                    else 0
                )

                # Calculate health percentage (healthy / total analyzed at this location)
                analyzed_at_location = (
                    loc_data["healthy"]
                    + loc_data["bleached"]
                    + loc_data["partially_bleached"]
                    + loc_data["uncertain"]
                )
                health_percentage = (
                    round((loc_data["healthy"] / analyzed_at_location) * 100, 2)
                    if analyzed_at_location > 0
                    else 0
                )

                latest_analysis = loc_data["latest_analysis"]

                active_locations.append(
                    {
                        "id": loc_data["id"],
                        "coordinates": loc_data["coordinates"],
                        "total_images": loc_data["total"],
                        "analyzed_images": analyzed_at_location,
                        "healthy": loc_data["healthy"],
                        "bleached": loc_data["bleached"],
                        "partially_bleached": loc_data["partially_bleached"],
                        "uncertain": loc_data["uncertain"],
                        "health_percentage": health_percentage,
                        "average_confidence": avg_confidence,
                        "name": f"Location ({loc_data['coordinates']['latitude']}, {loc_data['coordinates']['longitude']})",
                        "country": "Philippines",
                        "latest_analysis_date": (
                            latest_analysis["analyzed_at"].isoformat()
                            if latest_analysis and latest_analysis["analyzed_at"]
                            else (
                                loc_data["latest_upload_date"].isoformat()
                                if loc_data["latest_upload_date"]
                                else datetime.now().isoformat()
                            )
                        ),
                        "latest_analysis": latest_analysis,
                    }
                )

        # Sort locations by health percentage and confidence
        active_locations.sort(
            key=lambda x: (x["health_percentage"], x["average_confidence"]),
            reverse=True,
        )

        # Calculate combined bleached percentage (bleached + partially_bleached)
        total_bleached_percent = bleached_percent + partially_bleached_percent

        # Get top 5 locations by health percentage for summary
        top_locations = active_locations[:5] if active_locations else []

        result_data = {
            "total_images": total_images,
            "processed_images": processed_images,
            "healthy_count": healthy_count,
            "bleached_count": bleached_count,
            "partially_bleached_count": partially_bleached_count,
            "uncertain_count": uncertain_count,
            "healthy_percent": round(healthy_percent, 2),
            "bleached_percent": round(bleached_percent, 2),
            "partially_bleached_percent": round(partially_bleached_percent, 2),
            "uncertain_percent": round(uncertain_percent, 2),
            "total_bleached_percent": round(
                total_bleached_percent, 2
            ),  # Combined bleaching
            "unique_locations": len(active_locations),
            "recent_images": {
                "count": recent_images_count,
                "percent": round(recent_percent, 2),
                "healthy": recent_healthy,
                "bleached": recent_bleached,
            },
            "active_locations": active_locations,
            # New: Include all unique coordinates in a separate array for easy access
            "all_coordinates": [
                {"latitude": lat, "longitude": lng} for lat, lng in all_coordinates
            ],
            # New: Include coordinate summary
            "coordinate_summary": {
                "total_unique_coordinates": len(all_coordinates),
                "coordinates_range": {
                    "min_lat": (
                        min(lat for lat, lng in all_coordinates)
                        if all_coordinates
                        else None
                    ),
                    "max_lat": (
                        max(lat for lat, lng in all_coordinates)
                        if all_coordinates
                        else None
                    ),
                    "min_lng": (
                        min(lng for lat, lng in all_coordinates)
                        if all_coordinates
                        else None
                    ),
                    "max_lng": (
                        max(lng for lat, lng in all_coordinates)
                        if all_coordinates
                        else None
                    ),
                },
            },
            "health_trend": (
                "improving" if healthy_percent > total_bleached_percent else "declining"
            ),
            # New: Include top locations by health
            "top_locations_by_health": top_locations,
            "ai_model_mapping": {
                "schema_categories": [
                    "healthy",
                    "bleached",
                    "partially_bleached",
                    "uncertain",
                ],
                "ai_model_classes": [
                    "healthy",
                    "tabular_hard_coral",
                    "polar_white_bleaching",
                    "slight_pale_bleaching",
                    "very_pale_bleaching",
                ],
                "mapping": AI_MODEL_TO_SCHEMA_MAPPING,
            },
            "classification_summary": {
                "by_schema_category": {
                    "healthy": healthy_count,
                    "bleached": bleached_count,
                    "partially_bleached": partially_bleached_count,
                    "uncertain": uncertain_count,
                },
                "processing_stats": {
                    "total_images": total_images,
                    "processed_images": processed_images,
                    "processing_rate": (
                        round((processed_images / total_images) * 100, 2)
                        if total_images > 0
                        else 0
                    ),
                },
            },
        }

        logger.info(
            f"Trend calculation completed: {processed_images}/{total_images} images processed"
        )
        logger.info(
            f"Classification breakdown: H={healthy_count}, B={bleached_count}, PB={partially_bleached_count}, U={uncertain_count}"
        )
        logger.info(f"Coordinates found: {len(all_coordinates)} unique locations")

        return result_data

    except Exception as e:
        logger.error(f"Service: error calculating for trend results: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to calculate for trend",
        )
