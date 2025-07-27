from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class AuditTrailBase(BaseModel):
    actor_id: UUID
    actor_role: int
    action: str
    resource_type: str
    resource_id: Optional[UUID] = None
    description: str
    timestamp: Optional[datetime] = None


class CreateAuditTrail(AuditTrailBase):
    pass


class AuditTrailOut(BaseModel):
    id: UUID

    class Config:
        from_attributes = True
