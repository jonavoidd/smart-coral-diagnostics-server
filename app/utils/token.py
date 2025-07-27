import logging

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt

from app.core.config import settings

logger = logging.getLogger(__name__)


class TokenSecurity:
    @staticmethod
    def create_access_token(
        subject: Union[str, Any],
        user_data: Optional[Dict] = None,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        if expires_delta is not None:
            expires_delta = datetime.now(timezone.utc) + expires_delta
        else:
            expires_delta = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {
            "exp": expires_delta,
            "sub": subject,
            "iat": datetime.now(timezone.utc),
        }

        if user_data:
            to_encode.update(
                {
                    "user_id": str(user_data.get("id")),
                    "is_verified": user_data.get("is_verified", False),
                    "role": user_data.get("role", 1),
                    "email": user_data.get("email"),
                    "first_name": user_data.get("first_name"),
                    "last_name": user_data.get("last_name"),
                }
            )

        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, settings.ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        subject: Union[str, Any], exprires_delta: Optional[timedelta] = None
    ) -> str:
        if exprires_delta is not None:
            expires_delta = datetime.now(timezone.utc) + expires_delta
        else:
            expires_delta = datetime.now(timezone.utc) + timedelta(
                minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
            )

        to_encode = {
            "exp": expires_delta,
            "sub": subject,
            "iat": datetime.now(timezone.utc),
            "type": "refresh",
        }
        encoded_jwt = jwt.encode(
            to_encode, settings.REFRESH_SECRET_KEY, settings.ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def decode_access_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )

            return payload
        except JWTError as e:
            logger.error(f"error decoding token: {str(e)}")
            return None
