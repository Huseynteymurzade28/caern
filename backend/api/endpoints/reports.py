"""Report generation endpoint (PDF / CSV Façade)."""
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone

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


@router.post("", dependencies=[require_permission("reports:write")])
async def create_report(body: CreateReportRequest, session: DBSession, current_user: CurrentUser):
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

    if fmt == ReportFormat.pdf:
        data = generate_pdf(body.job_id, results)
        content_type = "application/pdf"
        ext = "pdf"
    else:
        data = generate_csv(body.job_id, results)
        content_type = "text/csv"
        ext = "csv"

    object_name = f"reports/{body.job_id}/{report.id}.{ext}"
    upload_file(object_name, io.BytesIO(data), len(data), content_type=content_type)
    await rpt_repo.mark_completed(report, object_name, len(data))

    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.REPORT_GENERATED,
        resource_type="Report",
        resource_id=report.id,
    ))

    return {"id": report.id, "format": fmt, "storage_path": object_name, "size_bytes": len(data)}


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
