"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    app_env: str = "development"
    app_debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    max_upload_size_mb: int = 500

    # PostgreSQL
    postgres_user: str = "caern"
    postgres_password: str = "caern_secret"
    postgres_db: str = "caern_db"
    postgres_host: str = "postgres"
    postgres_port: int = 5432

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_root_user: str = "caern_minio"
    minio_root_password: str = "caern_minio_secret"
    minio_bucket: str = "caern-images"
    minio_use_ssl: bool = False

    # JWT
    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_hours: int = 8
    jwt_refresh_token_expire_days: int = 7

    # Security
    max_login_attempts: int = 5
    lockout_minutes: int = 15

    # AI
    yolo_model_path: str = "/app/models/yolov8n.pt"
    sam_model_path: str = "/app/models/sam_vit_h.pth"
    model_confidence_threshold: float = 0.5
    gpu_timeout_seconds: int = 180

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "CAERN Platform <noreply@example.com>"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
