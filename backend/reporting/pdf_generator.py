"""PDF report generation using WeasyPrint.

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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jinja2 import DictLoader, Environment

from common_utils.exceptions import ReportGenerationError
from common_utils.logger import get_logger

log = get_logger(__name__)


_TEMPLATE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<style>
  @page { size: A4; margin: 22mm 18mm; }
  body { font-family: 'DejaVu Sans', Arial, sans-serif; color: #1a2236; font-size: 11pt; }
  h1 { color: #0a3d62; font-size: 22pt; margin: 0; }
  h2 { color: #0a3d62; font-size: 14pt; border-bottom: 2px solid #0a3d62;
       padding-bottom: 4px; margin-top: 28px; }
  h3 { color: #1a4d7a; font-size: 12pt; margin-top: 16px; }
  .cover { page-break-after: always; padding-top: 80px; }
  .cover .subtitle { color: #4a6181; font-size: 13pt; margin-top: 8px; }
  .cover .meta { margin-top: 60px; line-height: 1.9; }
  .cover .meta strong { display: inline-block; min-width: 200px; color: #0a3d62; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 4px;
           font-size: 9pt; font-weight: bold; }
  .badge-yeni { background: #d1fae5; color: #065f46; }
  .badge-yikim { background: #fee2e2; color: #991b1b; }
  .badge-veje { background: #fef3c7; color: #92400e; }
  .badge-yuzey { background: #dbeafe; color: #1e40af; }

  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th { background: #0a3d62; color: white; padding: 8px 10px; text-align: left;
       font-size: 10pt; }
  td { border: 1px solid #d4dbe6; padding: 7px 10px; font-size: 10pt; }
  tr:nth-child(even) { background: #f4f7fb; }

  .metric-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
                 margin-top: 12px; }
  .metric { border: 1px solid #d4dbe6; border-radius: 6px; padding: 12px 14px;
            background: #f9fbfd; }
  .metric .label { font-size: 9pt; color: #4a6181; text-transform: uppercase;
                   letter-spacing: 0.5px; }
  .metric .value { font-size: 16pt; color: #0a3d62; font-weight: bold;
                   margin-top: 4px; }
  .metric .unit { font-size: 10pt; color: #4a6181; margin-left: 4px; }

  .map-img { width: 100%; max-height: 380px; object-fit: contain;
             border: 1px solid #d4dbe6; border-radius: 6px; }
  .footer { font-size: 8pt; color: #7a8aa0; margin-top: 30px;
            text-align: center; border-top: 1px solid #e0e6ee; padding-top: 8px; }
</style>
</head>
<body>

<!-- KAPAK -->
<div class="cover">
  <h1>CAERN</h1>
  <div class="subtitle">Coğrafi Değişim Tespiti — Analiz Raporu</div>

  <div class="meta">
    <p><strong>Analiz ID:</strong> {{ job_id }}</p>
    <p><strong>Oluşturulma Tarihi:</strong> {{ generated_at }}</p>
    <p><strong>Hazırlayan:</strong> {{ user_email }}</p>
    <p><strong>Tespit Modeli:</strong> {{ detection_mode }}</p>
    <p><strong>Güven Eşiği:</strong> {{ "%.0f"|format(confidence_threshold * 100) }}%</p>
    <p><strong>Min. Alan Eşiği:</strong> {{ min_area_m2 }} m²</p>
    <p><strong>Toplam Tespit:</strong> {{ total }} nesne</p>
  </div>

  <div class="footer">
    Bu rapor CAERN platformu tarafından otomatik üretilmiştir.
  </div>
</div>

<!-- YONETICI OZETI -->
<h2>1. Yönetici Özeti</h2>
<p>
  Söz konusu analiz, iki ayrı zaman noktasında alınmış görüntülerin karşılaştırılması
  ile gerçekleştirilmiştir. Toplam <strong>{{ total }} adet</strong> değişim bölgesi
  tespit edilmiş olup, toplam değişim alanı
  <strong>{{ "%.0f"|format(metrics.totalChangedAreaM2 or 0) }} m²</strong>
  ({{ "%.4f"|format(metrics.totalChangedAreaKm2 or 0) }} km²)
  şeklindedir. Bu, kapsanan toplam alanın yaklaşık
  <strong>%{{ "%.2f"|format(metrics.changePercent or 0) }}</strong>'ine karşılık gelir.
</p>

<h3>Kategori Dağılımı</h3>
<table>
  <thead>
    <tr><th>Kategori</th><th>Nesne Sayısı</th><th>Toplam Alan (m²)</th><th>Yüzde</th></tr>
  </thead>
  <tbody>
  {% for cat, info in cat_rows %}
    <tr>
      <td><span class="badge badge-{{ cat_class[cat] }}">{{ cat }}</span></td>
      <td>{{ info.count }}</td>
      <td>{{ "%.1f"|format(info.areaM2) }}</td>
      <td>{{ "%.2f"|format((info.areaM2 / (metrics.totalChangedAreaM2 or 1)) * 100) }}%</td>
    </tr>
  {% endfor %}
  </tbody>
</table>

<!-- METRIK -->
<h2>2. Metrik Tablosu</h2>
<div class="metric-grid">
  <div class="metric">
    <div class="label">Toplam Alan</div>
    <div class="value">{{ "%.4f"|format(metrics.totalAreaKm2 or 0) }}<span class="unit">km²</span></div>
  </div>
  <div class="metric">
    <div class="label">Değişen Alan</div>
    <div class="value">{{ "%.0f"|format(metrics.totalChangedAreaM2 or 0) }}<span class="unit">m²</span></div>
  </div>
  <div class="metric">
    <div class="label">Değişim Oranı</div>
    <div class="value">%{{ "%.2f"|format(metrics.changePercent or 0) }}</div>
  </div>
  <div class="metric">
    <div class="label">Ortalama Güven</div>
    <div class="value">%{{ "%.1f"|format((metrics.avgConfidence or 0) * 100) }}</div>
  </div>
  <div class="metric">
    <div class="label">Nesne Sayısı</div>
    <div class="value">{{ metrics.objectCount or 0 }}</div>
  </div>
  <div class="metric">
    <div class="label">Piksel Çözünürlüğü</div>
    <div class="value">{{ "%.3f"|format(metrics.pixelAreaM2 or 0) }}<span class="unit">m²/px</span></div>
  </div>
</div>

{% if map_image_b64 %}
<h2>3. Değişim Haritası</h2>
<img class="map-img" src="data:image/png;base64,{{ map_image_b64 }}" />
{% endif %}

<!-- NESNE LISTESI -->
<h2>{{ "4" if map_image_b64 else "3" }}. Tespit Edilen Değişim Nesneleri</h2>
<table>
  <thead>
    <tr>
      <th>#</th><th>Kategori</th><th>Alan (m²)</th>
      <th>Güven</th><th>Merkez (lat, lon)</th>
    </tr>
  </thead>
  <tbody>
  {% for r in results[:80] %}
    <tr>
      <td>{{ loop.index }}</td>
      <td><span class="badge badge-{{ cat_class.get(r.change_type, 'yuzey') }}">{{ r.change_type }}</span></td>
      <td>{{ "%.1f"|format(r.area_m2 or 0) }}</td>
      <td>%{{ "%.1f"|format(r.confidence * 100) }}</td>
      <td>
        {%- if r.centroid_lat is not none -%}
          {{ "%.5f"|format(r.centroid_lat) }}, {{ "%.5f"|format(r.centroid_lon) }}
        {%- else -%}—{%- endif -%}
      </td>
    </tr>
  {% endfor %}
  </tbody>
</table>
{% if results|length > 80 %}
<p style="font-size: 9pt; color: #7a8aa0; margin-top: 6px;">
  Yalnızca ilk 80 nesne gösterildi. Tüm liste için CSV raporunu kullanın.
</p>
{% endif %}

<!-- METODOLOJI -->
<h2>{{ "5" if map_image_b64 else "4" }}. Metodoloji</h2>
<p>
  Analiz, iki temel aşamadan oluşur:
</p>
<ol>
  <li>
    <strong>Coğrafi Hizalama:</strong> Görüntüler önce WGS-84 koordinat sistemine
    dönüştürülür, ardından sub-piksel doğrulukta birbirine hizalanır.
  </li>
  <li>
    <strong>Değişim Tespiti:</strong> Normalized Difference Index (NDI) ile
    ışıklandırma farklarına dayanıklı bir eşikleme yapılır, morfolojik açma/kapama
    ile gürültü temizlenir ve bağlı bileşen analizi ile her değişim bölgesi
    ayrı bir nesne olarak etiketlenir.
  </li>
  <li>
    <strong>SAM Rafine:</strong> {% if detection_mode == "SAM-refined" %}
      Bu analiz SAM (Segment Anything) ile rafine edilmiş; her bbox'ın hassas
      poligon sınırı çıkarılmıştır.
    {% else %}
      SAM modeli bu çalıştırmada devre dışıydı; sonuçlar yalnızca klasik CV
      ile elde edilmiştir.
    {% endif %}
  </li>
  <li>
    <strong>Kategorize:</strong> Her bölgenin önceki ve sonraki RGB ortalamaları
    karşılaştırılarak YENI_YAPI / YIKIM / VEJETASYON / YUZEY_DEG sınıflarına
    atanır.
  </li>
</ol>

<p><strong>Parametreler:</strong></p>
<table>
  <tr><td>Güven Eşiği</td><td>{{ "%.2f"|format(confidence_threshold) }}</td></tr>
  <tr><td>Min. Alan Eşiği</td><td>{{ min_area_m2 }} m²</td></tr>
  <tr><td>Tespit Modu</td><td>{{ detection_mode }}</td></tr>
</table>

</body>
</html>
"""


