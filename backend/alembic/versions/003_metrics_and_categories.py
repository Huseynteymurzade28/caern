"""Metrics columns + new ClassLabel categories.

Revision ID: 003
Revises: 002
Create Date: 2026-05-18
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # analysis_jobs: yeni metrik alanlari
    op.add_column(
        "analysis_jobs",
        sa.Column("min_area_m2", sa.Float(), nullable=False, server_default="25.0"),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("detection_mode", sa.String(50), nullable=True),
    )
    op.add_column(
        "analysis_jobs",
        sa.Column("metric_summary", JSONB(), nullable=True),
    )

    # change_results: zenginlestirilmis kolonlar
    op.add_column("change_results", sa.Column("area_px", sa.Integer(), nullable=True))
    op.add_column("change_results", sa.Column("centroid_lat", sa.Float(), nullable=True))
    op.add_column("change_results", sa.Column("centroid_lon", sa.Float(), nullable=True))
    op.add_column("change_results", sa.Column("bbox_minx", sa.Float(), nullable=True))
    op.add_column("change_results", sa.Column("bbox_miny", sa.Float(), nullable=True))
    op.add_column("change_results", sa.Column("bbox_maxx", sa.Float(), nullable=True))
    op.add_column("change_results", sa.Column("bbox_maxy", sa.Float(), nullable=True))

    # classlabel enum'a yeni degerler ekle
    for value in ("YENI_YAPI", "YIKIM", "VEJETASYON", "YUZEY_DEG"):
        op.execute(f"ALTER TYPE classlabel ADD VALUE IF NOT EXISTS '{value}'")


def downgrade() -> None:
    op.drop_column("change_results", "bbox_maxy")
    op.drop_column("change_results", "bbox_maxx")
    op.drop_column("change_results", "bbox_miny")
    op.drop_column("change_results", "bbox_minx")
    op.drop_column("change_results", "centroid_lon")
    op.drop_column("change_results", "centroid_lat")
    op.drop_column("change_results", "area_px")
    op.drop_column("analysis_jobs", "metric_summary")
    op.drop_column("analysis_jobs", "detection_mode")
    op.drop_column("analysis_jobs", "min_area_m2")
    # Enum'a eklenen degerleri downgrade etmek icin PG'de tablo+enum recreate
    # gerektigi icin no-op birakiyoruz.
