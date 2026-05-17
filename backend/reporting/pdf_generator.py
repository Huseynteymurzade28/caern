"""PDF report generation using WeasyPrint (Façade Pattern)."""
from __future__ import annotations

import io
from datetime import datetime, timezone
from pathlib import Path
from typing import List

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
  body { font-family: Arial, sans-serif; margin: 30px; color: #222; }
  h1 { color: #1a56db; }
  table { width: 100%; border-collapse: collapse; margin-top: 20px; }
  th { background: #1a56db; color: white; padding: 8px 12px; text-align: left; }
  td { border: 1px solid #ddd; padding: 8px 12px; }
  tr:nth-child(even) { background: #f5f5f5; }
  .meta { color: #555; margin-bottom: 20px; }
  .new { color: #16a34a; font-weight: bold; }
  .lost { color: #dc2626; font-weight: bold; }
</style>
</head>
<body>
<h1>CAERN — Değişim Analiz Raporu</h1>
<div class="meta">
  <p><strong>Job ID:</strong> {{ job_id }}</p>
  <p><strong>Oluşturulma:</strong> {{ generated_at }}</p>
  <p><strong>Toplam Tespit:</strong> {{ total }} adet</p>
</div>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Sınıf</th>
      <th>Değişim Türü</th>
      <th>Güven</th>
      <th>Alan (m²)</th>
    </tr>
  </thead>
  <tbody>
  {% for r in results %}
    <tr>
      <td>{{ loop.index }}</td>
      <td>{{ r.class_label }}</td>
      <td class="{{ r.change_type }}">{{ r.change_type }}</td>
      <td>{{ "%.2f"|format(r.confidence * 100) }}%</td>
      <td>{{ "%.1f"|format(r.area_m2 or 0) }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>
</body>
</html>
"""


def generate_pdf(job_id: str, results: List) -> bytes:
    """Render analysis results to PDF bytes."""
    try:
        from weasyprint import HTML

        env = Environment(loader=DictLoader({"report.html": _TEMPLATE}))
        tmpl = env.get_template("report.html")
        html_str = tmpl.render(
            job_id=job_id,
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            total=len(results),
            results=results,
        )
        pdf_bytes = HTML(string=html_str).write_pdf()
        log.info("pdf_generated", job_id=job_id, size=len(pdf_bytes))
        return pdf_bytes
    except Exception as exc:
        raise ReportGenerationError(f"PDF üretimi başarısız: {exc}") from exc
