"""FastAPI application entry point."""
from __future__ import annotations

import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.router import api_router
from common_utils.config import settings
from common_utils.exceptions import CaernBaseError
from common_utils.logger import configure_logging, get_logger

configure_logging()
log = get_logger(__name__)

app = FastAPI(
    title="CAERN — IS ve Görüntü İşleme Destekli Harita Analiz Aracı",
    description="Uydu/drone görüntülerinden YOLOv8 + SAM ile otomatik değişim tespiti",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    redirect_slashes=False,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(CaernBaseError)
async def caern_error_handler(request: Request, exc: CaernBaseError) -> JSONResponse:
    log.warning("domain_error", code=exc.error_code, message=exc.message, trace_id=exc.trace_id)
    return JSONResponse(status_code=exc.http_status, content=exc.to_dict())


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_error", exc=str(exc), traceback=traceback.format_exc())
    from common_utils.exceptions import CaernBaseError as _Base

    err = _Base(f"Beklenmeyen sunucu hatası: {type(exc).__name__}")
    return JSONResponse(status_code=500, content=err.to_dict())


app.include_router(api_router)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "service": "caern-api"}


@app.on_event("startup")
async def startup() -> None:
    log.info("startup", env=settings.app_env)
    from storage.minio_client import ensure_bucket_exists
    try:
        ensure_bucket_exists()
    except Exception as exc:
        log.warning("minio_init_failed", exc=str(exc))
