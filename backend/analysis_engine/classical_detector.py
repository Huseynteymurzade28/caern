"""Klasik bilgisayarli gorme tabanli degisiklik tespiti.

AI modelleri (YOLO/SAM) yuklenemedigi veya runtime'da hata uretiği durumlarda
devreye girer. Pixel farki + morfoloji + kontur cikarimi ile bina/araç
büyüklügünde degisiklik bolgeleri bulur. Bu sayede pipeline her zaman elle
tutulur sonuc uretir.
"""
from __future__ import annotations

from typing import List

import cv2
import numpy as np

from ai_models.base import Detection
from common_utils.logger import get_logger

log = get_logger(__name__)

# Minimum alan (piksel). Cok kucuk gurultu bolgelerini eler.
MIN_AREA_PX = 1500
# Maksimum kontur sayisi — UI okunaklilik + SAM rafine suresi icin.
MAX_DETECTIONS = 25
# Pixel-fark esigi (0-255). Yuksek = daha az gurultu.
DIFF_THRESHOLD = 45


def detect_changes(
    before_rgb: np.ndarray,
    after_rgb: np.ndarray,
    confidence_threshold: float = 0.5,
) -> tuple[List[Detection], List[Detection]]:
    """Iki goruntu arasindaki degisiklikleri tespit eder.

    Returns:
        (before_detections, after_detections)
        - before_detections: before'da olup after'da olmayan (kayip) bolgeler
        - after_detections: after'da olup before'da olmayan (yeni) bolgeler
    """
    log.info("classical_detector_start", before_shape=before_rgb.shape, after_shape=after_rgb.shape)

    # Boyutlari esitle
    h = min(before_rgb.shape[0], after_rgb.shape[0])
    w = min(before_rgb.shape[1], after_rgb.shape[1])
    before = cv2.resize(before_rgb, (w, h))
    after = cv2.resize(after_rgb, (w, h))

    # Griye cevir + isiklandirma esitleme
    g_before = cv2.cvtColor(before, cv2.COLOR_RGB2GRAY)
    g_after = cv2.cvtColor(after, cv2.COLOR_RGB2GRAY)
    g_before = cv2.equalizeHist(g_before)
    g_after = cv2.equalizeHist(g_after)

    # Mutlak fark
    diff = cv2.absdiff(g_before, g_after)

    # Gurultu azaltma + esikleme
    diff = cv2.GaussianBlur(diff, (7, 7), 0)
    _, mask = cv2.threshold(diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    # Morfoloji: kucuk lekeleri birlestir, gurultuyu sil
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Hangi tarafta degisim var: before mu, after mi daha parlak/koyu?
    # before > after ise "kayip" (yikilan/kaldirilmis); after > before ise "yeni"
    lost_mask = ((g_before.astype(np.int16) - g_after.astype(np.int16)) > DIFF_THRESHOLD).astype(np.uint8) * 255
    new_mask = ((g_after.astype(np.int16) - g_before.astype(np.int16)) > DIFF_THRESHOLD).astype(np.uint8) * 255
    lost_mask = cv2.bitwise_and(lost_mask, mask)
    new_mask = cv2.bitwise_and(new_mask, mask)

    before_dets = _mask_to_detections(lost_mask, diff, label="bina", side="before")
    after_dets = _mask_to_detections(new_mask, diff, label="bina", side="after")

    log.info(
        "classical_detector_done",
        lost=len(before_dets),
        new=len(after_dets),
    )
    return before_dets, after_dets


def _mask_to_detections(
    mask: np.ndarray, diff: np.ndarray, label: str, side: str
) -> List[Detection]:
    """Maskeden kontur cikarip Detection listesine cevirir."""
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # En buyukten kuçuğe sirala (en belirgin degisiklikler oncelikli)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    detections: List[Detection] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA_PX:
            continue

        x, y, w, h = cv2.boundingRect(cnt)

        # Sinif tahmini: en-boy ve buyukluge gore basit heuristik
        aspect = w / max(h, 1)
        if area > 8000:
            cls_name = "bina"
            cls_id = 0
        elif aspect > 2.0 or aspect < 0.5:
            cls_name = "araç"
            cls_id = 1
        elif area < 1500:
            cls_name = "ağaç"
            cls_id = 2
        else:
            cls_name = "tarım_alanı"
            cls_id = 3

        # Confidence: bolgedeki ortalama fark yogunluguna bagli (0.5-0.95 arasi)
        region_diff = diff[y : y + h, x : x + w]
        intensity = float(region_diff.mean()) / 255.0
        confidence = round(min(0.95, 0.5 + intensity * 0.7), 3)

        detections.append(
            Detection(
                bbox=[float(x), float(y), float(x + w), float(y + h)],
                confidence=confidence,
                class_id=cls_id,
                class_name=cls_name,
            )
        )

        if len(detections) >= MAX_DETECTIONS:
            break

    return detections
