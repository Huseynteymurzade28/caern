"""FastAPI dependency factories: DB session, current user, RBAC enforcement."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import decode_token
from auth.rbac import can
from common_utils.exceptions import AuthenticationError, PermissionDeniedError
from data_access.database import get_db
from data_access.models.user import User, UserRole
from data_access.repositories.user_repo import UserRepository

bearer = HTTPBearer()


async def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_token(creds.credentials)
    user = await UserRepository(User, session).get(payload["sub"])
    if not user or not user.is_active:
        raise AuthenticationError("Kullanıcı bulunamadı veya pasif")
    return user


async def get_current_user_sse(
    session: Annotated[AsyncSession, Depends(get_db)],
    token: Optional[str] = Query(default=None),
    request: Request = None,
) -> User:
    """Auth dependency for SSE endpoints — accepts token via query param or Bearer header."""
    raw = token
    if not raw:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw = auth_header[7:]
    if not raw:
        raise AuthenticationError("Token eksik")
    payload = decode_token(raw)
    user = await UserRepository(User, session).get(payload["sub"])
    if not user or not user.is_active:
        raise AuthenticationError("Kullanıcı bulunamadı veya pasif")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserSSE = Annotated[User, Depends(get_current_user_sse)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


def require_role(*roles: UserRole):
    async def _check(user: CurrentUser):
        if user.role not in roles and user.role != UserRole.admin:
            raise PermissionDeniedError("Bu işlem için yetkiniz yok")
        return user

    return Depends(_check)


def require_permission(permission: str):
    async def _check(user: CurrentUser):
        if not can(user.role, permission):
            raise PermissionDeniedError(f"Yetki gerekli: {permission}")
        return user

    return Depends(_check)
