"""Admin endpoints: user management, audit logs."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel, EmailStr

from api.deps import CurrentUser, DBSession, require_role
from auth.service import AuthService
from common_utils.exceptions import NotFoundError
from data_access.models.audit_log import AuditLog
from data_access.models.user import User, UserRole
from data_access.repositories.user_repo import UserRepository
from sqlalchemy import select

router = APIRouter(prefix="/admin", tags=["Admin"])


class CreateUserRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    role: UserRole = UserRole.viewer


class UserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class UpdateUserRequest(BaseModel):
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


@router.post("/users", response_model=UserResponse, dependencies=[require_role(UserRole.admin)])
async def create_user(body: CreateUserRequest, session: DBSession, current_user: CurrentUser):
    """Admin: create a new platform user."""
    from data_access.models.audit_log import AuditAction

    svc = AuthService(session)
    user = await svc.create_user(body.email, body.username, body.password, body.role)
    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_CREATED,
        resource_type="User",
        resource_id=user.id,
    ))
    return user


@router.patch("/users/{user_id}", response_model=UserResponse, dependencies=[require_role(UserRole.admin)])
async def update_user(
    user_id: str, body: UpdateUserRequest, session: DBSession, current_user: CurrentUser
):
    """Admin: update user role or active status."""
    from data_access.models.audit_log import AuditAction

    repo = UserRepository(User, session)
    user = await repo.get(user_id)
    if not user:
        raise NotFoundError(f"Kullanıcı bulunamadı: {user_id}")

    if body.role is not None:
        await repo.update_role(user, body.role)
    if body.is_active is not None:
        await repo.set_active(user, body.is_active)

    session.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATED,
        resource_type="User",
        resource_id=user_id,
    ))
    return user


@router.get("/audit", dependencies=[require_role(UserRole.admin)])
async def get_audit_logs(
    session: DBSession,
    current_user: CurrentUser,
    limit: int = Query(50, le=500),
    offset: int = Query(0, ge=0),
):
    """Admin: paginated audit log retrieval."""
    result = await session.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "userId": log.user_id,
            "action": log.action,
            "resourceType": log.resource_type,
            "resourceId": log.resource_id,
            "ipAddress": log.ip_address,
            "createdAt": str(log.created_at),
        }
        for log in logs
    ]
