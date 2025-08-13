import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.connection import get_db
from app.services.trend_service import trend_result

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/")
def get_data_trends(db: Session = Depends(get_db)):
    try:
        return trend_result(db)
    except Exception as e:
        logger.error(f"Endpoint: error getting trend result data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get trend result",
        )
