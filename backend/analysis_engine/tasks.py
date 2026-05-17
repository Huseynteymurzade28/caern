"""Celery tasks: async analysis pipeline execution."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from analysis_engine.celery_app import app
from analysis_engine.job_orchestrator import JobOrchestrator
from common_utils.exceptions import GPUTimeoutError, GeoAlignmentError, MissingCRSError
from common_utils.logger import get_logger
from notification.sse import broadcast_progress

log = get_logger(__name__)


class AnalysisTask(Task):
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        log.error("task_failed", task_id=task_id, exc=str(exc))


@app.task(
    bind=True,
    base=AnalysisTask,
    name="analysis_engine.tasks.run_analysis",
    max_retries=3,
    default_retry_delay=10,
    queue="analysis",
)
def run_analysis(
    self: Task,
    job_id: str,
    before_path: str,
    after_path: str,
    confidence_threshold: float = 0.5,
) -> dict:
    """Main Celery task: execute the full analysis pipeline."""
    from data_access.database import AsyncSessionLocal
    from data_access.models.analysis_job import AnalysisJob, JobStatus
    from data_access.models.change_result import ChangeResult, ClassLabel
    from data_access.repositories.job_repo import JobRepository
    from storage.minio_client import download_to_path
    from geoalchemy2.shape import from_shape
    from shapely.geometry import shape

    log.info("task_started", task_id=self.request.id, job_id=job_id)

    async def _run() -> dict:
        loop = asyncio.get_event_loop()

        async with AsyncSessionLocal() as session:
            job_repo = JobRepository(AnalysisJob, session)
            job = await job_repo.get(job_id)
            if not job:
                raise ValueError(f"Job bulunamadı: {job_id}")

            await job_repo.update_status(job, JobStatus.running, progress=5.0)
            await broadcast_progress(job_id, 5, "Analiz başlatıldı")

            orchestrator = JobOrchestrator(job_id, confidence_threshold)

            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                b_local = tmp_dir / "before.tif"
                a_local = tmp_dir / "after.tif"

                download_to_path(before_path, b_local)
                download_to_path(after_path, a_local)

                def _progress_cb(pct: float, msg: str = "") -> None:
                    asyncio.run_coroutine_threadsafe(
                        broadcast_progress(job_id, pct, msg), loop
                    )

                try:
                    features = await loop.run_in_executor(
                        None, lambda: orchestrator.run(b_local, a_local, _progress_cb)
                    )
                except SoftTimeLimitExceeded:
                    await job_repo.update_status(
                        job, JobStatus.failed, error_message="GPU zaman aşımı (3 dk)"
                    )
                    await broadcast_progress(job_id, 0, "FAILED:GPU timeout")
                    raise GPUTimeoutError("GPU zaman aşımı")

            await job_repo.update_status(job, JobStatus.aggregating, progress=90.0)
            await broadcast_progress(job_id, 90, "Sonuçlar kaydediliyor")

            # Persist ChangeResult rows
            for feat in features:
                geom = shape(feat["geometry"])
                props = feat["properties"]
                label_str = props.get("classLabel", "bina")
                label = ClassLabel(label_str) if label_str in ClassLabel.__members__.values() else ClassLabel.bina
                cr = ChangeResult(
                    job_id=job_id,
                    geom=from_shape(geom, srid=4326),
                    class_label=label,
                    confidence=props["confidence"],
                    change_type=props["changeType"],
                    area_m2=float(geom.area * 1e10),
                )
                session.add(cr)

            await session.flush()
            await job_repo.update_status(job, JobStatus.completed, progress=100.0)
            await broadcast_progress(job_id, 100, "COMPLETED")
            await session.commit()

        return {"job_id": job_id, "feature_count": len(features)}

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except (MissingCRSError, GeoAlignmentError) as exc:
        log.warning("validation_error", job_id=job_id, exc=str(exc))
        raise self.retry(exc=exc, countdown=5)
    except GPUTimeoutError:
        raise
    except Exception as exc:
        log.error("task_error", job_id=job_id, exc=str(exc), exc_info=True)
        raise
