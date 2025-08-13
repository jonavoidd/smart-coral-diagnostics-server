from celery import Celery
from app.core.config import settings


celery_app = Celery(
    __name__, broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

celery_app.autodiscover_tasks(["app.jobs"])
