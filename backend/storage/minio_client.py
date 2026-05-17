"""MinIO wrapper for image and report storage with AES-256 server-side encryption."""
from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO, Optional

from minio import Minio
from minio.commonconfig import ENABLED, Tags
from minio.error import S3Error
from minio.sseconfig import Rule, SSEConfig

from common_utils.config import settings
from common_utils.exceptions import StorageError
from common_utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_use_ssl,
    )


def ensure_bucket_exists(bucket: str = settings.minio_bucket) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        # Enable server-side AES-256 encryption
        client.set_bucket_encryption(
            bucket,
            SSEConfig(Rule.new_sse_s3_rule()),
        )
        log.info("bucket_created", bucket=bucket)


def upload_file(
    object_name: str,
    data: BinaryIO,
    length: int,
    content_type: str = "application/octet-stream",
    bucket: str = settings.minio_bucket,
) -> str:
    """Upload bytes to MinIO; returns the object path."""
    ensure_bucket_exists(bucket)
    try:
        get_minio_client().put_object(
            bucket, object_name, data, length, content_type=content_type
        )
        log.info("file_uploaded", object_name=object_name, bucket=bucket)
        return object_name
    except S3Error as exc:
        raise StorageError(f"MinIO yükleme hatası: {exc}") from exc


def upload_path(local_path: Path, object_name: str, bucket: str = settings.minio_bucket) -> str:
    size = local_path.stat().st_size
    with local_path.open("rb") as fh:
        return upload_file(object_name, fh, size, bucket=bucket)


def download_to_path(object_name: str, dest: Path, bucket: str = settings.minio_bucket) -> None:
    try:
        response = get_minio_client().get_object(bucket, object_name)
        dest.write_bytes(response.read())
    except S3Error as exc:
        raise StorageError(f"MinIO indirme hatası: {exc}") from exc
    finally:
        response.close()
        response.release_conn()


def get_presigned_url(object_name: str, expires_seconds: int = 3600, bucket: str = settings.minio_bucket) -> str:
    from datetime import timedelta

    try:
        return get_minio_client().presigned_get_object(
            bucket, object_name, expires=timedelta(seconds=expires_seconds)
        )
    except S3Error as exc:
        raise StorageError(f"Pre-signed URL hatası: {exc}") from exc
