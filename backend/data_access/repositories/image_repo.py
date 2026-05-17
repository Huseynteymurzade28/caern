"""GeoImage repository."""
from __future__ import annotations

from typing import List

from sqlalchemy import select

from data_access.models.geo_image import GeoImage
from data_access.repositories.base import BaseRepository


class ImageRepository(BaseRepository[GeoImage]):
    async def get_by_uploader(self, user_id: str, limit: int = 50) -> List[GeoImage]:
        result = await self.session.execute(
            select(GeoImage)
            .where(GeoImage.uploaded_by == user_id)
            .order_by(GeoImage.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
