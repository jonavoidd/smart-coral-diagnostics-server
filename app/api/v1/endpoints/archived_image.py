import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID

from app.core.auth import require_role
from app.db.connection import get_db
from app.models.users import UserRole
from app.schemas.archived_image import ArchivedImageOut
from app.schemas.user import UserOut
from app.services.archived_image import select_archived_data, delete_archived_data

router = APIRouter()
logger = logging.getLogger(__name__)
LOG_MSG = "Endpoint:"


@router.get("/", response_model=Optional[List[ArchivedImageOut]])
def get_archived_data(
    db: Session = Depends(get_db),
    current_user: UserOut = Depends(
        require_role([UserRole.ADMIN, UserRole.SUPER_ADMIN])
    ),
):
    try:
        return select_archived_data(db)
    except Exception as e:
        logger.error(f"{LOG_MSG} error getting data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to get archived data",
        )


@router.delete("/{id}")
def delete_archived_data(id: UUID, db: Session = Depends(get_db)):
    try:
        return delete_archived_data(db, id)
    except Exception as e:
        logger.error(f"{LOG_MSG} error deleting data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed to delete archived data.",
        )
