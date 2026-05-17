"""Extract geospatial metadata from raster images."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import rasterio

from common_utils.exceptions import MissingCRSError, UnsupportedFormatError
from common_utils.logger import get_logger

log = get_logger(__name__)

SUPPORTED_FORMATS = {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".jp2"}


@dataclass
class ImageMetadata:
    width: int
    height: int
    crs: Optional[str]
    bbox: Optional[Tuple[float, float, float, float]]  # minx, miny, maxx, maxy
    band_count: int
    dtype: str


def extract_metadata(path: Path) -> ImageMetadata:
    """Open raster and read spatial metadata."""
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise UnsupportedFormatError(f"Desteklenmeyen format: {path.suffix}")

    with rasterio.open(path) as src:
        crs_str = src.crs.to_string() if src.crs else None
        if src.crs:
            bounds = src.bounds
            bbox = (bounds.left, bounds.bottom, bounds.right, bounds.top)
        else:
            bbox = None

        meta = ImageMetadata(
            width=src.width,
            height=src.height,
            crs=crs_str,
            bbox=bbox,
            band_count=src.count,
            dtype=str(src.dtypes[0]),
        )

    log.debug("metadata_extracted", path=str(path), crs=meta.crs, size=f"{meta.width}x{meta.height}")
    return meta


def validate_crs(path: Path) -> None:
    """Raise MissingCRSError if the image lacks CRS information."""
    meta = extract_metadata(path)
    if not meta.crs:
        raise MissingCRSError(f"Görüntüde CRS bilgisi yok: {path.name}")
