import logging

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.audit_trail import AuditTrailOut
from app.schemas.user import UserOut
from app.services.audit_trail_service import audit_trail_service

router = APIRouter()
logger = logging.getLogger(__name__)
LOG_MSG = "Endpoint:"


@router.get("/", response_model=List[AuditTrailOut])
def get_audit(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    try:
        return audit_trail_service.select_all_audit(db)
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting audit trails")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get audit trails",
        )


@router.get("/date", response_model=List[AuditTrailOut])
def get_audit_by_date(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    try:
        return audit_trail_service.select_audit_by_date(
            db, start_date=start_date, end_date=end_date
        )
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting audit trails by date: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get audit trails by date",
        )
