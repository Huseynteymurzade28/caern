"""AnalysisJob orchestrator: start, cancel, progress, produce results.

Detection stratejisi:
1. Klasik CV (pixel fark + morfoloji) ile degisim bolgelerini bul (hizli).
2. SAM (varsa) her bolgeyi gercek nesne sinirina rafine eder; mask -> polygon.
3. SAM basarisizsa axis-aligned bbox poligonu kullanilir.

Bu sayede SAM gercekten ise yariyor (bbox -> hassas poligon) ve GPU yoksa bile
classical-CV her zaman elle tutulur sonuc uretir.
"""
from __future__ import annotations

import concurrent.futures
import tempfile
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
from shapely.geometry import Polygon, box

from ai_models.base import Detection
from ai_models.model_registry import registry
from analysis_engine.classical_detector import detect_changes as classical_detect
from common_utils.config import settings
from common_utils.exceptions import JobCancelledError
from common_utils.logger import get_logger
from geo_processing.alignment import align_to_reference, normalize_to_wgs84
from geo_processing.image_processor import load_as_rgb
from geo_processing.metadata import validate_crs

log = get_logger(__name__)

MAX_RETRIES = 3
# SAM CPU'da yavas; rafineye giren bbox sayisini sinirla.
MAX_SAM_REFINE = 15
# SAM encoder full-res goruntuyu CPU'da kodlamak dakikalarca surer.
# Bu uzun kenari asma — kalitesini cok bozmaz, suresi 10x azalir.
SAM_MAX_SIDE = 1024
# Her goruntu icin SAM islemine ayrilan maksimum sure (sn).
SAM_TIMEOUT_SECONDS = 60


