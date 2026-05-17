"""Auth service: login, refresh, user creation with lockout logic."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Tuple

from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from auth.password import hash_password, verify_password
from common_utils.config import settings
from common_utils.exceptions import (
    AccountLockedError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from common_utils.logger import get_logger
from data_access.models.user import User, UserRole
from data_access.repositories.user_repo import UserRepository

log = get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = UserRepository(User, session)

    async def login(self, email: str, password: str) -> Tuple[str, str]:
        """Validate credentials, enforce lockout, return (access, refresh)."""
        user = await self.repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Geçersiz e-posta veya şifre")

        if user.is_locked and user.locked_until:
            if datetime.now(timezone.utc) < user.locked_until:
                raise AccountLockedError(
                    f"Hesap kilitlendi. {user.locked_until.strftime('%H:%M')} sonra tekrar deneyin."
                )
            else:
                await self.repo.reset_login_attempts(user)

        if not verify_password(password, user.password_hash):
            locked_until = None
            if user.failed_login_attempts + 1 >= settings.max_login_attempts:
                locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.lockout_minutes)
            await self.repo.record_failed_login(user, locked_until=locked_until)
            raise AuthenticationError("Geçersiz e-posta veya şifre")

        await self.repo.reset_login_attempts(user)
        log.info("login_success", user_id=user.id, email=user.email)

        access = create_access_token(user.id, extra={"role": user.role, "email": user.email})
        refresh = create_refresh_token(user.id)
        return access, refresh

    async def refresh(self, refresh_token: str) -> Tuple[str, str]:
        payload = decode_token(refresh_token, expected_type="refresh")
        user = await self.repo.get(payload["sub"])
        if not user or not user.is_active:
            raise AuthenticationError("Geçersiz kullanıcı")
        access = create_access_token(user.id, extra={"role": user.role, "email": user.email})
        new_refresh = create_refresh_token(user.id)
        return access, new_refresh

    async def create_user(
        self, email: str, username: str, password: str, role: UserRole = UserRole.viewer
    ) -> User:
        if await self.repo.get_by_email(email):
            raise ConflictError(f"E-posta zaten kayıtlı: {email}")
        if await self.repo.get_by_username(username):
            raise ConflictError(f"Kullanıcı adı zaten alınmış: {username}")

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        return await self.repo.create(user)
