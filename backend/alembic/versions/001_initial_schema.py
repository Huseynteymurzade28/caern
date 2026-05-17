"""Initial schema with PostGIS support.

Revision ID: 001
Revises:
Create Date: 2024-01-01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(100), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.Enum("admin","analist","viewer","ai_engineer", name="userrole"), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_locked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # ai_models
    op.create_table(
        "ai_models",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("model_type", sa.Enum("yolo","sam","yolo_sam", name="modeltype"), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # geo_images
    op.create_table(
        "geo_images",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("format", sa.Enum("jpeg","png","geotiff","tiff", name="imageformat"), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("crs", sa.String(200), nullable=True),
        sa.Column("bbox_minx", sa.Float(), nullable=True),
        sa.Column("bbox_miny", sa.Float(), nullable=True),
        sa.Column("bbox_maxx", sa.Float(), nullable=True),
        sa.Column("bbox_maxy", sa.Float(), nullable=True),
        sa.Column("acquisition_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # analysis_jobs
    op.create_table(
        "analysis_jobs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("model_id", UUID(as_uuid=False), sa.ForeignKey("ai_models.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.Enum(
            "created","validating","queued","running","aggregating",
            "completed","failed","cancelled","archived", name="jobstatus"
        ), nullable=False, server_default="created"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence_threshold", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_analysis_jobs_owner_id", "analysis_jobs", ["owner_id"])
    op.create_index("ix_analysis_jobs_status", "analysis_jobs", ["status"])

    # job_inputs
    op.create_table(
        "job_inputs",
        sa.Column("job_id", UUID(as_uuid=False), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("image_id", UUID(as_uuid=False), sa.ForeignKey("geo_images.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.Enum("before","after", name="imagerole"), nullable=False),
    )

    # change_results
    op.create_table(
        "change_results",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=False), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("geom", Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("class_label", sa.Enum("bina","araç","ağaç","tarım_alanı", name="classlabel"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("area_m2", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_change_results_job_id", "change_results", ["job_id"])

    # reports
    op.create_table(
        "reports",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_id", UUID(as_uuid=False), sa.ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.Enum("pdf","csv", name="reportformat"), nullable=False),
        sa.Column("status", sa.Enum("pending","generating","completed","failed", name="reportstatus"), nullable=False, server_default="pending"),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # audit_logs
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.Enum(
            "USER_CREATED","USER_UPDATED","USER_DELETED","LOGIN_ATTEMPT",
            "LOGIN_SUCCESS","LOGIN_FAILED","LOGOUT","MODEL_UPLOADED",
            "MODEL_ACTIVATED","JOB_CREATED","JOB_CANCELLED","REPORT_GENERATED",
            "IMAGE_UPLOADED","PERMISSION_CHANGED", name="auditaction"
        ), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("reports")
    op.drop_table("change_results")
    op.drop_table("job_inputs")
    op.drop_table("analysis_jobs")
    op.drop_table("geo_images")
    op.drop_table("ai_models")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS auditaction")
    op.execute("DROP TYPE IF EXISTS reportstatus")
    op.execute("DROP TYPE IF EXISTS reportformat")
    op.execute("DROP TYPE IF EXISTS classlabel")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS imagerole")
    op.execute("DROP TYPE IF EXISTS imageformat")
    op.execute("DROP TYPE IF EXISTS modeltype")
    op.execute("DROP TYPE IF EXISTS userrole")
