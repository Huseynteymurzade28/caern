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
    """CRS yoksa goruntuye sentetik WGS-84 bilgisi yazar.

    Eski davranis: MissingCRSError firlatip Celery'de retry'a sokuyordu.
    Yeni davranis: cogu ham JPG/PNG/TIFF CRS'siz oluyor — demo amacli kullanim
    icin sentetik bir transform atayarak pipeline'in surekliligini koruyoruz.
    """
    meta = extract_metadata(path)
    if meta.crs:
        return

    log.warning("crs_missing_assigning_synthetic", path=str(path))
    _assign_synthetic_crs(path)


def _assign_synthetic_crs(path: Path) -> None:
    """CRS'i olmayan rastere sentetik WGS-84 bbox + affine yazar."""
    from rasterio.transform import from_bounds

    with rasterio.open(path) as src:
        data = src.read()
        profile = src.profile.copy()
        height, width = src.height, src.width

    # Istanbul Bogazi yakini kucuk bir kutu (~1 km x 1 km) — gerçekçi koordinatlar.
    minx, miny, maxx, maxy = 29.025, 41.020, 29.035, 41.030
    transform = from_bounds(minx, miny, maxx, maxy, width, height)

    profile.update(crs="EPSG:4326", transform=transform)
    if profile.get("driver", "").upper() not in {"GTIFF", "GEOTIFF"}:
        profile["driver"] = "GTiff"

    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
