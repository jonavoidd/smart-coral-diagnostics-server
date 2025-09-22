from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class WebsiteContentBase(BaseModel):
    title: Optional[str] = None
    section: Optional[str] = None
    content: Optional[str] = None


class WebsiteContentCreate(WebsiteContentBase):
    pass


class WebsiteContentUpdate(WebsiteContentBase):
    pass


class WebsiteContentOut(WebsiteContentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
