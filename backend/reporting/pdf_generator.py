"""PDF report generation using ReportLab (pure-Python, no system deps).

Çok bölümlü Türkçe rapor:
  1. Kapak — proje, tarih, analiz parametreleri, kullanıcı
  2. Yönetici Özeti — toplam değişim, kategori dağılımı tablosu
  3. Metrik Tablosu — tüm sayısal değerler
  4. Değişim Haritası — gömülü görüntü (varsa)
  5. Nesne Listesi — her tespit için satır
  6. Metodoloji
"""
from __future__ import annotations

import base64
import io
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from common_utils.exceptions import ReportGenerationError
from common_utils.logger import get_logger

log = get_logger(__name__)


# ── Unicode font kaydı (Türkçe karakter desteği için) ────────────────────────
# ReportLab default Helvetica'sı PDFDocEncoding kullanır ve ş/ğ/ı/İ vb.
# karakterleri kare olarak basar. DejaVu Sans bunları desteklediği için
# TTF olarak kaydedip varsayılan font olarak kullanırız.
_FONT_REGULAR = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"

_FONT_CANDIDATES = [
    ("DejaVuSans",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("DejaVuSans",
     "/usr/share/fonts/dejavu/DejaVuSans.ttf",
     "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
]

for _name, _reg, _bold in _FONT_CANDIDATES:
    if os.path.isfile(_reg) and os.path.isfile(_bold):
        try:
            pdfmetrics.registerFont(TTFont(_name, _reg))
            pdfmetrics.registerFont(TTFont(f"{_name}-Bold", _bold))
            pdfmetrics.registerFontFamily(
                _name, normal=_name, bold=f"{_name}-Bold",
                italic=_name, boldItalic=f"{_name}-Bold",
            )
            _FONT_REGULAR = _name
            _FONT_BOLD = f"{_name}-Bold"
            log.info("pdf_font_registered", name=_name, path=_reg)
            break
        except Exception as exc:
            log.warning("pdf_font_register_failed", path=_reg, exc=str(exc))
else:
    log.warning("pdf_font_fallback_helvetica", reason="DejaVu TTF not found")


_BRAND = colors.HexColor("#0a3d62")
_BRAND_LIGHT = colors.HexColor("#1a4d7a")
_MUTED = colors.HexColor("#4a6181")
_BG_ALT = colors.HexColor("#f4f7fb")
_BORDER = colors.HexColor("#d4dbe6")

_CAT_COLOR_HEX = {
    "YENI_YAPI": "#065f46",
    "YIKIM": "#991b1b",
    "VEJETASYON": "#92400e",
    "YUZEY_DEG": "#1e40af",
}
_CAT_BG_HEX = {
    "YENI_YAPI": "#d1fae5",
    "YIKIM": "#fee2e2",
    "VEJETASYON": "#fef3c7",
    "YUZEY_DEG": "#dbeafe",
}


def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], textColor=_BRAND,
            fontName=_FONT_BOLD, fontSize=26, leading=30,
            alignment=0, spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Sub", parent=base["Normal"], textColor=_MUTED,
            fontName=_FONT_REGULAR, fontSize=13, leading=18, spaceAfter=24,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], textColor=_BRAND,
            fontName=_FONT_BOLD, fontSize=15, leading=20,
            spaceBefore=18, spaceAfter=8, borderPadding=2,
        ),
        "h3": ParagraphStyle(
            "H3", parent=base["Heading3"], textColor=_BRAND_LIGHT,
            fontName=_FONT_BOLD, fontSize=12, leading=16,
            spaceBefore=10, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["Normal"], fontName=_FONT_REGULAR,
            fontSize=10.5, leading=15, spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["Normal"], fontName=_FONT_REGULAR,
            fontSize=8.5, leading=11, textColor=_MUTED,
        ),
        "meta_label": ParagraphStyle(
            "MetaL", parent=base["Normal"], fontName=_FONT_BOLD,
            fontSize=10.5, leading=18, textColor=_BRAND,
        ),
        "metric_label": ParagraphStyle(
            "ML", parent=base["Normal"], fontName=_FONT_REGULAR,
            fontSize=8.5, leading=11, textColor=_MUTED,
        ),
        "metric_value": ParagraphStyle(
            "MV", parent=base["Normal"], fontName=_FONT_BOLD,
            fontSize=15, leading=18, textColor=_BRAND,
        ),
        "cell": ParagraphStyle(
            "Cell", parent=base["Normal"], fontName=_FONT_REGULAR,
            fontSize=9, leading=12,
        ),
    }


