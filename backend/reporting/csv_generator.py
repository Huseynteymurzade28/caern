"""CSV report generation."""
from __future__ import annotations

import csv
import io
from typing import List

from common_utils.exceptions import ReportGenerationError
from common_utils.logger import get_logger

log = get_logger(__name__)

HEADERS = ["id", "job_id", "class_label", "change_type", "confidence", "area_m2", "created_at"]


def generate_csv(job_id: str, results: List) -> bytes:
    try:
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=HEADERS)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    "id": str(r.id),
                    "job_id": job_id,
                    "class_label": r.class_label,
                    "change_type": r.change_type,
                    "confidence": f"{r.confidence:.4f}",
                    "area_m2": f"{r.area_m2 or 0:.2f}",
                    "created_at": str(r.created_at),
                }
            )
        data = buf.getvalue().encode("utf-8-sig")
        log.info("csv_generated", job_id=job_id, rows=len(results))
        return data
    except Exception as exc:
        raise ReportGenerationError(f"CSV üretimi başarısız: {exc}") from exc
