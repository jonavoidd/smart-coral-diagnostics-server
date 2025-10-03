import logging
import math

from collections import defaultdict
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from app.crud.bleaching_alert import (
    create_alert,
    get_alert_by_id,
    get_all_alerts,
    get_active_alerts,
    get_alerts_by_location,
    update_alert,
    resolve_alert,
    delete_alert,
    get_alert_statistics,
)
from app.models.analysis_results import AnalysisResult
from app.models.coral_images import CoralImages
from app.schemas.bleaching_alert import (
    CreateBleachingAlert,
    UpdateBleachingAlert,
    BleachingAlertOut,
    BleachingAlertSummary,
    AlertFilterParams,
)
from app.utils.geocoding import geocoding_service

logger = logging.getLogger(__name__)
LOG_MSG = "Service:"

# Constants
DEFAULT_ALERT_THRESHOLD = 10
DEFAULT_CLUSTER_RADIUS_KM = 50.0
MIN_BLEACHING_PERCENTAGE_THRESHOLD = 30.0


class BleachingAlertService:

    @staticmethod
    def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two points using Haversine formula
        Returns distance in kilometers
        """
        R = 6371  # Earth's radius in kilometers

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = R * c
        return distance

    @staticmethod
    def determine_severity_level(
        bleached_count: int, avg_bleaching_percentage: float
    ) -> str:
        """
        Determine alert severity based on bleached count and average bleaching percentage
        """
        if avg_bleaching_percentage >= 80 and bleached_count >= 300:
            return "critical"
        elif avg_bleaching_percentage >= 60 and bleached_count >= 200:
            return "high"
        elif avg_bleaching_percentage >= 40 and bleached_count >= 200:
            return "moderate"
        else:
            return "low"

    @staticmethod
    def cluster_locations(
        db: Session,
        radius_km: float = DEFAULT_CLUSTER_RADIUS_KM,
        min_bleaching_percentage: float = MIN_BLEACHING_PERCENTAGE_THRESHOLD,
    ) -> List[Dict]:
        """
        Cluster coral image locations and calculate bleaching statistics
        Returns list of location clusters with bleaching data
        """
        try:
            logger.info(
                f"{LOG_MSG} Starting location clustering with radius={radius_km}km, min_bleaching={min_bleaching_percentage}%"
            )

            # First, let's see ALL coral images with analysis
            total_query = db.query(func.count(CoralImages.id)).join(
                AnalysisResult, CoralImages.id == AnalysisResult.image_id
            )
            total_count = total_query.scalar()
            logger.info(f"{LOG_MSG} Total coral images with analysis: {total_count}")

            # Check how many have locations
            with_location_query = (
                db.query(func.count(CoralImages.id))
                .join(AnalysisResult, CoralImages.id == AnalysisResult.image_id)
                .filter(
                    and_(
                        CoralImages.latitude.isnot(None),
                        CoralImages.longitude.isnot(None),
                    )
                )
            )
            with_location_count = with_location_query.scalar()
            logger.info(f"{LOG_MSG} Coral images with location: {with_location_count}")

            # Check how many have bleaching percentage
            with_bleaching_query = (
                db.query(func.count(CoralImages.id))
                .join(AnalysisResult, CoralImages.id == AnalysisResult.image_id)
                .filter(
                    and_(
                        CoralImages.latitude.isnot(None),
                        CoralImages.longitude.isnot(None),
                        AnalysisResult.bleaching_percentage.isnot(None),
                    )
                )
            )
            with_bleaching_count = with_bleaching_query.scalar()
            logger.info(
                f"{LOG_MSG} Coral images with location and bleaching percentage: {with_bleaching_count}"
            )

            # Get all possible classification labels in the database
            classification_query = db.query(
                AnalysisResult.classification_labels
            ).distinct()
            all_classifications = [c[0] for c in classification_query.all() if c[0]]
            logger.info(
                f"{LOG_MSG} All classification labels in database: {all_classifications}"
            )

            # Now get the actual data - Let's be MORE PERMISSIVE for testing
            query = (
                db.query(
                    CoralImages.id,
                    CoralImages.latitude,
                    CoralImages.longitude,
                    AnalysisResult.bleaching_percentage,
                    AnalysisResult.classification_labels,
                )
                .join(AnalysisResult, CoralImages.id == AnalysisResult.image_id)
                .filter(
                    and_(
                        CoralImages.latitude.isnot(None),
                        CoralImages.longitude.isnot(None),
                        AnalysisResult.bleaching_percentage.isnot(None),
                    )
                )
            )

            all_with_bleaching = query.all()
            logger.info(
                f"{LOG_MSG} Found {len(all_with_bleaching)} corals with location and bleaching percentage"
            )

            if len(all_with_bleaching) > 0:
                logger.info(
                    f"{LOG_MSG} Sample data - First coral: lat={all_with_bleaching[0].latitude}, lon={all_with_bleaching[0].longitude}, bleaching={all_with_bleaching[0].bleaching_percentage}%, classification={all_with_bleaching[0].classification_labels}"
                )

            # Filter by classification - Make this MORE FLEXIBLE
            bleaching_keywords = [
                "bleach",  # Catches all bleaching variants
                "pale",  # Catches pale bleaching
                "white",  # Catches white bleaching
            ]

            coral_data = []
            for coral in all_with_bleaching:
                classification = (coral.classification_labels or "").lower()

                # Check if ANY bleaching keyword is in the classification
                is_bleached = any(
                    keyword in classification for keyword in bleaching_keywords
                )

                # Also check bleaching percentage threshold
                meets_threshold = coral.bleaching_percentage >= min_bleaching_percentage

                if is_bleached or meets_threshold:
                    coral_data.append(
                        {
                            "id": str(coral.id),
                            "latitude": coral.latitude,
                            "longitude": coral.longitude,
                            "bleaching_percentage": coral.bleaching_percentage,
                            "classification": coral.classification_labels,
                        }
                    )
                    logger.debug(
                        f"{LOG_MSG} Including coral {coral.id}: {classification}, {coral.bleaching_percentage}%"
                    )
                else:
                    logger.debug(
                        f"{LOG_MSG} Excluding coral {coral.id}: {classification}, {coral.bleaching_percentage}%"
                    )

            logger.info(
                f"{LOG_MSG} After filtering: {len(coral_data)} corals qualify for clustering"
            )

            if not coral_data:
                logger.warning(
                    f"{LOG_MSG} No coral data found for clustering after filters"
                )
                logger.warning(
                    f"{LOG_MSG} Try: 1) Lowering min_bleaching_percentage, 2) Checking classification labels match"
                )
                return []

            # Log first few qualifying corals
            for i, coral in enumerate(coral_data[:3]):
                logger.info(f"{LOG_MSG} Qualifying coral {i+1}: {coral}")

            # Convert to list of dictionaries
            corals = coral_data

            clusters = []
            used_indices = set()

            logger.info(
                f"{LOG_MSG} Starting clustering process with {len(corals)} corals"
            )

            for i, coral in enumerate(corals):
                if i in used_indices:
                    continue

                # Start a new cluster
                cluster = {
                    "center_lat": coral["latitude"],
                    "center_lon": coral["longitude"],
                    "corals": [coral],
                    "coral_ids": [coral["id"]],
                }
                used_indices.add(i)

                # Find all corals within radius
                for j, other_coral in enumerate(corals):
                    if j in used_indices:
                        continue

                    distance = BleachingAlertService.calculate_distance(
                        coral["latitude"],
                        coral["longitude"],
                        other_coral["latitude"],
                        other_coral["longitude"],
                    )

                    if distance <= radius_km:
                        cluster["corals"].append(other_coral)
                        cluster["coral_ids"].append(other_coral["id"])
                        used_indices.add(j)

                # Calculate cluster statistics
                if len(cluster["corals"]) > 0:
                    # Calculate center of mass for the cluster
                    avg_lat = sum(c["latitude"] for c in cluster["corals"]) / len(
                        cluster["corals"]
                    )
                    avg_lon = sum(c["longitude"] for c in cluster["corals"]) / len(
                        cluster["corals"]
                    )

                    cluster["center_lat"] = avg_lat
                    cluster["center_lon"] = avg_lon
                    cluster["total_count"] = len(cluster["corals"])
                    cluster["average_bleaching"] = sum(
                        c["bleaching_percentage"] for c in cluster["corals"]
                    ) / len(cluster["corals"])

                    clusters.append(cluster)
                    logger.info(
                        f"{LOG_MSG} Created cluster at ({avg_lat:.4f}, {avg_lon:.4f}) "
                        f"with {cluster['total_count']} corals, "
                        f"avg bleaching: {cluster['average_bleaching']:.1f}%"
                    )

            logger.info(f"{LOG_MSG} Created {len(clusters)} location clusters")

            return clusters

        except Exception as e:
            logger.error(f"{LOG_MSG} Error clustering locations: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            raise

    def generate_alerts(
        self,
        db: Session,
        min_bleached_count: int = DEFAULT_ALERT_THRESHOLD,
        cluster_radius_km: float = DEFAULT_CLUSTER_RADIUS_KM,
        regenerate_existing: bool = False,
    ) -> List[BleachingAlertOut]:
        """
        Generate bleaching alerts based on current coral image data
        """
        try:
            logger.info(f"{LOG_MSG} ===== STARTING ALERT GENERATION =====")
            logger.info(
                f"{LOG_MSG} Parameters: min_count={min_bleached_count}, radius={cluster_radius_km}km, regenerate={regenerate_existing}"
            )

            # Get location clusters with lower threshold for testing
            clusters = self.cluster_locations(
                db, cluster_radius_km, min_bleaching_percentage=20.0
            )

            logger.info(f"{LOG_MSG} Found {len(clusters)} clusters")

            generated_alerts = []

            for idx, cluster in enumerate(clusters):
                logger.info(
                    f"{LOG_MSG} Processing cluster {idx+1}/{len(clusters)}: {cluster['total_count']} corals"
                )

                # Only create alert if threshold is met
                if cluster["total_count"] < min_bleached_count:
                    logger.info(
                        f"{LOG_MSG} Cluster {idx+1} has {cluster['total_count']} corals, "
                        f"below threshold of {min_bleached_count}. Skipping."
                    )
                    continue

                logger.info(
                    f"{LOG_MSG} Cluster {idx+1} meets threshold! Creating alert..."
                )

                # CRITICAL: Explicitly convert all coral IDs to strings
                coral_ids_strings = []
                for cid in cluster["coral_ids"]:
                    if isinstance(cid, str):
                        coral_ids_strings.append(cid)
                    else:
                        coral_ids_strings.append(str(cid))

                logger.info(
                    f"{LOG_MSG} Converted {len(coral_ids_strings)} coral IDs to strings"
                )

                # Get real location name using reverse geocoding
                location_name = geocoding_service.get_location_name(
                    cluster["center_lat"], cluster["center_lon"]
                )
                logger.info(f"{LOG_MSG} Location name: {location_name}")

                # Check if alert already exists for this location
                existing_alerts = get_alerts_by_location(
                    db,
                    cluster["center_lat"],
                    cluster["center_lon"],
                    radius_km=cluster_radius_km,
                )

                if existing_alerts and not regenerate_existing:
                    # Update existing alert
                    alert = existing_alerts[0]
                    logger.info(f"{LOG_MSG} Updating existing alert {alert.id}")

                    update_data = UpdateBleachingAlert(
                        location_name=location_name,  # Update location name
                        total_images_analyzed=cluster["total_count"],
                        bleached_count=cluster["total_count"],
                        average_bleaching_percentage=round(
                            cluster["average_bleaching"], 2
                        ),
                        affected_coral_ids=coral_ids_strings,
                        severity_level=self.determine_severity_level(
                            cluster["total_count"], cluster["average_bleaching"]
                        ),
                    )
                    updated_alert = update_alert(db, alert.id, update_data)
                    if updated_alert:
                        generated_alerts.append(
                            BleachingAlertOut.model_validate(updated_alert)
                        )
                    continue

                # Determine severity
                severity = self.determine_severity_level(
                    cluster["total_count"], cluster["average_bleaching"]
                )

                logger.info(f"{LOG_MSG} Alert severity: {severity}")

                # Generate description and recommendations
                description = self._generate_description(
                    cluster["total_count"], cluster["average_bleaching"], severity
                )
                recommendations = self._generate_recommendations(severity)

                # Create new alert with REAL location name
                alert_data = CreateBleachingAlert(
                    latitude=cluster["center_lat"],
                    longitude=cluster["center_lon"],
                    location_name=location_name,  # Use geocoded name
                    severity_level=severity,
                    total_images_analyzed=cluster["total_count"],
                    bleached_count=cluster["total_count"],
                    average_bleaching_percentage=round(cluster["average_bleaching"], 2),
                    is_active=True,
                    alert_threshold=min_bleached_count,
                    cluster_radius_km=cluster_radius_km,
                    affected_coral_ids=coral_ids_strings,
                    description=description,
                    recommendations=recommendations,
                )

                new_alert = create_alert(db, alert_data)
                if new_alert:
                    generated_alerts.append(BleachingAlertOut.model_validate(new_alert))
                    logger.info(
                        f"{LOG_MSG} ✓ Created {severity} alert for {location_name} "
                        f"with {cluster['total_count']} bleached corals"
                    )

            logger.info(f"{LOG_MSG} ===== ALERT GENERATION COMPLETE =====")
            logger.info(f"{LOG_MSG} Generated {len(generated_alerts)} total alerts")
            return generated_alerts

        except Exception as e:
            logger.error(f"{LOG_MSG} Error generating alerts: {str(e)}")
            import traceback

            logger.error(traceback.format_exc())
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate alerts: {str(e)}",
            )

    def _generate_description(
        self, bleached_count: int, avg_bleaching: float, severity: str
    ) -> str:
        """Generate alert description"""
        return (
            f"A {severity} level bleaching event has been detected in this area. "
            f"Analysis of {bleached_count} coral images shows an average bleaching "
            f"percentage of {avg_bleaching:.1f}%. This indicates significant coral "
            f"stress and requires immediate attention from marine conservation authorities."
        )

    def _generate_recommendations(self, severity: str) -> str:
        """Generate recommendations based on severity"""
        base_recommendations = [
            "Monitor water temperature and quality regularly",
            "Document coral conditions with photographs",
            "Report findings to local marine conservation authorities",
            "Reduce local stressors (pollution, overfishing, coastal development)",
        ]

        if severity == "critical":
            base_recommendations.extend(
                [
                    "URGENT: Implement emergency response protocols",
                    "Consider temporary area closures to reduce human impact",
                    "Deploy coral restoration techniques if applicable",
                    "Coordinate with research institutions for intervention strategies",
                ]
            )
        elif severity == "high":
            base_recommendations.extend(
                [
                    "Increase monitoring frequency to weekly intervals",
                    "Assess potential for coral transplantation",
                    "Engage local community in conservation efforts",
                ]
            )

        return "\n• ".join([""] + base_recommendations)

    def get_alert_summary(self, db: Session) -> BleachingAlertSummary:
        """Get comprehensive alert summary"""
        try:
            stats = get_alert_statistics(db)

            # Get most affected locations (top 5 by bleached count)
            most_affected = get_all_alerts(
                db, filters=AlertFilterParams(is_active=True)
            )

            return BleachingAlertSummary(
                total_alerts=stats.get("total_alerts", 0),
                active_alerts=stats.get("active_alerts", 0),
                resolved_alerts=stats.get("resolved_alerts", 0),
                critical_alerts=stats.get("critical_alerts", 0),
                high_alerts=stats.get("high_alerts", 0),
                moderate_alerts=stats.get("moderate_alerts", 0),
                low_alerts=stats.get("low_alerts", 0),
                total_affected_corals=stats.get("total_affected_corals", 0),
                average_bleaching_percentage=stats.get(
                    "average_bleaching_percentage", 0.0
                ),
                most_affected_locations=[
                    BleachingAlertOut.model_validate(alert) for alert in most_affected
                ],
            )
        except Exception as e:
            logger.error(f"{LOG_MSG} error getting alert summary: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get alert summary",
            )


bleaching_alert_service = BleachingAlertService()
