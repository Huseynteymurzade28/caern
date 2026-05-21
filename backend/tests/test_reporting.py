"""Report generation tests."""
from __future__ import annotations

from unittest.mock import MagicMock


def _make_result(cls="bina", ct="new", conf=0.9, area=500.0):
    r = MagicMock()
    r.id = "result-1"
    r.class_label = cls
    r.change_type = ct
    r.confidence = conf
    r.area_m2 = area
    r.created_at = "2024-01-01 12:00:00"
    return r


def test_csv_generation():
    from reporting.csv_generator import generate_csv

    results = [_make_result(), _make_result("araç", "lost", 0.75)]
    data = generate_csv("job-x", results)
    text = data.decode("utf-8-sig")
    assert "id" in text
    assert "bina" in text
    assert "lost" in text


def test_pdf_generation():
    from reporting.pdf_generator import generate_pdf
    results = [_make_result()]
    pdf = generate_pdf("job-y", results)
    assert pdf[:4] == b"%PDF"
