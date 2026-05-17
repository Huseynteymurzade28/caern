"""Root API router — aggregates all endpoint modules."""
from __future__ import annotations

from fastapi import APIRouter

from api.endpoints import auth, images, jobs, reports, admin, models

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(images.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)
api_router.include_router(admin.router)
api_router.include_router(models.router)
