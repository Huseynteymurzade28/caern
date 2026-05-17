"""AIModel repository."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update

from data_access.models.ai_model import AIModel
from data_access.repositories.base import BaseRepository


class AIModelRepository(BaseRepository[AIModel]):
    async def get_active(self) -> Optional[AIModel]:
        result = await self.session.execute(
            select(AIModel).where(AIModel.is_active == True)  # noqa: E712
        )
        return result.scalar_one_or_none()

    async def deactivate_all(self) -> None:
        await self.session.execute(update(AIModel).values(is_active=False))
        await self.session.flush()

    async def activate(self, model: AIModel) -> AIModel:
        await self.deactivate_all()
        model.is_active = True
        await self.session.flush()
        return model
