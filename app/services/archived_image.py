from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.crud.archived_image import select_archived_data, delete_archived_data
from app.schemas.archived_image import CreateArchivedImage, ArchivedImageOut


class ArchivedImage:
    def select(db: Session):
        try:
            data = select_archived_data
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="no data archived data found",
                )

            return data
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to get archived data",
            )

    def delete(db: Session, id: UUID):
        try:
            return delete_archived_data(db, id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="failed to delete archived data",
            )
