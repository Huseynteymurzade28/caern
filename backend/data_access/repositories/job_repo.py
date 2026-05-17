"""AnalysisJob repository."""
from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from data_access.models.analysis_job import AnalysisJob, JobStatus
from data_access.repositories.base import BaseRepository


class JobRepository(BaseRepository[AnalysisJob]):
    async def get_by_owner(self, owner_id: str, limit: int = 50) -> List[AnalysisJob]:
        result = await self.session.execute(
            select(AnalysisJob)
            .where(AnalysisJob.owner_id == owner_id)
            .order_by(AnalysisJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        job: AnalysisJob,
        status: JobStatus,
        progress: Optional[float] = None,
        error_message: Optional[str] = None,
    ) -> AnalysisJob:
        job.status = status
        if progress is not None:
            job.progress = progress
        if error_message is not None:
            job.error_message = error_message
        await self.session.flush()
        return job

    async def update_progress(self, job: AnalysisJob, progress: float) -> AnalysisJob:
        job.progress = progress
        await self.session.flush()
        return job

    async def get_active_jobs(self) -> List[AnalysisJob]:
        result = await self.session.execute(
            select(AnalysisJob).where(
                AnalysisJob.status.in_([JobStatus.running, JobStatus.queued, JobStatus.validating])
            )
        )
        return list(result.scalars().all())
