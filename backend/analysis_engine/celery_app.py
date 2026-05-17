"""Celery application configuration."""
from __future__ import annotations

from celery import Celery

from common_utils.config import settings

app = Celery(
    "caern",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["analysis_engine.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "analysis_engine.tasks.run_analysis": {"queue": "analysis"},
    },
    task_time_limit=settings.gpu_timeout_seconds + 60,
    task_soft_time_limit=settings.gpu_timeout_seconds,
)
