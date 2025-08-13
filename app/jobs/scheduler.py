from celery.schedules import crontab

from app.core.celery_app import celery_app

celery_app.conf.beat_schedule = {
    "daily-inactive-deactication": {
        "task": "app.jobs.deactivate_users.deactivate_inactive_users",
        "schedule": crontab(hour=0, minute=0),
        "options": {"queue": "default"},
    }
}
