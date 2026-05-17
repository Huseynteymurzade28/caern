"""Report ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_access.database import Base


class ReportFormat(str, enum.Enum):
    pdf = "pdf"
    csv = "csv"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    generating = "generating"
    completed = "completed"
    failed = "failed"


class Report(Base):
    """Generated analysis report (PDF or CSV)."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False
    )
    format: Mapped[ReportFormat] = mapped_column(Enum(ReportFormat), nullable=False)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="reports")
