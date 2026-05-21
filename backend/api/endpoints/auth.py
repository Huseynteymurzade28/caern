"""Authentication endpoints: register, login and token refresh."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from auth.service import AuthService
from api.deps import DBSession
from data_access.models.user import UserRole

router = APIRouter(prefix="/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest, session: DBSession):
    """Create a new account and issue JWT tokens for immediate login."""
    svc = AuthService(session)
    await svc.create_user(
        email=body.email,
        username=body.username,
        password=body.password,
        role=UserRole.analist,
    )
    access, refresh = await svc.login(body.email, body.password)
    return TokenResponse(access_token=access, refresh_token=refresh)


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
