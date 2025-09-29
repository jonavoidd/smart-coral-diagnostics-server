from celery.schedules import crontab

from app.core.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "daily-inactive-deactication": {
        "task": "app.jobs.deactivate_users.deactivate_inactive_users",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "default"},
    },
    "check-bleaching-thresholds": {
        "task": "app.jobs.bleaching_alerts.check_bleaching_thresholds",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
        "options": {"queue": "default"},
    },
    "weekly-bleaching-reports": {
        "task": "app.jobs.bleaching_alerts.send_weekly_bleaching_reports",
        "schedule": crontab(hour=9, minute=0, day_of_week=0),  # Sunday at 9 AM
        "options": {"queue": "default"},
    },
    "monthly-bleaching-reports": {
        "task": "app.jobs.bleaching_alerts.send_monthly_bleaching_reports",
        "schedule": crontab(hour=10, minute=0, day=1),  # 1st of month at 10 AM
        "options": {"queue": "default"},
    },
    "cleanup-alert-history": {
        "task": "app.jobs.bleaching_alerts.cleanup_old_alert_history",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # Monday at 2 AM
        "options": {"queue": "default"},
    },
    "generate-bleaching-statistics": {
        "task": "app.jobs.bleaching_alerts.generate_bleaching_statistics",
        "schedule": crontab(hour=1, minute=0),  # Daily at 1 AM
        "options": {"queue": "default"},
    },
}
