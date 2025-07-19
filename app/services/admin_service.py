from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.security import Hasher
from app.crud.user import create_user, delete_user
from app.schemas.audit_trail import CreateAuditTrail
from app.schemas.user import CreateUser, UserOut
from app.services.audit_trail_service import audit_trail_service


class SuperAdmin:
    def create_admin(self, db: Session, payload: CreateUser, user: UserOut):
        hashed_password = Hasher.hash_password(payload.password)
        user = create_user(db, payload, hashed_password)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="error creating new admin",
            )

        audit = CreateAuditTrail(
            actor_id=user.id,
            actor_role=user.role,
            action="CREATE",
            resource_type=f"admin",
            description=f"super admin with the email {user.email} created a new admin account",
        )
        audit_trail_service.insert_audit(db, audit)

        return {"message": "admin successfully created", "user": user}

    def remove_admin(self, db: Session, id: UUID, user: UserOut):
        deleted = delete_user(db, id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="user not found"
            )

        audit = CreateAuditTrail(
            actor_id=user.id,
            actor_role=user.role,
            action="DELETE",
            resource_type="admin",
            description=f"super admin with the email {user.email} deleted admin with the id: {id}",
        )
        audit_trail_service.insert_audit(db, audit)

        return {"message": f"deleted user with id {id}"}


super_admin = SuperAdmin()
