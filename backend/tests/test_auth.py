"""Auth service unit tests."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from auth.jwt_handler import create_access_token, decode_token
from auth.password import hash_password, verify_password
from common_utils.exceptions import AuthenticationError, TokenExpiredError


def test_password_hash_and_verify():
    hashed = hash_password("secret123")
    assert verify_password("secret123", hashed)
    assert not verify_password("wrong", hashed)


def test_create_and_decode_access_token():
    token = create_access_token("user-123", extra={"role": "analist"})
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["role"] == "analist"
    assert payload["type"] == "access"


def test_decode_wrong_type_raises():
    from auth.jwt_handler import create_refresh_token
    refresh = create_refresh_token("user-abc")
    with pytest.raises(AuthenticationError):
        decode_token(refresh, expected_type="access")


@pytest.mark.asyncio
async def test_login_wrong_password(session):
    from auth.service import AuthService
    from data_access.models.user import User
    from auth.password import hash_password

    user = User(
        email="test@test.com",
        username="testuser",
        password_hash=hash_password("correct"),
        role="viewer",
    )
    session.add(user)
    await session.flush()

    svc = AuthService(session)
    with pytest.raises(AuthenticationError):
        await svc.login("test@test.com", "wrong")