class JobOrchestrator:
    """Coordinates the full analysis pipeline for a single job."""

    def __init__(self, job_id: str, confidence_threshold: float = 0.5) -> None:
        self.job_id = job_id
        self.confidence_threshold = confidence_threshold
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

            _progress(15, "WGS-84'e dönüştürülüyor")
            before_wgs = normalize_to_wgs84(before_path, tmp_dir / "before_wgs.tif")
            after_wgs = normalize_to_wgs84(after_path, tmp_dir / "after_wgs.tif")
            self._check_cancelled()

            _progress(25, "Coğrafi hizalanıyor")
            after_aligned = align_to_reference(after_wgs, before_wgs, tmp_dir / "after_aligned.tif")
            self._check_cancelled()

            _progress(35, "Görüntüler yükleniyor")
            before_rgb = load_as_rgb(before_wgs)
            after_rgb = load_as_rgb(after_aligned)
            self._check_cancelled()

            _progress(45, "Değişim bölgeleri tespit ediliyor")
            before_dets, after_dets = classical_detect(
                before_rgb, after_rgb, self.confidence_threshold
            )
            self._check_cancelled()

            _progress(60, "SAM modeli yükleniyor")
            sam = self._try_load_sam()
            self._check_cancelled()

            if sam is not None and (before_dets or after_dets):
                _progress(70, f"SAM ile {len(before_dets) + len(after_dets)} bölge rafine ediliyor")
                try:
                    before_dets = self._refine_with_sam(sam, before_rgb, before_dets)
                    after_dets = self._refine_with_sam(sam, after_rgb, after_dets)
                    self._detection_mode = "SAM-refined"
                except Exception as exc:
                    log.warning("sam_refine_failed", job_id=self.job_id, exc=str(exc))
                    self._detection_mode = "classical-CV"
            else:
                self._detection_mode = "classical-CV"

            _progress(85, "Coğrafi koordinatlar hesaplanıyor")
            import rasterio
            with rasterio.open(before_wgs) as src:
                transform = src.transform

            features = self._aggregate_results(
                before_dets, after_dets, transform, before_rgb.shape[:2]
            )

            _progress(
                95,
                f"Sonuçlar hazırlanıyor (mod: {self._detection_mode}, {len(features)} değişiklik)",
            )
            return features

    def _try_load_sam(self):
        """SAM yuklemeye calis; basarisizsa None dondur."""
        try:
            sam = registry.get_sam()
            log.info("sam_ready", job_id=self.job_id)
            return sam
        except Exception as exc:
            log.warning("sam_load_failed", job_id=self.job_id, exc=str(exc))
            return None

    def _refine_with_sam(
        self, sam, image: np.ndarray, detections: List[Detection]
    ) -> List[Detection]:
        """SAM ile her bbox'i hassas maskeye cevirir.

        Performans: goruntuyu SAM_MAX_SIDE'a downsample eder (CPU encoder hizi
        ~10x artar), bbox'lari olceklendirir, sonra mask'i orijinal boyuta
        geri buyutur. Tum islem SAM_TIMEOUT_SECONDS ile sinirli — asarsa
        orijinal bbox'lar mask'siz dondurulur.
        """
        if not detections:
            return detections

        # En guvenilir N taneyi rafine et, kalani aynen birak.
        to_refine = detections[:MAX_SAM_REFINE]
        passthrough = detections[MAX_SAM_REFINE:]

        H, W = image.shape[:2]
        max_side = max(H, W)
        if max_side > SAM_MAX_SIDE:
            scale = SAM_MAX_SIDE / max_side
            new_w, new_h = int(round(W * scale)), int(round(H * scale))
            small = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            scale = 1.0
            small = image

        small_boxes = [[b * scale for b in d.bbox] for d in to_refine]

        def _do_predict():
            return sam.predict_with_boxes(small, small_boxes)

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                refined = pool.submit(_do_predict).result(timeout=SAM_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            log.warning(
                "sam_timeout", job_id=self.job_id, timeout=SAM_TIMEOUT_SECONDS,
                refine_count=len(to_refine),
            )
            return detections  # Hepsi mask'siz dondu — bbox poligonu kullanilacak

        result: List[Detection] = []
        for orig, ref in zip(to_refine, refined):
            mask_full = None
            new_bbox = orig.bbox

            if ref.mask is not None and ref.mask.any():
                if scale < 1.0:
                    mask_full = cv2.resize(
                        ref.mask.astype(np.uint8), (W, H),
                        interpolation=cv2.INTER_NEAREST,
                    ).astype(bool)
                else:
                    mask_full = ref.mask

                if mask_full.any():
                    ys, xs = np.where(mask_full)
                    new_bbox = [
                        float(xs.min()), float(ys.min()),
                        float(xs.max()), float(ys.max()),
                    ]

            result.append(
                Detection(
                    bbox=new_bbox,
                    confidence=orig.confidence,
                    class_id=orig.class_id,
                    class_name=orig.class_name,
                    mask=mask_full,
                )
            )

        result.extend(passthrough)
        return result

    def _aggregate_results(
        self,
        before_dets: List[Detection],
        after_dets: List[Detection],
        transform,
        img_shape: Tuple[int, int],
    ) -> List[dict]:
        """Compare before/after detections and produce GeoJSON features."""
        before_polys = [(d, self._det_to_polygon(d, transform)) for d in before_dets]
        after_polys = [(d, self._det_to_polygon(d, transform)) for d in after_dets]

        features: list[dict] = []
        seen_after: set[int] = set()

        for b_det, b_poly in before_polys:
            matched = False
            for j, (a_det, a_poly) in enumerate(after_polys):
                if j in seen_after:
                    continue
                inter = b_poly.intersection(a_poly).area
                union = b_poly.union(a_poly).area
                iou = inter / union if union > 0 else 0
                if iou >= 0.3:
                    seen_after.add(j)
                    matched = True
                    break
            if not matched:
                features.append(self._make_feature(b_det, b_poly, "lost"))

        for j, (a_det, a_poly) in enumerate(after_polys):
            if j not in seen_after:
                features.append(self._make_feature(a_det, a_poly, "new"))

        return features

    @staticmethod
    def _det_to_polygon(d: Detection, transform) -> Polygon:
        """Detection -> WGS-84 cografi Polygon.

        Mask varsa contour cikarip cografi koordinatlara cevirir (gerçek sekil).
        Yoksa bbox dikdortgeni kullanir.
        """
        import rasterio.transform as rt

        if d.mask is not None and d.mask.any():
            poly = JobOrchestrator._mask_to_polygon(d.mask)
            if poly is not None and not poly.is_empty:
                geo_coords = [rt.xy(transform, py, px) for px, py in poly.exterior.coords]
                geo_poly = Polygon(geo_coords)
                if geo_poly.is_valid and geo_poly.area > 0:
                    return geo_poly

        x1, y1, x2, y2 = d.bbox
        corners = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
        geo_corners = [rt.xy(transform, py, px) for px, py in corners]
        return Polygon(geo_corners)

    @staticmethod
    def _mask_to_polygon(mask: np.ndarray) -> Polygon | None:
        """Binary mask -> sadelestirilmis Polygon (en buyuk kontur)."""
        from shapely.geometry import MultiPolygon

        m = mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        cnt = max(contours, key=cv2.contourArea)
        if cv2.contourArea(cnt) < 20:
            return None

        # Douglas-Peucker basitlestirme; cok kose olusmasin
        eps = 0.005 * cv2.arcLength(cnt, closed=True)
        cnt = cv2.approxPolyDP(cnt, eps, closed=True)

        coords = cnt.reshape(-1, 2)
        if len(coords) < 3:
            return None

        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)

        # buffer(0) MultiPolygon uretebilir; en buyuk parcayi al
        if isinstance(poly, MultiPolygon):
            poly = max(poly.geoms, key=lambda g: g.area)

        return poly if poly.is_valid and not poly.is_empty and hasattr(poly, "exterior") else None

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
