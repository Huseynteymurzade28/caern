"""AnalysisJob orchestrator: start, cancel, progress, produce results."""
from __future__ import annotations

import concurrent.futures
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import numpy as np
from shapely.geometry import Polygon, box, mapping
from shapely.ops import unary_union

from ai_models.base import Detection
from ai_models.model_registry import registry
from common_utils.config import settings
from common_utils.exceptions import GPUTimeoutError, JobCancelledError
from common_utils.logger import get_logger
from geo_processing.alignment import align_to_reference, normalize_to_wgs84
from geo_processing.image_processor import load_as_rgb
from geo_processing.metadata import validate_crs

log = get_logger(__name__)

MAX_RETRIES = 3


class JobOrchestrator:
    """Coordinates the full analysis pipeline for a single job."""

    def __init__(self, job_id: str, confidence_threshold: float = 0.5) -> None:
        self.job_id = job_id
        self.confidence_threshold = confidence_threshold
        self._cancelled = False

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
    ) -> List[dict]:
        """Full pipeline; returns list of GeoJSON Feature dicts."""
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

            _progress(10, "WGS-84'e dönüştürülüyor")
            before_wgs = normalize_to_wgs84(before_path, tmp_dir / "before_wgs.tif")
            after_wgs = normalize_to_wgs84(after_path, tmp_dir / "after_wgs.tif")
            self._check_cancelled()

            _progress(20, "Coğrafi hizalanıyor")
            after_aligned = align_to_reference(after_wgs, before_wgs, tmp_dir / "after_aligned.tif")
            self._check_cancelled()

            _progress(30, "Görüntüler yükleniyor")
            before_rgb = load_as_rgb(before_wgs)
            after_rgb = load_as_rgb(after_aligned)
            self._check_cancelled()

            _progress(40, "AI modelleri yükleniyor")
            yolo = registry.get_yolo()
            sam = registry.get_sam()
            self._check_cancelled()

            _progress(50, "YOLO ve SAM paralel çalışıyor")
            before_dets, after_dets = self._parallel_detect(
                yolo, sam, before_rgb, after_rgb
            )
            self._check_cancelled()

            _progress(75, "Maskeler birleştiriliyor")
            import rasterio
            with rasterio.open(before_wgs) as src:
                transform = src.transform

            features = self._aggregate_results(
                before_dets, after_dets, transform, before_rgb.shape[:2]
            )

            _progress(95, "Sonuçlar hazırlanıyor")
            return features

    def _parallel_detect(
        self,
        yolo,
        sam,
        before_rgb: np.ndarray,
        after_rgb: np.ndarray,
    ) -> Tuple[List[Detection], List[Detection]]:
        """Run YOLO+SAM on before and after images concurrently."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            fut_before_yolo = pool.submit(yolo.predict, before_rgb)
            fut_after_yolo = pool.submit(yolo.predict, after_rgb)
            fut_before_sam = pool.submit(sam.predict, before_rgb)
            fut_after_sam = pool.submit(sam.predict, after_rgb)

            before_yolo = fut_before_yolo.result(timeout=settings.gpu_timeout_seconds)
            after_yolo = fut_after_yolo.result(timeout=settings.gpu_timeout_seconds)
            before_sam = fut_before_sam.result(timeout=settings.gpu_timeout_seconds)
            after_sam = fut_after_sam.result(timeout=settings.gpu_timeout_seconds)

        before_dets = self._merge_detections(before_yolo, before_sam)
        after_dets = self._merge_detections(after_yolo, after_sam)
        return before_dets, after_dets

    def _merge_detections(
        self, yolo_dets: List[Detection], sam_dets: List[Detection]
    ) -> List[Detection]:
        """NMS fusion of YOLO + SAM detections."""
        combined = [d for d in yolo_dets + sam_dets if d.confidence >= self.confidence_threshold]
        return self._nms(combined, iou_threshold=0.5)

    @staticmethod
    def _nms(dets: List[Detection], iou_threshold: float = 0.5) -> List[Detection]:
        if not dets:
            return []
        dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
        kept: List[Detection] = []
        for det in dets:
            b1 = box(*det.bbox)
            dominated = any(
                b1.intersection(box(*k.bbox)).area / b1.union(box(*k.bbox)).area >= iou_threshold
                for k in kept
            )
            if not dominated:
                kept.append(det)
        return kept

    def _aggregate_results(
        self,
        before_dets: List[Detection],
        after_dets: List[Detection],
        transform,
        img_shape: Tuple[int, int],
    ) -> List[dict]:
        """Compare before/after detections and produce GeoJSON features."""
        import rasterio.transform as rt

        def det_to_polygon(d: Detection) -> Polygon:
            x1, y1, x2, y2 = d.bbox
            corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
            geo_corners = [
                rt.xy(transform, py, px) for px, py in corners
            ]
            return Polygon(geo_corners)

        before_polys = [(d, det_to_polygon(d)) for d in before_dets]
        after_polys = [(d, det_to_polygon(d)) for d in after_dets]

        features = []
        seen_after = set()

        for i, (b_det, b_poly) in enumerate(before_polys):
            matched = False
            for j, (a_det, a_poly) in enumerate(after_polys):
                iou = b_poly.intersection(a_poly).area / b_poly.union(a_poly).area
                if iou >= 0.3:
                    seen_after.add(j)
                    matched = True
                    break
            if not matched:
                # Object was in before but not after → lost
                features.append(self._make_feature(b_det, b_poly, "lost"))

        for j, (a_det, a_poly) in enumerate(after_polys):
            if j not in seen_after:
                features.append(self._make_feature(a_det, a_poly, "new"))

        return features

    @staticmethod
    def _make_feature(det: Detection, poly: Polygon, change_type: str) -> dict:
        from shapely.geometry import mapping

        return {
            "type": "Feature",
            "geometry": mapping(poly),
            "properties": {
                "classLabel": det.class_name,
                "confidence": det.confidence,
                "changeType": change_type,
                "areaM2": None,
            },
        }
