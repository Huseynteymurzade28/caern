"""CSV report generation.

Çıkış kolonları (Türkçe başlık + İngilizce key):
  nesne_id, kategori, alan_m2, alan_km2, guven_skoru,
  merkez_lat, merkez_lon, sinir_kutucuk, tespit_tarihi,
  analiz_id, model_adi
"""
from __future__ import annotations

import csv
import io
from typing import Iterable, List, Optional

from common_utils.exceptions import ReportGenerationError
from common_utils.logger import get_logger

log = get_logger(__name__)

HEADERS = [
    "nesne_id",
    "kategori",
    "alan_m2",
    "alan_km2",
    "guven_skoru",
    "merkez_lat",
    "merkez_lon",
    "sinir_kutucuk",
    "tespit_tarihi",
    "analiz_id",
    "model_adi",
]


def generate_csv(
    job_id: str,
    results: Iterable,
    model_name: Optional[str] = None,
) -> bytes:
    try:
        buf = io.StringIO()
        # UTF-8 BOM — Excel'in Türkçe karakterleri doğru göstermesi için
        buf.write("﻿")
        writer = csv.DictWriter(buf, fieldnames=HEADERS)
        writer.writeheader()

        for r in results:
            bbox_parts = [
                getattr(r, attr, None)
                for attr in ("bbox_minx", "bbox_miny", "bbox_maxx", "bbox_maxy")
            ]
            bbox_str = (
                ";".join(f"{v:.6f}" for v in bbox_parts)
                if all(v is not None for v in bbox_parts)
                else ""
            )
            area_m2 = float(getattr(r, "area_m2", 0.0) or 0.0)
            writer.writerow(
                {
                    "nesne_id": str(r.id),
                    "kategori": getattr(r, "change_type", ""),
                    "alan_m2": f"{area_m2:.2f}",
                    "alan_km2": f"{area_m2 / 1_000_000.0:.6f}",
                    "guven_skoru": f"{float(r.confidence):.4f}",
                    "merkez_lat": f"{float(r.centroid_lat):.6f}"
                    if getattr(r, "centroid_lat", None) is not None
                    else "",
                    "merkez_lon": f"{float(r.centroid_lon):.6f}"
                    if getattr(r, "centroid_lon", None) is not None
                    else "",
                    "sinir_kutucuk": bbox_str,
                    "tespit_tarihi": str(r.created_at) if r.created_at else "",
                    "analiz_id": job_id,
                    "model_adi": model_name or "classical-CV+SAM",
                }
            )
        data = buf.getvalue().encode("utf-8")
        log.info("csv_generated", job_id=job_id, rows=sum(1 for _ in []))
        return data
    except Exception as exc:
        raise ReportGenerationError(f"CSV üretimi başarısız: {exc}") from exc
