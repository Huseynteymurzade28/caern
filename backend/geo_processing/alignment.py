"""Pixel-level geographic alignment using GDAL warp."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject

from common_utils.exceptions import GeoAlignmentError
from common_utils.logger import get_logger

log = get_logger(__name__)

TARGET_CRS = "EPSG:4326"


def align_to_reference(source: Path, reference: Path, output: Path) -> Path:
    """Reproject and resample source to match reference image grid."""
    try:
        with rasterio.open(reference) as ref:
            ref_crs = ref.crs
            ref_transform = ref.transform
            ref_width = ref.width
            ref_height = ref.height

        with rasterio.open(source) as src:
            transform, width, height = calculate_default_transform(
                src.crs, ref_crs, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update(
                crs=ref_crs,
                transform=ref_transform,
                width=ref_width,
                height=ref_height,
                compress="lzw",
            )

            with rasterio.open(output, "w", **kwargs) as dst:
                for band_idx in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band_idx),
                        destination=rasterio.band(dst, band_idx),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=ref_transform,
                        dst_crs=ref_crs,
                        resampling=Resampling.bilinear,
                    )

        log.info("alignment_complete", source=str(source), output=str(output))
        return output

    except Exception as exc:
        raise GeoAlignmentError(f"Coğrafi hizalama başarısız: {exc}") from exc


def normalize_to_wgs84(source: Path, output: Path) -> Path:
    """Reproject any CRS image to WGS-84 (EPSG:4326)."""
    try:
        with rasterio.open(source) as src:
            if src.crs and src.crs.to_epsg() == 4326:
                import shutil
                shutil.copy2(source, output)
                return output

            transform, width, height = calculate_default_transform(
                src.crs, TARGET_CRS, src.width, src.height, *src.bounds
            )
            kwargs = src.meta.copy()
            kwargs.update(crs=TARGET_CRS, transform=transform, width=width, height=height)

            with rasterio.open(output, "w", **kwargs) as dst:
                for band_idx in range(1, src.count + 1):
                    reproject(
                        source=rasterio.band(src, band_idx),
                        destination=rasterio.band(dst, band_idx),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=TARGET_CRS,
                        resampling=Resampling.bilinear,
                    )
        return output
    except Exception as exc:
        raise GeoAlignmentError(f"WGS-84 dönüştürme hatası: {exc}") from exc
