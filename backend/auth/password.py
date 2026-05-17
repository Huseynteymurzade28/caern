"""Argon2 password hashing utilities."""
from __future__ import annotations

from passlib.context import CryptContext

_ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _ctx.verify(plain, hashed)
