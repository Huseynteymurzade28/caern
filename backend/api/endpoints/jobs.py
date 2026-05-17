"""Analysis job endpoints: create, progress SSE, results."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from analysis_engine.tasks import run_analysis
from api.deps import CurrentUser, CurrentUserSSE, DBSession, require_permission
from common_utils.exceptions import NotFoundError, PermissionDeniedError
from data_access.models.analysis_job import AnalysisJob, ImageRole, JobInput, JobStatus
from data_access.models.audit_log import AuditAction, AuditLog
from data_access.models.geo_image import GeoImage
from data_access.repositories.change_result_repo import ChangeResultRepository
from data_access.repositories.image_repo import ImageRepository
from data_access.repositories.job_repo import JobRepository
from notification.sse import stream_progress

router = APIRouter(prefix="/jobs", tags=["Jobs"])


class CreateJobRequest(BaseModel):
    before_image_id: str
    after_image_id: str
    model_id: Optional[str] = None
    confidence_threshold: float = 0.5


class JobResponse(BaseModel):
    id: str
    status: str
    progress: float
    created_at: datetime
    owner_id: str

    class Config:
        from_attributes = True


@router.get("", response_model=List[JobResponse], dependencies=[require_permission("jobs:read")])
async def list_jobs(session: DBSession, current_user: CurrentUser):
    """List analysis jobs for the current user."""
    job_repo = JobRepository(AnalysisJob, session)
    jobs = await job_repo.get_by_owner(current_user.id)
    return jobs


@router.post("", response_model=JobResponse, dependencies=[require_permission("jobs:write")])
async def create_job(body: CreateJobRequest, session: DBSession, current_user: CurrentUser):
    """Create and enqueue an analysis job."""
    img_repo = ImageRepository(GeoImage, session)

    before_img = await img_repo.get(body.before_image_id)
    if not before_img:
        raise NotFoundError(f"Önceki görüntü bulunamadı: {body.before_image_id}")
    after_img = await img_repo.get(body.after_image_id)
    if not after_img:
        raise NotFoundError(f"Sonraki görüntü bulunamadı: {body.after_image_id}")

    job = AnalysisJob(
        owner_id=current_user.id,
        model_id=body.model_id,
        confidence_threshold=body.confidence_threshold,
        status=JobStatus.created,
    )
    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.create(job)

    session.add(JobInput(job_id=job.id, image_id=before_img.id, role=ImageRole.before))
    session.add(JobInput(job_id=job.id, image_id=after_img.id, role=ImageRole.after))
    await session.flush()

    # Enqueue Celery task
    task = run_analysis.apply_async(
        kwargs={
            "job_id": job.id,
            "before_path": before_img.storage_path,
            "after_path": after_img.storage_path,
            "confidence_threshold": body.confidence_threshold,
        },
        queue="analysis",
    )
    await job_repo.update_status(job, JobStatus.queued)
    job.celery_task_id = task.id

    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.JOB_CREATED,
        resource_type="AnalysisJob",
        resource_id=job.id,
    ))

    return job


@router.get("/{job_id}/progress")
async def job_progress_sse(job_id: str, session: DBSession, current_user: CurrentUserSSE):
    """SSE stream for real-time job progress (0-100)."""
    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.get(job_id)
    if not job:
        raise NotFoundError(f"Job bulunamadı: {job_id}")
    if job.owner_id != current_user.id and current_user.role.value != "admin":
        raise PermissionDeniedError("Bu job'a erişim yetkiniz yok")

    return StreamingResponse(
        stream_progress(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{job_id}/results", dependencies=[require_permission("jobs:read")])
async def job_results(job_id: str, session: DBSession, current_user: CurrentUser):
    """Return GeoJSON FeatureCollection of detected changes."""
    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.get(job_id)
    if not job:
        raise NotFoundError(f"Job bulunamadı: {job_id}")

    from data_access.models.change_result import ChangeResult
    cr_repo = ChangeResultRepository(ChangeResult, session)
    features = await cr_repo.get_geojson_features(job_id)

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "jobId": job_id,
            "status": job.status,
            "featureCount": len(features),
        },
    }


@router.delete("/{job_id}", dependencies=[require_permission("jobs:write")])
async def cancel_job(job_id: str, session: DBSession, current_user: CurrentUser):
    """Cancel a running or queued job."""
    from celery.result import AsyncResult
    from analysis_engine.celery_app import app as celery_app

    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.get(job_id)
    if not job:
        raise NotFoundError(f"Job bulunamadı: {job_id}")

    if job.celery_task_id:
        AsyncResult(job.celery_task_id, app=celery_app).revoke(terminate=True)

    await job_repo.update_status(job, JobStatus.cancelled)
    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.JOB_CANCELLED,
        resource_type="AnalysisJob",
        resource_id=job_id,
    ))
    return {"cancelled": True, "job_id": job_id}
