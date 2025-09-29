import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, text
import math

from app.models.alert_subscriptions import AlertSubscription, AlertHistory
from app.models.public_alerts import PublicBleachingAlert, PublicAlertHistory
from app.models.coral_images import CoralImages
from app.models.analysis_results import AnalysisResult
from app.services.email_service import email_service
from app.schemas.alert_subscription import BleachingAlertData

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self):
        self.earth_radius_km = 6371.0  # Earth's radius in kilometers

    def calculate_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points using Haversine formula"""
        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        return self.earth_radius_km * c

    def get_bleaching_cases_in_area(
        self,
        db: Session,
        latitude: float,
        longitude: float,
        radius_km: float,
        days_back: int = 30,
    ) -> List[Dict]:
        """Get bleaching cases within a specified radius and time period"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)

        # Get all coral images with analysis results in the time period
        query = (
            db.query(
                CoralImages.id,
                CoralImages.latitude,
                CoralImages.longitude,
                CoralImages.observation_date,
                CoralImages.name,
                AnalysisResult.bleaching_percentage,
                AnalysisResult.classification_labels,
                AnalysisResult.analyzed_at,
            )
            .join(AnalysisResult, CoralImages.id == AnalysisResult.image_id)
            .filter(
                and_(
                    CoralImages.latitude.isnot(None),
                    CoralImages.longitude.isnot(None),
                    AnalysisResult.analyzed_at >= cutoff_date,
                    AnalysisResult.bleaching_percentage
                    > 0,  # Only cases with bleaching
                )
            )
        )

        cases = []
        for row in query.all():
            if row.latitude and row.longitude:
                distance = self.calculate_distance(
                    latitude, longitude, row.latitude, row.longitude
                )
                if distance <= radius_km:
                    cases.append(
                        {
                            "id": str(row.id),
                            "latitude": row.latitude,
                            "longitude": row.longitude,
                            "observation_date": row.observation_date,
                            "name": row.name,
                            "bleaching_percentage": row.bleaching_percentage,
                            "classification_labels": row.classification_labels,
                            "analyzed_at": row.analyzed_at,
                            "distance_km": distance,
                        }
                    )

        return cases

    def check_bleaching_thresholds(self, db: Session) -> List[BleachingAlertData]:
        """Check for areas that have reached bleaching thresholds"""
        # Get all active subscriptions
        subscriptions = (
            db.query(AlertSubscription)
            .filter(AlertSubscription.is_active == True)
            .all()
        )

        alert_data = []

        for subscription in subscriptions:
            if subscription.latitude and subscription.longitude:
                # Get bleaching cases in the subscription area
                cases = self.get_bleaching_cases_in_area(
                    db,
                    subscription.latitude,
                    subscription.longitude,
                    subscription.radius_km or 50.0,
                )

                if len(cases) >= subscription.bleaching_threshold:
                    # Determine severity level
                    severity = self._determine_severity(
                        len(cases), subscription.bleaching_threshold
                    )

                    alert_data.append(
                        BleachingAlertData(
                            area_name=f"{subscription.city or 'Unknown'}, {subscription.country or 'Unknown'}",
                            latitude=subscription.latitude,
                            longitude=subscription.longitude,
                            bleaching_count=len(cases),
                            threshold=subscription.bleaching_threshold,
                            affected_radius_km=subscription.radius_km or 50.0,
                            recent_cases=cases[-10:],  # Last 10 cases
                            severity_level=severity,
                        )
                    )

        return alert_data

    def create_or_update_public_alert(
        self, db: Session, alert_data: BleachingAlertData
    ) -> Optional[PublicBleachingAlert]:
        """Create or update a public alert for public display"""
        try:
            # Check if there's already a public alert for this area
            existing_alert = (
                db.query(PublicBleachingAlert)
                .filter(
                    and_(
                        PublicBleachingAlert.latitude == alert_data.latitude,
                        PublicBleachingAlert.longitude == alert_data.longitude,
                        PublicBleachingAlert.is_active == True,
                    )
                )
                .first()
            )

            if existing_alert:
                # Update existing alert
                existing_alert.bleaching_count = alert_data.bleaching_count
                existing_alert.severity_level = alert_data.severity_level
                existing_alert.last_updated = datetime.utcnow()
                db.commit()
                db.refresh(existing_alert)

                # Create history record
                history = PublicAlertHistory(
                    alert_id=existing_alert.id,
                    change_type="updated",
                    description=f"Alert updated: {alert_data.bleaching_count} cases detected",
                )
                db.add(history)
                db.commit()

                return existing_alert
            else:
                # Create new public alert
                public_alert = PublicBleachingAlert(
                    area_name=alert_data.area_name,
                    latitude=alert_data.latitude,
                    longitude=alert_data.longitude,
                    bleaching_count=alert_data.bleaching_count,
                    threshold=alert_data.threshold,
                    affected_radius_km=alert_data.affected_radius_km,
                    severity_level=alert_data.severity_level,
                    description=f"Bleaching threshold reached: {alert_data.bleaching_count} cases detected in {alert_data.area_name}",
                )

                db.add(public_alert)
                db.commit()
                db.refresh(public_alert)

                # Create history record
                history = PublicAlertHistory(
                    alert_id=public_alert.id,
                    change_type="created",
                    description=f"New public alert created for {alert_data.area_name}",
                )
                db.add(history)
                db.commit()

                return public_alert

        except Exception as e:
            logger.error(f"Failed to create/update public alert: {str(e)}")
            db.rollback()
            return None

    def _determine_severity(self, case_count: int, threshold: int) -> str:
        """Determine severity level based on case count vs threshold"""
        ratio = case_count / threshold
        if ratio >= 3.0:
            return "critical"
        elif ratio >= 2.0:
            return "high"
        elif ratio >= 1.5:
            return "medium"
        else:
            return "low"

    async def send_bleaching_alert(
        self,
        db: Session,
        subscription: AlertSubscription,
        alert_data: BleachingAlertData,
    ) -> bool:
        """Send bleaching alert to a specific subscription"""
        try:
            # Create alert history record
            alert_history = AlertHistory(
                subscription_id=subscription.id,
                alert_type="threshold_reached",
                title=f"🚨 Bleaching Alert: {alert_data.area_name}",
                message=f"Bleaching threshold reached: {alert_data.bleaching_count} cases detected",
                bleaching_count=alert_data.bleaching_count,
                affected_area=alert_data.area_name,
                latitude=alert_data.latitude,
                longitude=alert_data.longitude,
                delivery_status="pending",
            )
            db.add(alert_history)
            db.commit()

            # Send email
            success = await self._send_bleaching_alert_email(
                subscription.email, alert_data, subscription
            )

            # Update delivery status
            alert_history.email_sent = success
            alert_history.email_sent_at = datetime.utcnow() if success else None
            alert_history.delivery_status = "sent" if success else "failed"
            db.commit()

            return success

        except Exception as e:
            logger.error(f"Failed to send bleaching alert: {str(e)}")
            return False

    async def _send_bleaching_alert_email(
        self,
        email: str,
        alert_data: BleachingAlertData,
        subscription: AlertSubscription,
    ) -> bool:
        """Send bleaching alert email"""
        subject = f"🚨 Coral Bleaching Alert: {alert_data.area_name}"

        # Create HTML email template
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Coral Bleaching Alert</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #2c3e50;
                    background-color: #fff5f5;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }
                .container {
                    background-color: #ffffff;
                    padding: 30px;
                    border-radius: 10px;
                    border: 2px solid #e74c3c;
                    box-shadow: 0 4px 15px rgba(231, 76, 60, 0.1);
                }
                .header {
                    text-align: center;
                    margin-bottom: 30px;
                    background-color: #e74c3c;
                    color: white;
                    padding: 20px;
                    border-radius: 8px;
                }
                .alert-level {
                    display: inline-block;
                    padding: 8px 16px;
                    border-radius: 20px;
                    font-weight: bold;
                    margin: 10px 0;
                }
                .critical { background-color: #e74c3c; color: white; }
                .high { background-color: #f39c12; color: white; }
                .medium { background-color: #f1c40f; color: #2c3e50; }
                .low { background-color: #27ae60; color: white; }
                .stats {
                    background-color: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin: 20px 0;
                }
                .stat-item {
                    display: flex;
                    justify-content: space-between;
                    padding: 8px 0;
                    border-bottom: 1px solid #dee2e6;
                }
                .stat-item:last-child {
                    border-bottom: none;
                }
                .footer {
                    text-align: center;
                    margin-top: 30px;
                    font-size: 12px;
                    color: #666;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Coral Bleaching Alert</h1>
                    <div class="alert-level {{ severity_class }}">{{ severity_level.upper() }} SEVERITY</div>
                </div>
                
                <h2>Alert Details</h2>
                <p><strong>Location:</strong> {{ area_name }}</p>
                <p><strong>Coordinates:</strong> {{ latitude }}, {{ longitude }}</p>
                <p><strong>Alert Time:</strong> {{ current_time }}</p>
                
                <div class="stats">
                    <h3>Bleaching Statistics</h3>
                    <div class="stat-item">
                        <span>Cases Detected:</span>
                        <strong>{{ bleaching_count }}</strong>
                    </div>
                    <div class="stat-item">
                        <span>Threshold:</span>
                        <strong>{{ threshold }}</strong>
                    </div>
                    <div class="stat-item">
                        <span>Exceeded by:</span>
                        <strong>{{ exceeded_by }} cases</strong>
                    </div>
                    <div class="stat-item">
                        <span>Monitoring Radius:</span>
                        <strong>{{ radius_km }} km</strong>
                    </div>
                </div>
                
                <h3>Recent Cases</h3>
                <p>The following recent bleaching cases have been detected in your monitoring area:</p>
                <ul>
                    {% for case in recent_cases[:5] %}
                    <li>
                        <strong>{{ case.name or 'Unnamed' }}</strong> - 
                        {{ case.bleaching_percentage }}% bleaching detected
                        {% if case.observation_date %}
                        ({{ case.observation_date.strftime('%Y-%m-%d') }})
                        {% endif %}
                    </li>
                    {% endfor %}
                </ul>
                
                <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <strong>⚠️ Action Required:</strong> This area has exceeded the bleaching threshold. 
                    Consider immediate conservation actions or contact local marine authorities.
                </div>
                
                <p>This alert was sent because the number of bleaching cases in your monitored area has reached or exceeded your threshold of {{ threshold }} cases.</p>
                
                <div class="footer">
                    <p>This is an automated alert from {{ app_name }}.</p>
                    <p>To manage your alert preferences, visit your account settings.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create text version
        text_template = """
        🚨 CORAL BLEACHING ALERT - {{ app_name }}
        
        SEVERITY: {{ severity_level.upper() }}
        Location: {{ area_name }}
        Coordinates: {{ latitude }}, {{ longitude }}
        Alert Time: {{ current_time }}
        
        BLEACHING STATISTICS:
        - Cases Detected: {{ bleaching_count }}
        - Threshold: {{ threshold }}
        - Exceeded by: {{ exceeded_by }} cases
        - Monitoring Radius: {{ radius_km }} km
        
        RECENT CASES:
        {% for case in recent_cases[:5] %}
        - {{ case.name or 'Unnamed' }}: {{ case.bleaching_percentage }}% bleaching
          {% if case.observation_date %}({{ case.observation_date.strftime('%Y-%m-%d') }}){% endif %}
        {% endfor %}
        
        ⚠️ ACTION REQUIRED: This area has exceeded the bleaching threshold. 
        Consider immediate conservation actions or contact local marine authorities.
        
        This alert was sent because the number of bleaching cases in your monitored area has reached or exceeded your threshold of {{ threshold }} cases.
        
        ---
        This is an automated alert from {{ app_name }}.
        To manage your alert preferences, visit your account settings.
        """

        from jinja2 import Template

        # Prepare template variables
        template_vars = {
            "app_name": "Smart Coral Diagnostics",
            "area_name": alert_data.area_name,
            "latitude": alert_data.latitude,
            "longitude": alert_data.longitude,
            "bleaching_count": alert_data.bleaching_count,
            "threshold": alert_data.threshold,
            "exceeded_by": alert_data.bleaching_count - alert_data.threshold,
            "radius_km": alert_data.affected_radius_km,
            "severity_level": alert_data.severity_level,
            "severity_class": alert_data.severity_level,
            "recent_cases": alert_data.recent_cases,
            "current_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        # Render templates
        html_content = Template(html_template).render(**template_vars)
        text_content = Template(text_template).render(**template_vars)

        return await email_service.send_email(
            to_email=email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
        )

    async def send_weekly_report(self, db: Session) -> bool:
        """Send weekly bleaching report to all subscribers"""
        try:
            # Get all active subscriptions that want weekly reports
            subscriptions = (
                db.query(AlertSubscription)
                .filter(
                    and_(
                        AlertSubscription.is_active == True,
                        AlertSubscription.weekly_reports == True,
                    )
                )
                .all()
            )

            for subscription in subscriptions:
                await self._send_weekly_report_email(db, subscription)

            return True

        except Exception as e:
            logger.error(f"Failed to send weekly reports: {str(e)}")
            return False

    async def send_monthly_report(self, db: Session) -> bool:
        """Send monthly bleaching report to all subscribers"""
        try:
            # Get all active subscriptions that want monthly reports
            subscriptions = (
                db.query(AlertSubscription)
                .filter(
                    and_(
                        AlertSubscription.is_active == True,
                        AlertSubscription.monthly_reports == True,
                    )
                )
                .all()
            )

            for subscription in subscriptions:
                await self._send_monthly_report_email(db, subscription)

            return True

        except Exception as e:
            logger.error(f"Failed to send monthly reports: {str(e)}")
            return False

    async def _send_weekly_report_email(
        self, db: Session, subscription: AlertSubscription
    ) -> bool:
        """Send weekly report email to a specific subscription"""
        try:
            # Get bleaching cases for the past week
            week_ago = datetime.utcnow() - timedelta(days=7)

            if subscription.latitude and subscription.longitude:
                cases = self.get_bleaching_cases_in_area(
                    db,
                    subscription.latitude,
                    subscription.longitude,
                    subscription.radius_km or 50.0,
                    days_back=7,
                )
            else:
                cases = []

            subject = (
                f"📊 Weekly Coral Bleaching Report - {subscription.city or 'Your Area'}"
            )

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Weekly Coral Bleaching Report</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #2c3e50;
                        background-color: #f8f9fa;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .container {
                        background-color: #ffffff;
                        padding: 30px;
                        border-radius: 10px;
                        border: 1px solid #dee2e6;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 30px;
                        background-color: #17a2b8;
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                    }
                    .stats-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 20px;
                        margin: 20px 0;
                    }
                    .stat-card {
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        border: 1px solid #dee2e6;
                    }
                    .stat-number {
                        font-size: 24px;
                        font-weight: bold;
                        color: #17a2b8;
                    }
                    .stat-label {
                        font-size: 14px;
                        color: #6c757d;
                        margin-top: 5px;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📊 Weekly Coral Bleaching Report</h1>
                        <p>{{ area_name }} • Week of {{ week_start }} to {{ week_end }}</p>
                    </div>
                    
                    <h2>Summary</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ total_cases }}</div>
                            <div class="stat-label">Bleaching Cases</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ high_severity }}</div>
                            <div class="stat-label">High Severity</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ medium_severity }}</div>
                            <div class="stat-label">Medium Severity</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ low_severity }}</div>
                            <div class="stat-label">Low Severity</div>
                        </div>
                    </div>
                    
                    <h3>Recent Activity</h3>
                    {% if recent_cases %}
                    <ul>
                        {% for case in recent_cases[:5] %}
                        <li>
                            <strong>{{ case.name or 'Unnamed' }}</strong> - 
                            {{ case.bleaching_percentage }}% bleaching
                            {% if case.observation_date %}
                            ({{ case.observation_date.strftime('%Y-%m-%d') }})
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                    {% else %}
                    <p>No bleaching cases detected in your monitoring area this week.</p>
                    {% endif %}
                    
                    <div class="footer">
                        <p>This is your weekly automated report from {{ app_name }}.</p>
                        <p>To manage your alert preferences, visit your account settings.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Calculate statistics
            total_cases = len(cases)
            high_severity = len(
                [c for c in cases if c.get("bleaching_percentage", 0) >= 50]
            )
            medium_severity = len(
                [c for c in cases if 25 <= c.get("bleaching_percentage", 0) < 50]
            )
            low_severity = len(
                [c for c in cases if 0 < c.get("bleaching_percentage", 0) < 25]
            )

            template_vars = {
                "app_name": "Smart Coral Diagnostics",
                "area_name": f"{subscription.city or 'Unknown'}, {subscription.country or 'Unknown'}",
                "week_start": week_ago.strftime("%Y-%m-%d"),
                "week_end": datetime.utcnow().strftime("%Y-%m-%d"),
                "total_cases": total_cases,
                "high_severity": high_severity,
                "medium_severity": medium_severity,
                "low_severity": low_severity,
                "recent_cases": cases[-5:] if cases else [],
            }

            from jinja2 import Template

            html_content = Template(html_template).render(**template_vars)

            return await email_service.send_email(
                to_email=subscription.email, subject=subject, html_content=html_content
            )

        except Exception as e:
            logger.error(f"Failed to send weekly report: {str(e)}")
            return False

    async def _send_monthly_report_email(
        self, db: Session, subscription: AlertSubscription
    ) -> bool:
        """Send monthly report email to a specific subscription"""
        try:
            # Get bleaching cases for the past month
            month_ago = datetime.utcnow() - timedelta(days=30)

            if subscription.latitude and subscription.longitude:
                cases = self.get_bleaching_cases_in_area(
                    db,
                    subscription.latitude,
                    subscription.longitude,
                    subscription.radius_km or 50.0,
                    days_back=30,
                )
            else:
                cases = []

            subject = f"📈 Monthly Coral Bleaching Report - {subscription.city or 'Your Area'}"

            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Monthly Coral Bleaching Report</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        color: #2c3e50;
                        background-color: #f8f9fa;
                        max-width: 600px;
                        margin: 0 auto;
                        padding: 20px;
                    }
                    .container {
                        background-color: #ffffff;
                        padding: 30px;
                        border-radius: 10px;
                        border: 1px solid #dee2e6;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }
                    .header {
                        text-align: center;
                        margin-bottom: 30px;
                        background-color: #28a745;
                        color: white;
                        padding: 20px;
                        border-radius: 8px;
                    }
                    .stats-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr;
                        gap: 20px;
                        margin: 20px 0;
                    }
                    .stat-card {
                        background-color: #f8f9fa;
                        padding: 20px;
                        border-radius: 8px;
                        text-align: center;
                        border: 1px solid #dee2e6;
                    }
                    .stat-number {
                        font-size: 24px;
                        font-weight: bold;
                        color: #28a745;
                    }
                    .stat-label {
                        font-size: 14px;
                        color: #6c757d;
                        margin-top: 5px;
                    }
                    .trend {
                        background-color: #e3f2fd;
                        padding: 15px;
                        border-radius: 8px;
                        margin: 20px 0;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>📈 Monthly Coral Bleaching Report</h1>
                        <p>{{ area_name }} • {{ month_name }} {{ year }}</p>
                    </div>
                    
                    <h2>Monthly Summary</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-number">{{ total_cases }}</div>
                            <div class="stat-label">Total Cases</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ avg_daily }}</div>
                            <div class="stat-label">Avg Daily</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-number">{{ peak_day }}</div>
                            <div class="stat-label">Peak Day</div>
                        </div>
                    </div>
                    
                    <div class="trend">
                        <h3>Trend Analysis</h3>
                        <p><strong>Severity Distribution:</strong></p>
                        <ul>
                            <li>High Severity (≥50%): {{ high_severity }} cases</li>
                            <li>Medium Severity (25-49%): {{ medium_severity }} cases</li>
                            <li>Low Severity (<25%): {{ low_severity }} cases</li>
                        </ul>
                    </div>
                    
                    <h3>Key Insights</h3>
                    {% if total_cases > 0 %}
                    <ul>
                        <li>Average bleaching percentage: {{ avg_bleaching }}%</li>
                        <li>Most affected area: {{ most_affected_area }}</li>
                        <li>Peak activity: {{ peak_activity_period }}</li>
                    </ul>
                    {% else %}
                    <p>No bleaching cases detected in your monitoring area this month.</p>
                    {% endif %}
                    
                    <div class="footer">
                        <p>This is your monthly automated report from {{ app_name }}.</p>
                        <p>To manage your alert preferences, visit your account settings.</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Calculate comprehensive statistics
            total_cases = len(cases)
            avg_daily = round(total_cases / 30, 1) if total_cases > 0 else 0

            # Calculate severity distribution
            high_severity = len(
                [c for c in cases if c.get("bleaching_percentage", 0) >= 50]
            )
            medium_severity = len(
                [c for c in cases if 25 <= c.get("bleaching_percentage", 0) < 50]
            )
            low_severity = len(
                [c for c in cases if 0 < c.get("bleaching_percentage", 0) < 25]
            )

            # Calculate average bleaching percentage
            avg_bleaching = (
                round(
                    sum(c.get("bleaching_percentage", 0) for c in cases) / total_cases,
                    1,
                )
                if total_cases > 0
                else 0
            )

            # Find peak day (simplified)
            peak_day = (
                max(
                    len(
                        [
                            c
                            for c in cases
                            if c.get("analyzed_at", datetime.utcnow()).date() == date
                        ]
                    )
                    for date in set(
                        c.get("analyzed_at", datetime.utcnow()).date() for c in cases
                    )
                )
                if cases
                else 0
            )

            template_vars = {
                "app_name": "Smart Coral Diagnostics",
                "area_name": f"{subscription.city or 'Unknown'}, {subscription.country or 'Unknown'}",
                "month_name": datetime.utcnow().strftime("%B"),
                "year": datetime.utcnow().year,
                "total_cases": total_cases,
                "avg_daily": avg_daily,
                "peak_day": peak_day,
                "high_severity": high_severity,
                "medium_severity": medium_severity,
                "low_severity": low_severity,
                "avg_bleaching": avg_bleaching,
                "most_affected_area": subscription.city or "Unknown",
                "peak_activity_period": "Last week" if total_cases > 0 else "None",
            }

            from jinja2 import Template

            html_content = Template(html_template).render(**template_vars)

            return await email_service.send_email(
                to_email=subscription.email, subject=subject, html_content=html_content
            )

        except Exception as e:
            logger.error(f"Failed to send monthly report: {str(e)}")
            return False


# Create service instance
alert_service = AlertService()
