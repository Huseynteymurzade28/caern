"""AnalysisJob + JobInput ORM models."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_access.database import Base


class JobStatus(str, enum.Enum):
    created = "created"
    validating = "validating"
    queued = "queued"
    running = "running"
    aggregating = "aggregating"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    archived = "archived"


class ImageRole(str, enum.Enum):
    before = "before"
    after = "after"


class AnalysisJob(Base):
    """Central coordinator for a single analysis request."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    owner_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.created, index=True
    )
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)
    min_area_m2: Mapped[float] = mapped_column(Float, default=25.0, nullable=False)
    detection_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metric_summary: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship("User", back_populates="jobs")
    ai_model: Mapped[Optional["AIModel"]] = relationship("AIModel", back_populates="jobs")
    inputs: Mapped[List["JobInput"]] = relationship(
        "JobInput", back_populates="job", cascade="all, delete-orphan"
    )
    change_results: Mapped[List["ChangeResult"]] = relationship(
        "ChangeResult", back_populates="job", cascade="all, delete-orphan"
    )
    reports: Mapped[List["Report"]] = relationship(
        "Report", back_populates="job", cascade="all, delete-orphan"
    )


class JobInput(Base):
    """Junction table: which images are used in a job, and in what role."""

    __tablename__ = "job_inputs"

    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), primary_key=True
    )
    image_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("geo_images.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[ImageRole] = mapped_column(Enum(ImageRole), nullable=False)

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="inputs")
    geo_image: Mapped["GeoImage"] = relationship("GeoImage", back_populates="job_inputs")
