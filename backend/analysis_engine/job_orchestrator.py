"""AnalysisJob orchestrator: pipeline + metric aggregation.

Pipeline:
  1. CRS doğrulama → WGS-84'e dönüştürme → ko-registrasyon
  2. RGB yükleme + sub-pixel hizalama
  3. NDI tabanlı değişim tespiti + bağlı bileşen + otomatik kategorize
  4. (Opsiyonel) SAM rafine etmesi — bbox → hassas poligon
  5. Piksel koordinatlarını WGS-84'e çevir
  6. Metrik özet (toplam alan, kategori dağılımı, histogram, top-5 GeoJSON)
"""
from __future__ import annotations

import concurrent.futures
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np
import rasterio
from pyproj import Geod
from shapely.geometry import Polygon, mapping

from ai_models.model_registry import registry
from analysis_engine.classical_detector import (
    DEFAULT_MIN_AREA_M2,
    DEFAULT_PIXEL_AREA_M2,
    RegionDetection,
    detect_changes as classical_detect,
    pixel_diff_histogram,
)
from common_utils.exceptions import JobCancelledError
from common_utils.logger import get_logger
from geo_processing.alignment import align_to_reference, normalize_to_wgs84
from geo_processing.image_processor import load_as_rgb
from geo_processing.metadata import validate_crs

log = get_logger(__name__)

MAX_SAM_REFINE = 15
SAM_MAX_SIDE = 1024
SAM_TIMEOUT_SECONDS = 60

_GEOD = Geod(ellps="WGS84")


