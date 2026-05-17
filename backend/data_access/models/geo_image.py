"""GeoImage ORM model."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from data_access.database import Base


class ImageFormat(str, enum.Enum):
    jpeg = "jpeg"
    png = "png"
    geotiff = "geotiff"
    tiff = "tiff"
    jp2 = "jp2"


class GeoImage(Base):
    """Uploaded satellite/drone image with spatial metadata."""

    __tablename__ = "geo_images"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    format: Mapped[ImageFormat] = mapped_column(Enum(ImageFormat), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    height: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crs: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bbox_minx: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_miny: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_maxx: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bbox_maxy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acquisition_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_by: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job_inputs: Mapped[List["JobInput"]] = relationship("JobInput", back_populates="geo_image")
