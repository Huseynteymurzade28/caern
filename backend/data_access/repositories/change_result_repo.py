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
                ChangeResult.area_px,
                ChangeResult.centroid_lat,
                ChangeResult.centroid_lon,
                ChangeResult.bbox_minx,
                ChangeResult.bbox_miny,
                ChangeResult.bbox_maxx,
                ChangeResult.bbox_maxy,
                ChangeResult.created_at,
                ST_AsGeoJSON(ChangeResult.geom).label("geom_json"),
            ).where(ChangeResult.job_id == job_id)
        )
        import json

        features: List[dict] = []
        for row in rows:
            category = row.change_type
            features.append(
                {
                    "type": "Feature",
                    "id": str(row.id),
                    "geometry": json.loads(row.geom_json),
                    "properties": {
                        "category": category,
                        "classLabel": getattr(row.class_label, "value", row.class_label),
                        "confidence": row.confidence,
                        "changeType": category,  # legacy alias for older clients
                        "areaM2": row.area_m2,
                        "areaPx": row.area_px,
                        "centroid": [row.centroid_lon, row.centroid_lat]
                        if row.centroid_lat is not None
                        else None,
                        "bbox": [row.bbox_minx, row.bbox_miny, row.bbox_maxx, row.bbox_maxy]
                        if row.bbox_minx is not None
                        else None,
                        "createdAt": row.created_at.isoformat() if row.created_at else None,
                    },
                }
            )
        return features