_CAT_CLASS = {
    "YENI_YAPI": "yeni",
    "YIKIM": "yikim",
    "VEJETASYON": "veje",
    "YUZEY_DEG": "yuzey",
}


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
    """Render analysis results to PDF bytes."""
    try:
        from weasyprint import HTML

        metrics = metrics or {}

        # Kategori siralamasi
        cats = ("YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG")
        by_cat = (metrics.get("byCategory") or {})
        cat_rows = [
            (c, by_cat.get(c, {"count": 0, "areaM2": 0.0})) for c in cats
        ]

        env = Environment(loader=DictLoader({"report.html": _TEMPLATE}))
        tmpl = env.get_template("report.html")
        html_str = tmpl.render(
            job_id=job_id,
            generated_at=datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
            total=len(results),
            results=results,
            metrics=metrics,
            cat_rows=cat_rows,
            cat_class=_CAT_CLASS,
            user_email=user_email,
            detection_mode=detection_mode,
            confidence_threshold=confidence_threshold,
            min_area_m2=min_area_m2,
            map_image_b64=map_image_b64,
        )
        pdf_bytes = HTML(string=html_str).write_pdf()
        log.info("pdf_generated", job_id=job_id, size=len(pdf_bytes))
        return pdf_bytes
    except Exception as exc:
        raise ReportGenerationError(f"PDF üretimi başarısız: {exc}") from exc


def encode_image_b64(image_bytes: bytes) -> str:
    """Convenience: bytes → base64 string for embedding in PDF."""
    return base64.b64encode(image_bytes).decode("ascii")
