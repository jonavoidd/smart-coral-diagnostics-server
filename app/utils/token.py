from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any
from jose import JWTError, jwt

from app.core.config import settings


class TokenSecurity:
    def create_access_token(
        subject: Union[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta is not None:
            expires_delta = datetime.now(timezone.utc) + expires_delta
        else:
            expires_delta = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {"exp": expires_delta, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

        # to_encode = data.copy()
        # expire = datetime.now(timezone.utc) + (
        #     expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        # )
        # to_encode.update({"exp": expire})
        # return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def create_refresh_token(
        subject: Union[str, Any], exprires_delta: Optional[timedelta] = None
    ) -> str:
        if exprires_delta is not None:
            expires_delta = datetime.now(timezone.utc) + expires_delta
        else:
            expires_delta = datetime.now(timezone.utc) + timedelta(
                minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {"exp": expires_delta, "sub": str(subject)}
        encoded_jwt = jwt.encode(
            to_encode, settings.REFRESH_SECRET_KEY, settings.ALGORITHM
        )

        return encoded_jwt

    def decode_access_token(token: str) -> Optional[dict]:
        try:
            return jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
        except JWTError:
            return None
