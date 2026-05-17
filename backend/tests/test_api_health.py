"""API health and auth endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client):
    resp = await client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "badpass"},
    )
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_images_unauthorized(client):
    resp = await client.get("/images/some-id")
    assert resp.status_code == 403
