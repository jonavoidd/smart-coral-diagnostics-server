from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    name: str
    email: EmailStr


class Token(UserBase):
    access_token: str
    token_type: str
