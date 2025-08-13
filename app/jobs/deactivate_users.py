import logging

from celery import shared_task
from fastapi import Depends
from sqlalchemy.orm import Session

from app.crud.user import deactivate_inactive_accounts
from app.db.connection import get_db

logger = logging.getLogger(__name__)


@shared_task
def deactivate_inactive_users(db: Session = Depends(get_db)):
    try:
        deactivate_inactive_accounts(db)
    except Exception as e:
        logger.error(f"error running job to deactivate inactive accounts: {str(e)}")
