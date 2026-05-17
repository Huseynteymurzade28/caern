"""AI Model management endpoints."""
from __future__ import annotations

import io
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel
from typing import Optional

from api.deps import CurrentUser, DBSession, require_role
from common_utils.exceptions import NotFoundError
from data_access.models.ai_model import AIModel, ModelType
from data_access.models.audit_log import AuditAction, AuditLog
from data_access.models.user import UserRole
from data_access.repositories.model_repo import AIModelRepository
from storage.minio_client import upload_file

router = APIRouter(prefix="/models", tags=["AI Models"])


class ModelResponse(BaseModel):
    id: str
    name: str
    version: str
    model_type: str
    is_active: bool
    f1_score: Optional[float]

    class Config:
        from_attributes = True


@router.post("", response_model=ModelResponse, dependencies=[require_role(UserRole.ai_engineer)])
async def upload_model(
    name: str = Form(...),
    version: str = Form(...),
    model_type: ModelType = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    session: DBSession = None,
    current_user: CurrentUser = None,
):
    """Upload a .pt or .onnx model file."""
    import uuid

    data = await file.read()
    ext = Path(file.filename).suffix
    object_name = f"models/{uuid.uuid4()}{ext}"
    upload_file(object_name, io.BytesIO(data), len(data))

    model = AIModel(
        name=name,
        version=version,
        model_type=model_type,
        file_path=object_name,
        description=description,
    )
    repo = AIModelRepository(AIModel, session)
    model = await repo.create(model)

    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.MODEL_UPLOADED,
        resource_type="AIModel",
        resource_id=model.id,
    ))
    return model


@router.post("/{model_id}/activate", response_model=ModelResponse, dependencies=[require_role(UserRole.ai_engineer)])
async def activate_model(model_id: str, session: DBSession, current_user: CurrentUser):
    """Set a model as the active default (deactivates others)."""
    repo = AIModelRepository(AIModel, session)
    model = await repo.get(model_id)
    if not model:
        raise NotFoundError(f"Model bulunamadı: {model_id}")

    model = await repo.activate(model)

    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.MODEL_ACTIVATED,
        resource_type="AIModel",
        resource_id=model_id,
    ))
    return model


@router.get("", response_model=list[ModelResponse], dependencies=[require_role(UserRole.ai_engineer)])
async def list_models(session: DBSession, current_user: CurrentUser):
    repo = AIModelRepository(AIModel, session)
    return await repo.list(limit=100)
