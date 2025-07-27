from fastapi import Depends, HTTPException, Request, status
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


BACKEND_DEBUG = False


if not BACKEND_DEBUG:

    async def get_current_user(
        request: Request, db: Session = Depends(get_db)
    ) -> UserOut:
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            print("No token found in cookies or headers")
            raise credentials_exception

        print(f"Token found: {token[:10]}...")

        payload = TokenSecurity.decode_access_token(token)
        if payload is None:
            print("Token decode failed")
            raise credentials_exception

        email: str = payload.get("sub")
        if email is None:
            print("Email not found")
            raise credentials_exception

        user = get_user_by_email(db, email)
        if user is None:
            print("User not found")
            raise credentials_exception

        if user.is_verified != payload.get("is_verified"):
            print("User not verified")
            raise credentials_exception

        return user

else:

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
    def role_checker(current_user: UserOut = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource",
            )
        return current_user

    return role_checker
