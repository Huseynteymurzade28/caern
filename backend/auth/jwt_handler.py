"""JWT access + refresh token creation and validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

from common_utils.config import settings
from common_utils.exceptions import AuthenticationError, TokenExpiredError


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, extra: Dict[str, Any] | None = None) -> str:
    expire = _now() + timedelta(hours=settings.jwt_access_token_expire_hours)
    payload: Dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "access",
        **(extra or {}),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    expire = _now() + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": _now(),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: str = "access") -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token süresi dolmuş")
    except JWTError:
        raise AuthenticationError("Geçersiz token")

    if payload.get("type") != expected_type:
        raise AuthenticationError("Geçersiz token türü")

    return payload
