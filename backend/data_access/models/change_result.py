"""ChangeResult ORM model with PostGIS geometry."""
from __future__ import annotations

import enum
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_access.database import Base


class ClassLabel(str, enum.Enum):
    bina = "bina"
    arac = "araç"
    agac = "ağaç"
    tarim_alani = "tarım_alanı"


class ChangeResult(Base):
    """Detected change polygon with spatial geometry."""

    __tablename__ = "change_results"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    geom = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    class_label: Mapped[ClassLabel] = mapped_column(Enum(ClassLabel), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "new" | "lost"
    area_m2: Mapped[float] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped["AnalysisJob"] = relationship("AnalysisJob", back_populates="change_results")
