from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import (
    OAuth2PasswordBearer,
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from jose import jwt, JWTError
from typing import List
from uuid import UUID

from app.db.connection import get_db
from app.core.config import settings
from app.crud.user import get_user_by_email
from app.models.users import UserRole
from app.schemas.user import UserOut
from app.utils.token import TokenSecurity

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

security = HTTPBearer()
supabase_jwt_key = settings.SUPABASE_JWT_KEY


async def get_current_user_supa(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = jwt.decode(token, supabase_jwt_key, algorithms=settings.ALGORITHM)
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> UserOut:
    payload = TokenSecurity.decode_access_token(token)

    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception

    user = get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    return user


def require_role(allowed_roles: List[UserRole]):
    def role_checker(id: UUID, current_user: UserOut = Depends(get_current_user)):
        if current_user.id == id:
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return role_checker
