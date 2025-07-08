from pydantic import BaseModel, EmailStr, constr
from uuid import UUID
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = constr(min_length=8)


class UserBase(BaseModel):
    name: str
    email: EmailStr
    age: int
    role: Optional[int] = None
    profile: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    created_at: datetime = None
    updated_at: datetime = None


class CreateUser(UserBase):
    password: str
    agree_to_terms: bool = True


class UpdateUser(UserBase):
    name: Optional[str] = None
    password: Optional[str] = None
    age: Optional[int] = None
    role: Optional[int] = None
    profile: Optional[str] = None
    company: Optional[str] = None
    position: Optional[str] = None
    is_active: Optional[bool] = None


class UserOut(UserBase):
    id: UUID
    is_active: bool = False
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True


class UserInDB(UserOut):
    password: str
