"""Domain exception hierarchy for the CAERN platform."""
from __future__ import annotations

import uuid
from typing import Optional


class CaernBaseError(Exception):
    """Root exception; all custom errors extend this."""

    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, *, trace_id: Optional[str] = None) -> None:
        super().__init__(message)
        self.message = message
        self.trace_id = trace_id or str(uuid.uuid4())

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "traceId": self.trace_id,
            }
        }


# ── Auth ─────────────────────────────────────────────────────────────────────

class AuthenticationError(CaernBaseError):
    http_status = 401
    error_code = "AUTHENTICATION_FAILED"


class TokenExpiredError(AuthenticationError):
    error_code = "TOKEN_EXPIRED"


class AccountLockedError(AuthenticationError):
    error_code = "ACCOUNT_LOCKED"


class PermissionDeniedError(CaernBaseError):
    http_status = 403
    error_code = "PERMISSION_DENIED"


# ── Resource ─────────────────────────────────────────────────────────────────

class NotFoundError(CaernBaseError):
    http_status = 404
    error_code = "NOT_FOUND"


class ConflictError(CaernBaseError):
    http_status = 409
    error_code = "CONFLICT"


# ── Validation ───────────────────────────────────────────────────────────────

class ValidationError(CaernBaseError):
    http_status = 422
    error_code = "VALIDATION_ERROR"


class UnsupportedFormatError(ValidationError):
    error_code = "UNSUPPORTED_FORMAT"


class FileTooLargeError(ValidationError):
    error_code = "FILE_TOO_LARGE"


class MissingCRSError(ValidationError):
    error_code = "MISSING_CRS"


# ── Geo processing ───────────────────────────────────────────────────────────

class GeoAlignmentError(CaernBaseError):
    http_status = 500
    error_code = "GEO_ALIGNMENT_FAILED"


class GeoProcessingError(CaernBaseError):
    http_status = 500
    error_code = "GEO_PROCESSING_FAILED"


# ── AI / Analysis ────────────────────────────────────────────────────────────

class ModelNotFoundError(NotFoundError):
    error_code = "MODEL_NOT_FOUND"


class ModelLoadError(CaernBaseError):
    http_status = 500
    error_code = "MODEL_LOAD_FAILED"


class GPUTimeoutError(CaernBaseError):
    http_status = 504
    error_code = "GPU_TIMEOUT"


class AnalysisJobError(CaernBaseError):
    http_status = 500
    error_code = "ANALYSIS_JOB_FAILED"


class JobCancelledError(AnalysisJobError):
    error_code = "JOB_CANCELLED"


# ── Storage ──────────────────────────────────────────────────────────────────

class StorageError(CaernBaseError):
    http_status = 500
    error_code = "STORAGE_ERROR"


# ── Reporting ────────────────────────────────────────────────────────────────

class ReportGenerationError(CaernBaseError):
    http_status = 500
    error_code = "REPORT_GENERATION_FAILED"
