"""Report generation endpoint (PDF / CSV).

İki modu destekler:
  * POST /reports            — raporu üretir, MinIO'ya yükler ve metadata döner
  * GET  /reports/{job}/download.{ext}  — doğrudan stream (UI buton bunu çağırır)
  * GET  /reports/{id}/download  — eski preset URL (uyumluluk için)
"""
from __future__ import annotations

import io

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from api.deps import CurrentUser, DBSession, require_permission
from common_utils.exceptions import NotFoundError
from data_access.models.analysis_job import AnalysisJob
from data_access.models.audit_log import AuditAction, AuditLog
from data_access.models.change_result import ChangeResult
from data_access.models.report import Report, ReportFormat, ReportStatus
from data_access.repositories.change_result_repo import ChangeResultRepository
from data_access.repositories.job_repo import JobRepository
from data_access.repositories.report_repo import ReportRepository
from reporting.csv_generator import generate_csv
from reporting.pdf_generator import generate_pdf
from storage.minio_client import upload_file

router = APIRouter(prefix="/reports", tags=["Reports"])


class CreateReportRequest(BaseModel):
    job_id: str
    format: str  # "pdf" | "csv"


class ReportSummary(BaseModel):
    id: str
    job_id: str
    format: str
    status: str
    size_bytes: int | None
    storage_path: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("", dependencies=[require_permission("reports:read")])
async def list_reports(session: DBSession, current_user: CurrentUser):
    """List all reports visible to the current user (most-recent first)."""
    from sqlalchemy import select
    result = await session.execute(
        select(Report).order_by(Report.created_at.desc()).limit(200)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "format": r.format.value if hasattr(r.format, "value") else r.format,
            "status": r.status.value if hasattr(r.status, "value") else r.status,
            "size_bytes": r.size_bytes,
            "storage_path": r.storage_path,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def _render_report(
    *,
    job: AnalysisJob,
    results: list[ChangeResult],
    user_email: str,
    fmt: ReportFormat,
) -> tuple[bytes, str]:
    """Render the report body. Returns (data, content_type)."""
    if fmt == ReportFormat.csv:
        data = generate_csv(
            job.id,
            results,
            model_name=job.detection_mode or "classical-CV",
        )
        return data, "text/csv; charset=utf-8"

    data = generate_pdf(
        job.id,
        results,
        metrics=job.metric_summary or {},
        user_email=user_email,
        detection_mode=job.detection_mode or "classical-CV",
        confidence_threshold=job.confidence_threshold,
        min_area_m2=job.min_area_m2,
    )
    return data, "application/pdf"


@router.post("", dependencies=[require_permission("reports:write")])
async def create_report(
    body: CreateReportRequest, session: DBSession, current_user: CurrentUser
):
    """Generate and store a PDF or CSV report for an analysis job."""
    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.get(body.job_id)
    if not job:
        raise NotFoundError(f"Job bulunamadı: {body.job_id}")

    cr_repo = ChangeResultRepository(ChangeResult, session)
    results = await cr_repo.get_by_job(body.job_id)

    fmt = ReportFormat(body.format)
    report = Report(
        job_id=body.job_id,
        format=fmt,
        status=ReportStatus.generating,
        created_by=current_user.id,
    )
    rpt_repo = ReportRepository(Report, session)
    report = await rpt_repo.create(report)

    data, content_type = await _render_report(
        job=job, results=results, user_email=current_user.email, fmt=fmt
    )

    ext = "pdf" if fmt == ReportFormat.pdf else "csv"
    object_name = f"reports/{body.job_id}/{report.id}.{ext}"
    upload_file(object_name, io.BytesIO(data), len(data), content_type=content_type)
    await rpt_repo.mark_completed(report, object_name, len(data))

    session.add(
        AuditLog(
            user_id=current_user.id,
            action=AuditAction.REPORT_GENERATED,
            resource_type="Report",
            resource_id=report.id,
        )
    )

    return {
        "id": report.id,
        "format": fmt,
        "storage_path": object_name,
        "size_bytes": len(data),
    }


@router.get("/jobs/{job_id}/download.{ext}", dependencies=[require_permission("reports:read")])
async def stream_job_report(
    job_id: str, ext: str, session: DBSession, current_user: CurrentUser
):
    """Generate the report on-the-fly and stream it to the client.

    UI'nin "Rapor İndir" butonları bu uç noktayı kullanır — MinIO'ya
    yükleme + tekrar indirme yerine doğrudan response gövdesine yazar.
    """
    ext = ext.lower()
    if ext not in ("pdf", "csv"):
        raise NotFoundError(f"Desteklenmeyen format: {ext}")

    job_repo = JobRepository(AnalysisJob, session)
    job = await job_repo.get(job_id)
    if not job:
        raise NotFoundError(f"Job bulunamadı: {job_id}")

    cr_repo = ChangeResultRepository(ChangeResult, session)
    results = await cr_repo.get_by_job(job_id)

    fmt = ReportFormat.pdf if ext == "pdf" else ReportFormat.csv
    data, content_type = await _render_report(
        job=job, results=results, user_email=current_user.email, fmt=fmt
    )

    session.add(
        AuditLog(
            user_id=current_user.id,
            action=AuditAction.REPORT_GENERATED,
            resource_type="AnalysisJob",
            resource_id=job_id,
        )
    )

    filename = f"caern_analiz_{job_id[:8]}.{ext}"
    return StreamingResponse(
        iter([data]),
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


@router.get("/{report_id}/download", dependencies=[require_permission("reports:read")])
async def download_report(report_id: str, session: DBSession, current_user: CurrentUser):
    """Return a pre-signed download URL for the report."""
    rpt_repo = ReportRepository(Report, session)
    report = await rpt_repo.get(report_id)
    if not report:
        raise NotFoundError(f"Rapor bulunamadı: {report_id}")

    from storage.minio_client import get_presigned_url

    url = get_presigned_url(report.storage_path)
    return {"download_url": url, "expires_in": 3600}