def _fmt(x: Optional[float], spec: str = ".2f", default: str = "—") -> str:
    if x is None:
        return default
    try:
        return format(float(x), spec)
    except (TypeError, ValueError):
        return default


def _category_chip(cat: str, st: Dict[str, ParagraphStyle]) -> Paragraph:
    fg = _CAT_COLOR_HEX.get(cat, "#374151")
    bg = _CAT_BG_HEX.get(cat, "#e5e7eb")
    return Paragraph(
        f'<font color="{fg}" backColor="{bg}"><b>&nbsp;{cat}&nbsp;</b></font>',
        st["cell"],
    )


def _build_cover(
    *,
    job_id: str,
    user_email: str,
    detection_mode: str,
    confidence_threshold: float,
    min_area_m2: float,
    total: int,
    st: Dict[str, ParagraphStyle],
) -> list:
    elements = [
        Spacer(1, 30 * mm),
        Paragraph("CAERN", st["title"]),
        Paragraph("Coğrafi Değişim Tespiti — Analiz Raporu", st["subtitle"]),
        Spacer(1, 30 * mm),
    ]
    meta_rows = [
        ("Analiz ID", job_id),
        ("Oluşturulma Tarihi", datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")),
        ("Hazırlayan", user_email),
        ("Tespit Modeli", detection_mode),
        ("Güven Eşiği", f"%{confidence_threshold * 100:.0f}"),
        ("Min. Alan Eşiği", f"{min_area_m2} m²"),
        ("Toplam Tespit", f"{total} nesne"),
    ]
    table = Table(
        [[Paragraph(f"<b>{k}</b>", st["meta_label"]), Paragraph(str(v), st["body"])]
         for k, v in meta_rows],
        colWidths=[55 * mm, 110 * mm],
    )
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 40 * mm))
    elements.append(Paragraph(
        "<i>Bu rapor CAERN platformu tarafından otomatik üretilmiştir.</i>",
        st["small"],
    ))
    elements.append(PageBreak())
    return elements


