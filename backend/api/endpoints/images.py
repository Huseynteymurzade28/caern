"""Image upload and retrieval endpoints."""
from __future__ import annotations

import io
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel
from typing import Optional

from api.deps import CurrentUser, DBSession, require_permission
from common_utils.config import settings
from common_utils.exceptions import FileTooLargeError, UnsupportedFormatError
from data_access.models.audit_log import AuditAction, AuditLog
from data_access.models.geo_image import GeoImage, ImageFormat
from data_access.repositories.image_repo import ImageRepository
from geo_processing.metadata import extract_metadata
from storage.minio_client import upload_file

router = APIRouter(prefix="/images", tags=["Images"])

ALLOWED_EXTENSIONS = {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".jp2"}
FORMAT_MAP = {".tif": "geotiff", ".tiff": "geotiff", ".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".jp2": "jp2"}


class ImageResponse(BaseModel):
    id: str
    filename: str
    format: str
    size_bytes: int
    width: Optional[int]
    height: Optional[int]
    crs: Optional[str]

    class Config:
        from_attributes = True


@router.post("", response_model=ImageResponse, dependencies=[require_permission("images:write")])
async def upload_image(
    file: UploadFile = File(...),
    session: DBSession = None,
    current_user: CurrentUser = None,
):
    """Upload a geo-referenced image (JPEG/PNG/GeoTIFF, max 500 MB)."""
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFormatError(f"Desteklenmeyen format: {ext}")

    data = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise FileTooLargeError(f"Dosya boyutu sınırı: {settings.max_upload_size_mb} MB")

    import tempfile, os

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        meta = extract_metadata(tmp_path)
    finally:
        os.unlink(tmp_path)

    object_name = f"images/{current_user.id}/{uuid.uuid4()}{ext}"
    upload_file(object_name, io.BytesIO(data), len(data))

    img = GeoImage(
        filename=file.filename,
        storage_path=object_name,
        format=ImageFormat(FORMAT_MAP[ext]),
        size_bytes=len(data),
        width=meta.width,
        height=meta.height,
        crs=meta.crs,
        bbox_minx=meta.bbox[0] if meta.bbox else None,
        bbox_miny=meta.bbox[1] if meta.bbox else None,
        bbox_maxx=meta.bbox[2] if meta.bbox else None,
        bbox_maxy=meta.bbox[3] if meta.bbox else None,
        uploaded_by=current_user.id,
    )
    repo = ImageRepository(GeoImage, session)
    img = await repo.create(img)

    audit = AuditLog(
        user_id=current_user.id,
        action=AuditAction.IMAGE_UPLOADED,
        resource_type="GeoImage",
        resource_id=img.id,
    )
    session.add(audit)

    return img


@router.get("/{image_id}", response_model=ImageResponse, dependencies=[require_permission("images:read")])
async def get_image(image_id: str, session: DBSession, current_user: CurrentUser):
    """Retrieve image metadata by ID."""
    repo = ImageRepository(GeoImage, session)
    img = await repo.get(image_id)
    if not img:
        from common_utils.exceptions import NotFoundError
        raise NotFoundError(f"Görüntü bulunamadı: {image_id}")
    return img
