"""Add JP2 to imageformat enum.

Revision ID: 002
Revises: 001
Create Date: 2026-05-17
"""
from __future__ import annotations

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE imageformat ADD VALUE IF NOT EXISTS 'jp2'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # A full type recreation would be required; left as no-op for safety.
    pass
