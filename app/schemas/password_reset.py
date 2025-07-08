from pydantic import BaseModel, EmailStr, constr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class GetToken(BaseModel):
    token: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = constr(min_length=8)


class PasswordChangeRequest(BaseModel):
    old_password: str = constr(min_length=8)
    new_password: str = constr(min_length=8)
    confirm_new_password: str = constr(min_length=8)


class RequestResponse(BaseModel):
    email: EmailStr
    token: str
