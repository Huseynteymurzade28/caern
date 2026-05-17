"""User repository."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from data_access.models.user import User, UserRole
from data_access.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def record_failed_login(self, user: User, locked_until: Optional[datetime] = None) -> User:
        user.failed_login_attempts += 1
        if locked_until:
            user.is_locked = True
            user.locked_until = locked_until
        await self.session.flush()
        return user

    async def reset_login_attempts(self, user: User) -> User:
        user.failed_login_attempts = 0
        user.is_locked = False
        user.locked_until = None
        user.last_login = datetime.now(timezone.utc)
        await self.session.flush()
        return user

    async def update_role(self, user: User, role: UserRole) -> User:
        user.role = role
        await self.session.flush()
        return user

    async def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self.session.flush()
        return user
