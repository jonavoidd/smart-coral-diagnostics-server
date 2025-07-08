from pydantic import BaseModel, EmailStr


class Email(BaseModel):
    email: EmailStr
    subject: str
    body: str
