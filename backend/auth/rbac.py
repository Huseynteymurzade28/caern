"""Role-based access control helpers."""
from __future__ import annotations

from data_access.models.user import UserRole

# Privilege ordering: higher index → more permissions
_ROLE_ORDER = [UserRole.viewer, UserRole.analist, UserRole.ai_engineer, UserRole.admin]


def has_min_role(user_role: UserRole, required: UserRole) -> bool:
    """Return True if user_role is at least as privileged as required."""
    try:
        return _ROLE_ORDER.index(user_role) >= _ROLE_ORDER.index(required)
    except ValueError:
        return False


ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.viewer: {"jobs:read", "images:read", "reports:read"},
    UserRole.analist: {
        "jobs:read", "jobs:write",
        "images:read", "images:write",
        "reports:read", "reports:write",
    },
    UserRole.ai_engineer: {
        "jobs:read", "jobs:write",
        "images:read", "images:write",
        "reports:read", "reports:write",
        "models:read", "models:write",
    },
    UserRole.admin: {"*"},
}


def can(user_role: UserRole, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(user_role, set())
    return "*" in perms or permission in perms
