import logging

from datetime import date
from sqlalchemy import insert, select, and_
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List
from uuid import UUID

from app.models.audit_trail import AuditTrail
from app.schemas.audit_trail import CreateAuditTrail

logger = logging.getLogger(__name__)
LOG_MSG = "Crud:"


class AuditTrailCrud:
    def create_audit(self, db: Session, payload: CreateAuditTrail) -> AuditTrail:
        audit = AuditTrail(**payload.model_dump())

        try:
            db.add(audit)
            db.commit()
            db.refresh(audit)

            return audit
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"{LOG_MSG} error inserting logs into audit trail: {str(e)}")
            raise

    def get_all_audit(self, db: Session) -> List[AuditTrail]:
        try:
            audit = db.query(AuditTrail).all()
            return audit
        except SQLAlchemyError as e:
            logger.error(f"{LOG_MSG} error getting all audit: {str(e)}")
            raise

    def get_audit_by_id(self, db: Session, id: UUID) -> AuditTrail:
        query = select(AuditTrail).where(AuditTrail.id == id)

        try:
            result = db.execute(query)
            audit = result.scalar_one_or_none()

            return result
        except SQLAlchemyError as e:
            logger.error(f"{LOG_MSG} error getting audit by id: {str(e)}")
            raise

    def get_audit_by_date(
        self, db: Session, start_date: date, end_date: date
    ) -> List[AuditTrail]:
        query = select(AuditTrail).where(
            and_(AuditTrail.timestamp > start_date, AuditTrail.timestamp < end_date)
        )

        try:
            audit = db.execute(query).scalars().all()
            return audit
        except SQLAlchemyError as e:
            logger.error(f"{LOG_MSG} error getting audit by time: {str(e)}")
            raise


audit_trail_crud = AuditTrailCrud()
