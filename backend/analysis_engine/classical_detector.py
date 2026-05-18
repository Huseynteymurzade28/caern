"""Klasik bilgisayarli gorme tabanli degisiklik tespiti.

İki ortorektifiye edilmiş RGB görüntü arasındaki değişim bölgelerini bulur ve
her bölgeyi otomatik olarak kategorize eder:

  * YENI_YAPI  — önceden düşük, sonradan yüksek yansıma (yapılaşma)
  * YIKIM      — önceden yüksek, sonradan düşük yansıma (yıkım/temizleme)
  * VEJETASYON — yeşil kanal hâkim değişim
  * YUZEY_DEG  — diğer tüm yüzey değişimleri

Yöntem:
  1. Normalized Difference Index — |after - before| / (after + before + ε)
     → ışıklandırma farklarına karşı dayanıklı eşikleme
  2. Morfoloji (erosion + dilation) — tek piksel gürültüsünü temizler
  3. scipy.ndimage.label ile bağlı bileşen analizi → her değişim bölgesi
     ayrı bir nesne olarak etiketlenir
  4. Minimum alan eşiği uygulanır (varsayılan 25 m²)
  5. Her bölgenin ortalama RGB değerleri kullanılarak otomatik kategori
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import cv2
import numpy as np
from scipy import ndimage as sndi

from common_utils.logger import get_logger

log = get_logger(__name__)


# Varsayilan parametreler — orchestrator override edebilir
DEFAULT_NDI_THRESHOLD = 0.18          # 0..1 araliginda, daha yuksek = daha az tespit
DEFAULT_MIN_AREA_M2 = 25.0            # m^2 (px^2'ye orchestrator'da cevrilir)
MAX_DETECTIONS = 200                   # gorsellik icin ust limit
DEFAULT_MORPH_KERNEL = 5               # piksel
DEFAULT_PIXEL_AREA_M2 = 0.25 * 0.25    # 0.25 m GSD varsayilan (= 0.0625 m^2/px)


@dataclass
class RegionDetection:
    """Tespit edilen tek bir degisim bolgesi."""
    label_id: int
    bbox: Tuple[float, float, float, float]   # x1, y1, x2, y2 (piksel)
    centroid_px: Tuple[float, float]          # (cx, cy) piksel
    area_px: int
    area_m2: float
    confidence: float                          # 0..1
    category: str                              # YENI_YAPI / YIKIM / VEJETASYON / YUZEY_DEG
    mean_before_rgb: Tuple[float, float, float]
    mean_after_rgb: Tuple[float, float, float]
    pixel_mask: np.ndarray | None = None       # bool, full-size


def detect_changes(
    before_rgb: np.ndarray,
    after_rgb: np.ndarray,
    *,
    ndi_threshold: float = DEFAULT_NDI_THRESHOLD,
    min_area_m2: float = DEFAULT_MIN_AREA_M2,
    pixel_area_m2: float = DEFAULT_PIXEL_AREA_M2,
    morph_kernel: int = DEFAULT_MORPH_KERNEL,
) -> Tuple[List[RegionDetection], np.ndarray]:
    """Iki goruntu arasinda degisim bolgelerini bulup kategorize eder.

    Returns:
        (regions, diff_uint8)
        - regions: List[RegionDetection]
        - diff_uint8: piksel fark gorseli (0..255, gri) — histogram icin
    """
    log.info(
        "classical_detector_start",
        before_shape=before_rgb.shape,
        after_shape=after_rgb.shape,
        ndi_threshold=ndi_threshold,
        min_area_m2=min_area_m2,
    )

    # Boyutlari hizala
    H = min(before_rgb.shape[0], after_rgb.shape[0])
    W = min(before_rgb.shape[1], after_rgb.shape[1])
    before = cv2.resize(before_rgb, (W, H))
    after = cv2.resize(after_rgb, (W, H))

    # Griye + isiklandirma normalizasyonu
    g_before = cv2.cvtColor(before, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g_after = cv2.cvtColor(after, cv2.COLOR_RGB2GRAY).astype(np.float32)

    # NDI = |after - before| / (after + before + eps)
    eps = 1e-3
    ndi = np.abs(g_after - g_before) / (g_after + g_before + eps)

    # Klasik mutlak fark (0..255) — histogram icin
    diff_uint8 = cv2.absdiff(
        cv2.cvtColor(before, cv2.COLOR_RGB2GRAY),
        cv2.cvtColor(after, cv2.COLOR_RGB2GRAY),
    )

    # Esikleme
    mask = (ndi > ndi_threshold).astype(np.uint8) * 255

    # Morfoloji: erosion (gurultu) + dilation (delik kapat)
    k = max(3, int(morph_kernel))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # Bagli bilesen analizi (scipy)
    labels, n_components = sndi.label(mask > 0)
    log.info("connected_components", n=int(n_components))

    if n_components == 0:
        return [], diff_uint8

    # Her bilesen icin metrik + kategori
    min_area_px = max(1, int(round(min_area_m2 / max(pixel_area_m2, 1e-9))))

    regions: List[RegionDetection] = []
    component_slices = sndi.find_objects(labels)
    component_areas = sndi.sum(np.ones_like(labels), labels, index=np.arange(1, n_components + 1))

    # Buyuklugu en yuksek olanlardan basla
    order = np.argsort(-component_areas)

    for idx in order:
        label_id = int(idx) + 1
        area_px = int(component_areas[idx])
        if area_px < min_area_px:
            continue

        s = component_slices[idx]
        if s is None:
            continue
        y_slice, x_slice = s
        sub_mask = (labels[y_slice, x_slice] == label_id)
        if not sub_mask.any():
            continue

        y1, y2 = y_slice.start, y_slice.stop
        x1, x2 = x_slice.start, x_slice.stop

        # Centroid (alt-piksel)
        ys, xs = np.where(sub_mask)
        cy = float(ys.mean() + y1)
        cx = float(xs.mean() + x1)

        # Ortalama RGB (before/after) - sadece bu bilesen pikselleri
        b_sub = before[y1:y2, x1:x2][sub_mask]
        a_sub = after[y1:y2, x1:x2][sub_mask]
        mean_b = tuple(float(v) for v in b_sub.mean(axis=0))
        mean_a = tuple(float(v) for v in a_sub.mean(axis=0))

        # Guven skoru: bolgedeki ortalama NDI yogunlugu
        ndi_sub = ndi[y1:y2, x1:x2][sub_mask]
        conf_raw = float(ndi_sub.mean())
        confidence = round(min(0.99, 0.55 + conf_raw * 1.4), 3)

        category = _classify_category(mean_b, mean_a)
        area_m2 = area_px * pixel_area_m2

        full_mask = np.zeros(labels.shape, dtype=bool)
        full_mask[y1:y2, x1:x2] = sub_mask

        regions.append(
            RegionDetection(
                label_id=label_id,
                bbox=(float(x1), float(y1), float(x2), float(y2)),
                centroid_px=(cx, cy),
                area_px=area_px,
                area_m2=area_m2,
                confidence=confidence,
                category=category,
                mean_before_rgb=mean_b,
                mean_after_rgb=mean_a,
                pixel_mask=full_mask,
            )
        )

        if len(regions) >= MAX_DETECTIONS:
            break

    log.info(
        "classical_detector_done",
        regions=len(regions),
        categories={c: sum(1 for r in regions if r.category == c)
                    for c in ("YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG")},
    )
    return regions, diff_uint8


def _classify_category(
    mean_before_rgb: Tuple[float, float, float],
    mean_after_rgb: Tuple[float, float, float],
) -> str:
    """Bolge kategorisini RGB ortalamalarindan tahmin eder."""
    rb, gb, bb = mean_before_rgb
    ra, ga, ba = mean_after_rgb

    sum_b = rb + gb + bb + 1e-6
    sum_a = ra + ga + ba + 1e-6

    green_ratio_before = gb / sum_b
    green_ratio_after = ga / sum_a
    brightness_before = (rb + gb + bb) / 3.0
    brightness_after = (ra + ga + ba) / 3.0
    delta_brightness = brightness_after - brightness_before

    # Vejetasyon: sonraki gorüntüde yesil hakim VEYA yesil orani arttı
    if green_ratio_after > 0.40 or (green_ratio_after - green_ratio_before) > 0.06:
        return "VEJETASYON"

    if delta_brightness > 25:
        return "YENI_YAPI"
    if delta_brightness < -25:
        return "YIKIM"

    return "YUZEY_DEG"


def pixel_diff_histogram(diff_uint8: np.ndarray, bins: int = 10) -> List[dict]:
    """0..255 araligindaki piksel fark gorselinden histogram uretir."""
    hist, edges = np.histogram(diff_uint8.ravel(), bins=bins, range=(0, 255))
    return [
        {
            "bin": i,
            "range_min": float(edges[i]),
            "range_max": float(edges[i + 1]),
            "count": int(hist[i]),
        }
        for i in range(bins)
    ]
