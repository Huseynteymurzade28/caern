"""Authentication endpoints: login and token refresh."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from auth.service import AuthService
from api.deps import DBSession

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: DBSession):
    """Authenticate user and issue JWT tokens."""
    svc = AuthService(session)
    access, refresh = await svc.login(body.email, body.password)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, session: DBSession):
    """Issue new token pair from a valid refresh token."""
    svc = AuthService(session)
    access, refresh = await svc.refresh(body.refresh_token)
    return TokenResponse(access_token=access, refresh_token=refresh)
