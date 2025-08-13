import logging

from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID

from app.crud.audit_trail import audit_trail_crud
from app.schemas.audit_trail import CreateAuditTrail, AuditTrailOut


class AuditTrailService:
    def insert_audit(self, db: Session, payload: CreateAuditTrail):
        res = audit_trail_crud.create_audit(db, payload)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="auditing action failed",
            )

        return res

    def select_all_audit(self, db: Session) -> List[AuditTrailOut]:
        return audit_trail_crud.get_all_audit(db)

    def select_audit_by_id(self, db: Session, id: UUID):
        res = audit_trail_crud.get_audit_by_id(db, id)
        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="no audit trail found with given id",
            )

        return res

    def select_audit_by_date(
        self, db: Session, start_date: date, end_date: date
    ) -> List[AuditTrailOut]:
        return audit_trail_crud.get_audit_by_date(db, start_date, end_date)


audit_trail_service = AuditTrailService()