def _build_summary(
    *, total: int, metrics: Dict[str, Any], cat_rows: list, st: Dict[str, ParagraphStyle]
) -> list:
    changed_m2 = metrics.get("totalChangedAreaM2") or 0
    changed_km2 = metrics.get("totalChangedAreaKm2") or (changed_m2 / 1_000_000.0)
    change_pct = metrics.get("changePercent") or 0
    elements = [
        Paragraph("1. Yönetici Özeti", st["h2"]),
        Paragraph(
            f"Söz konusu analiz, iki ayrı zaman noktasında alınmış görüntülerin "
            f"karşılaştırılması ile gerçekleştirilmiştir. Toplam "
            f"<b>{total} adet</b> değişim bölgesi tespit edilmiş olup, "
            f"toplam değişim alanı <b>{_fmt(changed_m2, '.0f')} m²</b> "
            f"({_fmt(changed_km2, '.4f')} km²) şeklindedir. Bu, kapsanan toplam alanın "
            f"yaklaşık <b>%{_fmt(change_pct, '.2f')}</b>'ine karşılık gelir.",
            st["body"],
        ),
        Paragraph("Kategori Dağılımı", st["h3"]),
    ]
    table_data = [["Kategori", "Nesne Sayısı", "Toplam Alan (m²)", "Yüzde"]]
    for cat, info in cat_rows:
        area = info.get("areaM2", 0.0)
        count = info.get("count", 0)
        pct = (area / (changed_m2 or 1)) * 100
        table_data.append([
            _category_chip(cat, st),
            str(count),
            _fmt(area, ".1f"),
            f"%{_fmt(pct, '.2f')}",
        ])
    t = Table(table_data, colWidths=[45 * mm, 30 * mm, 45 * mm, 30 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _BG_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    return elements


def _build_metrics(metrics: Dict[str, Any], st: Dict[str, ParagraphStyle]) -> list:
    cells = [
        ("Toplam Alan", _fmt(metrics.get("totalAreaKm2"), ".4f"), "km²"),
        ("Değişen Alan", _fmt(metrics.get("totalChangedAreaM2"), ".0f"), "m²"),
        ("Değişim Oranı", f"%{_fmt(metrics.get('changePercent'), '.2f')}", ""),
        ("Ortalama Güven", f"%{_fmt((metrics.get('avgConfidence') or 0) * 100, '.1f')}", ""),
        ("Nesne Sayısı", str(metrics.get("objectCount") or 0), ""),
        ("Piksel Çözünürlüğü", _fmt(metrics.get("pixelAreaM2"), ".3f"), "m²/px"),
    ]

    def _card(label: str, value: str, unit: str) -> Table:
        body = f'<font size="15" color="#0a3d62"><b>{value}</b></font>'
        if unit:
            body += f' <font size="10" color="#4a6181">{unit}</font>'
        inner = Table(
            [[Paragraph(label.upper(), st["metric_label"])],
             [Paragraph(body, st["body"])]],
            colWidths=[80 * mm],
        )
        inner.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, _BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fbfd")),
            ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        return inner

    grid_rows = []
    for i in range(0, len(cells), 2):
        left = _card(*cells[i])
        right = _card(*cells[i + 1]) if i + 1 < len(cells) else ""
        grid_rows.append([left, right])
    grid = Table(grid_rows, colWidths=[85 * mm, 85 * mm])
    grid.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return [Paragraph("2. Metrik Tablosu", st["h2"]), grid]


def _build_map(map_image_b64: Optional[str], st: Dict[str, ParagraphStyle]) -> list:
    if not map_image_b64:
        return []
    try:
        img_bytes = base64.b64decode(map_image_b64)
        img = Image(io.BytesIO(img_bytes), width=170 * mm, height=110 * mm, kind="proportional")
        return [Paragraph("3. Değişim Haritası", st["h2"]), img]
    except Exception as exc:
        log.warning("pdf_map_image_failed", exc=str(exc))
        return []


def _build_objects(results: list, has_map: bool, st: Dict[str, ParagraphStyle]) -> list:
    section = "4" if has_map else "3"
    rows = [["#", "Kategori", "Alan (m²)", "Güven", "Merkez (lat, lon)"]]
    for idx, r in enumerate(results[:80], start=1):
        cat = getattr(r, "change_type", "—")
        clat = getattr(r, "centroid_lat", None)
        clon = getattr(r, "centroid_lon", None)
        center = (
            f"{float(clat):.5f}, {float(clon):.5f}"
            if clat is not None and clon is not None else "—"
        )
        rows.append([
            str(idx),
            _category_chip(str(cat), st),
            _fmt(getattr(r, "area_m2", 0), ".1f"),
            f"%{_fmt((r.confidence or 0) * 100, '.1f')}",
            center,
        ])
    t = Table(rows, colWidths=[12 * mm, 38 * mm, 28 * mm, 22 * mm, 55 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _BRAND),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), _FONT_BOLD),
        ("FONTNAME", (0, 1), (-1, -1), _FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _BG_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements = [
        Paragraph(f"{section}. Tespit Edilen Değişim Nesneleri", st["h2"]),
        t,
    ]
    if len(results) > 80:
        elements.append(Paragraph(
            "Yalnızca ilk 80 nesne gösterildi. Tüm liste için CSV raporunu kullanın.",
            st["small"],
        ))
    return elements


def _build_methodology(
    *, detection_mode: str, confidence_threshold: float,
    min_area_m2: float, has_map: bool, st: Dict[str, ParagraphStyle],
) -> list:
    section = "5" if has_map else "4"
    sam_line = (
        "Bu analiz SAM (Segment Anything) ile rafine edilmiş; her bbox'ın hassas "
        "poligon sınırı çıkarılmıştır."
        if detection_mode == "SAM-refined"
        else "SAM modeli bu çalıştırmada devre dışıydı; sonuçlar yalnızca klasik CV ile elde edilmiştir."
    )
    steps = [
        ("Coğrafi Hizalama",
         "Görüntüler önce WGS-84 koordinat sistemine dönüştürülür, ardından "
         "sub-piksel doğrulukta birbirine hizalanır."),
        ("Değişim Tespiti",
         "Normalized Difference Index (NDI) ile ışıklandırma farklarına dayanıklı "
         "bir eşikleme yapılır, morfolojik açma/kapama ile gürültü temizlenir ve "
         "bağlı bileşen analizi ile her değişim bölgesi ayrı bir nesne olarak etiketlenir."),
        ("SAM Rafine", sam_line),
        ("Kategorize",
         "Her bölgenin önceki ve sonraki RGB ortalamaları karşılaştırılarak "
         "YENI_YAPI / YIKIM / VEJETASYON / YUZEY_DEG sınıflarına atanır."),
    ]
    elements = [Paragraph(f"{section}. Metodoloji", st["h2"])]
    for i, (title, body) in enumerate(steps, start=1):
        elements.append(Paragraph(f"<b>{i}. {title}:</b> {body}", st["body"]))

    params = Table(
        [["Güven Eşiği", _fmt(confidence_threshold, ".2f")],
         ["Min. Alan Eşiği", f"{min_area_m2} m²"],
         ["Tespit Modu", detection_mode]],
        colWidths=[60 * mm, 80 * mm],
    )
    params.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, _BORDER),
        ("BACKGROUND", (0, 0), (0, -1), _BG_ALT),
        ("FONTNAME", (0, 0), (-1, -1), _FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<b>Parametreler:</b>", st["body"]))
    elements.append(params)
    return elements


def _on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT_REGULAR, 7.5)
    canvas.setFillColor(_MUTED)
    canvas.drawRightString(
        A4[0] - 18 * mm, 10 * mm,
        f"CAERN Analiz Raporu — Sayfa {doc.page}",
    )
    canvas.drawString(18 * mm, 10 * mm, "caern.local")
    canvas.restoreState()


def generate_pdf(
    job_id: str,
    results: List,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    user_email: str = "—",
    detection_mode: str = "classical-CV",
    confidence_threshold: float = 0.5,
    min_area_m2: float = 25.0,
    map_image_b64: Optional[str] = None,
) -> bytes:
    """Render analysis results to PDF bytes using ReportLab."""
    try:
        metrics = metrics or {}
        st = _styles()

        cats = ("YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG")
        by_cat = metrics.get("byCategory") or {}
        cat_rows = [
            (c, by_cat.get(c, {"count": 0, "areaM2": 0.0})) for c in cats
        ]

        buf = io.BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=22 * mm,
            bottomMargin=18 * mm,
            title=f"CAERN Analiz Raporu — {job_id[:8]}",
            author="CAERN",
        )

        flow: list = []
        flow.extend(_build_cover(
            job_id=job_id, user_email=user_email,
            detection_mode=detection_mode,
            confidence_threshold=confidence_threshold,
            min_area_m2=min_area_m2,
            total=len(results), st=st,
        ))
        flow.extend(_build_summary(
            total=len(results), metrics=metrics,
            cat_rows=cat_rows, st=st,
        ))
        flow.extend(_build_metrics(metrics, st))
        map_block = _build_map(map_image_b64, st)
        flow.extend(map_block)
        flow.extend(_build_objects(results, has_map=bool(map_block), st=st))
        flow.extend(_build_methodology(
            detection_mode=detection_mode,
            confidence_threshold=confidence_threshold,
            min_area_m2=min_area_m2,
            has_map=bool(map_block),
            st=st,
        ))

        doc.build(flow, onFirstPage=_on_page, onLaterPages=_on_page)
        pdf_bytes = buf.getvalue()
        log.info("pdf_generated", job_id=job_id, size=len(pdf_bytes))
        return pdf_bytes
    except Exception as exc:
        log.error("pdf_generation_failed", job_id=job_id, exc=str(exc))
        raise ReportGenerationError(f"PDF üretimi başarısız: {exc}") from exc


def encode_image_b64(image_bytes: bytes) -> str:
    """Convenience: bytes → base64 string for embedding in PDF."""
    return base64.b64encode(image_bytes).decode("ascii")
