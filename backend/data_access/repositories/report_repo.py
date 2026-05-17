"""Report repository."""
from __future__ import annotations

from typing import List

from sqlalchemy import select

from data_access.models.report import Report, ReportStatus
from data_access.repositories.base import BaseRepository


class ReportRepository(BaseRepository[Report]):
    async def get_by_job(self, job_id: str) -> List[Report]:
        result = await self.session.execute(
            select(Report).where(Report.job_id == job_id).order_by(Report.created_at.desc())
        )
        return list(result.scalars().all())

    async def mark_completed(self, report: Report, storage_path: str, size_bytes: int) -> Report:
        from datetime import datetime, timezone

        report.status = ReportStatus.completed
        report.storage_path = storage_path
        report.size_bytes = size_bytes
        report.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return report

    async def mark_failed(self, report: Report) -> Report:
        report.status = ReportStatus.failed
        await self.session.flush()
        return report
