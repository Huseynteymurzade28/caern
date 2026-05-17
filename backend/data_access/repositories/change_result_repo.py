"""ChangeResult repository."""
from __future__ import annotations

from typing import List

from geoalchemy2.functions import ST_AsGeoJSON
from sqlalchemy import select

from data_access.models.change_result import ChangeResult
from data_access.repositories.base import BaseRepository


class ChangeResultRepository(BaseRepository[ChangeResult]):
    async def get_by_job(self, job_id: str) -> List[ChangeResult]:
        result = await self.session.execute(
            select(ChangeResult).where(ChangeResult.job_id == job_id)
        )
        return list(result.scalars().all())

    async def get_geojson_features(self, job_id: str) -> List[dict]:
        """Return GeoJSON Feature dicts for Leaflet rendering."""
        rows = await self.session.execute(
            select(
                ChangeResult.id,
                ChangeResult.class_label,
                ChangeResult.confidence,
                ChangeResult.change_type,
                ChangeResult.area_m2,
                ST_AsGeoJSON(ChangeResult.geom).label("geom_json"),
            ).where(ChangeResult.job_id == job_id)
        )
        import json

        return [
            {
                "type": "Feature",
                "id": str(row.id),
                "geometry": json.loads(row.geom_json),
                "properties": {
                    "classLabel": row.class_label,
                    "confidence": row.confidence,
                    "changeType": row.change_type,
                    "areaM2": row.area_m2,
                },
            }
            for row in rows
        ]
