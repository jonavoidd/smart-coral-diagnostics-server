from datetime import datetime, date
from pydantic import BaseModel, EmailStr, StringConstraints
from typing import Annotated, List, Optional
from uuid import UUID

PasswordStr = Annotated[str, StringConstraints(min_length=8)]


class LoginRequest(BaseModel):
    email: EmailStr
    password: PasswordStr


class UserBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    email: EmailStr
    provider: Optional[str] = "local"
    provider_id: Optional[str] = None
    contact_number: Optional[str] = None

    agree_to_terms: bool
    subscribe_to_newsletter: Optional[bool] = False

    city: Optional[str] = None
    country: Optional[str] = None

    birthdate: date
    bio: Optional[str] = None
    experience: Optional[str] = None
    diving_certification: Optional[str] = None
    research_experience: Optional[str] = None

    organization: Optional[str] = None
    position: Optional[str] = None

    primary_interests: Optional[List[str]] = []
    contribution_types: Optional[List[str]] = []

    role: Optional[int] = None
    profile: Optional[str] = None

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateUser(UserBase):
    password: PasswordStr


class UpdateUser(BaseModel):
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    provider: Optional[str] = None
    provider_id: Optional[str] = None
    contact_number: Optional[str] = None

    agree_to_terms: Optional[bool] = None
    subscribe_to_newsletter: Optional[bool] = None

    city: Optional[str] = None
    country: Optional[str] = None

    birthdate: Optional[date] = None
    bio: Optional[str] = None
    experience: Optional[str] = None
    diving_certification: Optional[str] = None
    research_experience: Optional[str] = None

    organization: Optional[str] = None
    position: Optional[str] = None

    primary_interests: Optional[List[str]] = None
    contribution_types: Optional[List[str]] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None

    updated_at: Optional[datetime] = None


class UserOut(UserBase):
    id: UUID
    is_verified: Optional[bool] = False
    is_active: Optional[bool] = False
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True