class JobOrchestrator:
    """Coordinates the full analysis pipeline for a single job."""

    def __init__(
        self,
        job_id: str,
        confidence_threshold: float = 0.5,
        min_area_m2: float = DEFAULT_MIN_AREA_M2,
    ) -> None:
        self.job_id = job_id
        self.confidence_threshold = confidence_threshold
        self.min_area_m2 = min_area_m2
        self._cancelled = False
        self._detection_mode = "unknown"

    def cancel(self) -> None:
        self._cancelled = True

    def _check_cancelled(self) -> None:
        if self._cancelled:
            raise JobCancelledError("İş iptal edildi")

    def run(
        self,
        before_path: Path,
        after_path: Path,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Returns {"features": [...], "metrics": {...}}."""

        def _progress(pct: float, msg: str = "") -> None:
            if progress_callback:
                progress_callback(pct, msg)
            log.info("job_progress", job_id=self.job_id, pct=pct, msg=msg)

        _progress(5, "CRS doğrulanıyor")
        validate_crs(before_path)
        validate_crs(after_path)
        self._check_cancelled()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)

            _progress(15, "WGS-84'e dönüştürülüyor")
            before_wgs = normalize_to_wgs84(before_path, tmp_dir / "before_wgs.tif")
            after_wgs = normalize_to_wgs84(after_path, tmp_dir / "after_wgs.tif")
            self._check_cancelled()

            _progress(25, "Coğrafi hizalanıyor")
            after_aligned = align_to_reference(
                after_wgs, before_wgs, tmp_dir / "after_aligned.tif"
            )
            self._check_cancelled()

            _progress(35, "Görüntüler yükleniyor")
            before_rgb = load_as_rgb(before_wgs)
            after_rgb = load_as_rgb(after_aligned)
            self._check_cancelled()

            pixel_area_m2 = self._estimate_pixel_area_m2(before_wgs)
            log.info("pixel_area_m2", v=pixel_area_m2)

            _progress(45, "Değişim bölgeleri tespit ediliyor")
            regions, diff_img = classical_detect(
                before_rgb,
                after_rgb,
                min_area_m2=self.min_area_m2,
                pixel_area_m2=pixel_area_m2,
            )
            self._check_cancelled()

            _progress(60, "SAM modeli yükleniyor")
            sam = self._try_load_sam()
            self._check_cancelled()

            if sam is not None and regions:
                _progress(70, f"SAM ile {len(regions)} bölge rafine ediliyor")
                try:
                    regions = self._refine_with_sam(sam, after_rgb, regions)
                    self._detection_mode = "SAM-refined"
                except Exception as exc:
                    log.warning("sam_refine_failed", job_id=self.job_id, exc=str(exc))
                    self._detection_mode = "classical-CV"
            else:
                self._detection_mode = "classical-CV"

            _progress(85, "Coğrafi koordinatlar hesaplanıyor")
            with rasterio.open(before_wgs) as src:
                transform = src.transform

            features = self._regions_to_features(regions, transform)

            _progress(
                92,
                f"Metrikler hesaplanıyor ({self._detection_mode}, {len(features)} bölge)",
            )
            metrics = self._compute_metrics(
                features=features,
                regions=regions,
                diff_img=diff_img,
                img_shape=before_rgb.shape[:2],
                pixel_area_m2=pixel_area_m2,
            )
            metrics["detection_mode"] = self._detection_mode

            return {"features": features, "metrics": metrics}

    # ─── SAM ──────────────────────────────────────────────────────────

    def _try_load_sam(self):
        try:
            sam = registry.get_sam()
            log.info("sam_ready", job_id=self.job_id)
            return sam
        except Exception as exc:
            log.warning("sam_load_failed", job_id=self.job_id, exc=str(exc))
            return None

    def _refine_with_sam(
        self, sam, image: np.ndarray, regions: List[RegionDetection]
    ) -> List[RegionDetection]:
        if not regions:
            return regions

        to_refine = regions[:MAX_SAM_REFINE]
        passthrough = regions[MAX_SAM_REFINE:]

        H, W = image.shape[:2]
        max_side = max(H, W)
        if max_side > SAM_MAX_SIDE:
            scale = SAM_MAX_SIDE / max_side
            new_w, new_h = int(round(W * scale)), int(round(H * scale))
            small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            small = image

        small_boxes = [[b * scale for b in r.bbox] for r in to_refine]

        def _do_predict():
            return sam.predict_with_boxes(small, small_boxes)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                refined = pool.submit(_do_predict).result(timeout=SAM_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            log.warning("sam_timeout", job_id=self.job_id)
            return regions

        result: List[RegionDetection] = []
        for orig, ref in zip(to_refine, refined):
            new_mask = None
            new_bbox = orig.bbox
            if ref.mask is not None and ref.mask.any():
                if scale < 1.0:
                    new_mask = cv2.resize(
                        ref.mask.astype(np.uint8), (W, H),
                        interpolation=cv2.INTER_NEAREST,
                    ).astype(bool)
                else:
                    new_mask = ref.mask
                if new_mask.any():
                    ys, xs = np.where(new_mask)
                    new_bbox = (
                        float(xs.min()), float(ys.min()),
                        float(xs.max()), float(ys.max()),
                    )
            result.append(
                RegionDetection(
                    label_id=orig.label_id,
                    bbox=new_bbox,
                    centroid_px=orig.centroid_px,
                    area_px=orig.area_px,
                    area_m2=orig.area_m2,
                    confidence=orig.confidence,
                    category=orig.category,
                    mean_before_rgb=orig.mean_before_rgb,
                    mean_after_rgb=orig.mean_after_rgb,
                    pixel_mask=new_mask if new_mask is not None else orig.pixel_mask,
                )
            )

        result.extend(passthrough)
        return result

    # ─── Geo / poligon ───────────────────────────────────────────────

    @staticmethod
    def _estimate_pixel_area_m2(raster_path: Path) -> float:
        """Raster'in WGS-84 hücre boyutundan piksel basina m^2 tahmini.

        Yaklasik: enlemde latitude-baga ı bir cosinus duzeltmesi ile.
        """
        try:
            with rasterio.open(raster_path) as src:
                a = src.transform.a   # x-çözünürlüğü (derece)
                e = -src.transform.e  # y-çözünürlüğü (derece)
                lat = (src.bounds.top + src.bounds.bottom) / 2.0
                # 1 derece enlem ≈ 111_320 m. Boylam: 111_320 * cos(lat).
                lat_m = 111_320.0
                lon_m = 111_320.0 * float(np.cos(np.deg2rad(lat)))
                px_w = abs(a) * lon_m
                px_h = abs(e) * lat_m
                area = px_w * px_h
                if not np.isfinite(area) or area <= 0:
                    return DEFAULT_PIXEL_AREA_M2
                return float(area)
        except Exception as exc:
            log.warning("pixel_area_estimate_failed", exc=str(exc))
            return DEFAULT_PIXEL_AREA_M2

    def _regions_to_features(
        self, regions: List[RegionDetection], transform
    ) -> List[dict]:
        import rasterio.transform as rt

        features: List[dict] = []
        for r in regions:
            poly = self._region_to_polygon(r, transform)
            if poly is None or poly.is_empty:
                continue

            # Centroid WGS-84
            cx_px, cy_px = r.centroid_px
            cx_lon, cy_lat = rt.xy(transform, cy_px, cx_px)

            # Gercek alan (m^2) - geodesik
            try:
                lon_arr = [c[0] for c in poly.exterior.coords]
                lat_arr = [c[1] for c in poly.exterior.coords]
                geo_area_m2 = abs(_GEOD.polygon_area_perimeter(lon_arr, lat_arr)[0])
            except Exception:
                geo_area_m2 = r.area_m2

            features.append({
                "type": "Feature",
                "geometry": mapping(poly),
                "properties": {
                    "category": r.category,
                    "confidence": r.confidence,
                    "areaM2": float(geo_area_m2),
                    "areaPx": int(r.area_px),
                    "centroid": [float(cx_lon), float(cy_lat)],
                    "bbox": list(r.bbox),
                    "labelId": int(r.label_id),
                },
            })
        return features

    @staticmethod
    def _region_to_polygon(r: RegionDetection, transform) -> Polygon | None:
        import rasterio.transform as rt

        if r.pixel_mask is not None and r.pixel_mask.any():
            m = (r.pixel_mask.astype(np.uint8)) * 255
            contours, _ = cv2.findContours(
                m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if contours:
                cnt = max(contours, key=cv2.contourArea)
                if cv2.contourArea(cnt) >= 20:
                    eps = 0.005 * cv2.arcLength(cnt, closed=True)
                    cnt = cv2.approxPolyDP(cnt, eps, closed=True)
                    coords = cnt.reshape(-1, 2)
                    if len(coords) >= 3:
                        geo_coords = [
                            rt.xy(transform, py, px) for px, py in coords
                        ]
                        poly = Polygon(geo_coords)
                        if not poly.is_valid:
                            poly = poly.buffer(0)
                        if poly.is_valid and not poly.is_empty and hasattr(poly, "exterior"):
                            return poly

        # Fallback — bbox dortgeni
        x1, y1, x2, y2 = r.bbox
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        geo_corners = [rt.xy(transform, py, px) for px, py in corners]
        return Polygon(geo_corners)

    # ─── Metrikler ────────────────────────────────────────────────────

    @staticmethod
    def _compute_metrics(
        features: List[dict],
        regions: List[RegionDetection],
        diff_img: np.ndarray,
        img_shape: Tuple[int, int],
        pixel_area_m2: float,
    ) -> Dict[str, Any]:
        H, W = img_shape
        total_area_m2 = float(H * W * pixel_area_m2)

        per_cat: Dict[str, Dict[str, float]] = {}
        total_changed = 0.0
        for f in features:
            cat = f["properties"]["category"]
            area = float(f["properties"]["areaM2"])
            entry = per_cat.setdefault(cat, {"count": 0, "area_m2": 0.0})
            entry["count"] += 1
            entry["area_m2"] += area
            total_changed += area

        avg_conf = (
            float(np.mean([f["properties"]["confidence"] for f in features]))
            if features else 0.0
        )

        # Top-5 en buyuk degisim (full GeoJSON Feature)
        top5 = sorted(
            features, key=lambda f: f["properties"]["areaM2"], reverse=True
        )[:5]
        top5_collection = {
            "type": "FeatureCollection",
            "features": top5,
        }

        histogram = pixel_diff_histogram(diff_img, bins=10)

        change_pct = (total_changed / total_area_m2 * 100.0) if total_area_m2 > 0 else 0.0

        return {
            "totalAreaM2": total_area_m2,
            "totalAreaKm2": total_area_m2 / 1_000_000.0,
            "totalChangedAreaM2": total_changed,
            "totalChangedAreaKm2": total_changed / 1_000_000.0,
            "changePercent": change_pct,
            "objectCount": len(features),
            "avgConfidence": avg_conf,
            "byCategory": {
                cat: {
                    "count": int(per_cat.get(cat, {"count": 0})["count"]),
                    "areaM2": float(per_cat.get(cat, {"area_m2": 0.0})["area_m2"]),
                }
                for cat in ("YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG")
            },
            "topRegions": top5_collection,
            "pixelDiffHistogram": histogram,
            "pixelAreaM2": pixel_area_m2,
        }
