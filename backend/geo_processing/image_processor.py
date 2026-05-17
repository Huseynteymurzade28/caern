"""Convert raster tiles to numpy arrays for AI inference."""
from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np
import rasterio
from rasterio.plot import reshape_as_image


def load_as_rgb(path: Path, target_size: Tuple[int, int] | None = None) -> np.ndarray:
    """Load first 3 bands as HxWxC uint8 array suitable for YOLO/SAM."""
    import cv2

    with rasterio.open(path) as src:
        bands = min(src.count, 3)
        data = src.read(list(range(1, bands + 1)))

    img = reshape_as_image(data).astype(np.float32)

    # Normalize per-band to 0-255
    for c in range(img.shape[2]):
        mn, mx = img[:, :, c].min(), img[:, :, c].max()
        if mx > mn:
            img[:, :, c] = (img[:, :, c] - mn) / (mx - mn) * 255

    img = img.astype(np.uint8)

    # Pad to 3 channels if grayscale
    if img.shape[2] == 1:
        img = np.repeat(img, 3, axis=2)
    elif img.shape[2] == 2:
        img = np.concatenate([img, img[:, :, :1]], axis=2)

    if target_size:
        img = cv2.resize(img, target_size, interpolation=cv2.INTER_LINEAR)

    return img


def pixel_to_geo(
    px: float, py: float, transform: rasterio.transform.Affine
) -> Tuple[float, float]:
    """Convert pixel coordinates to geographic (lon, lat)."""
    lon, lat = rasterio.transform.xy(transform, py, px)
    return float(lon), float(lat)
