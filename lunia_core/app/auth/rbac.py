"""Role based access control utilities with tenant isolation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Sequence, Set


class AccessDeniedError(Exception):
    """Raised when a user does not meet role requirements."""


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"
    AUDITOR = "auditor"

    @classmethod
    def from_claim(cls, value: str) -> "Role":
        for role in cls:
            if role.value == value.lower():
                return role
        raise ValueError(f"unknown role: {value}")


ROLE_HIERARCHY = {
    Role.OWNER: {Role.OWNER, Role.ADMIN, Role.VIEWER, Role.AUDITOR},
    Role.ADMIN: {Role.ADMIN, Role.VIEWER, Role.AUDITOR},
    Role.VIEWER: {Role.VIEWER},
    Role.AUDITOR: {Role.AUDITOR},
}


@dataclass
class TenantPolicy:
    tenant_id: Optional[str]
    allowed_tenants: Set[str]


class RBACManager:
    """Performs role checks and tenant isolation."""

    def __init__(
        self, default_role: Role | None = None, enforce_tenant_wall: bool | None = None
    ) -> None:
        if default_role is not None:
            resolved_role = default_role
        else:
            env_role = os.getenv("AUTH_DEFAULT_ROLE", Role.VIEWER.value)
            resolved_role = Role._value2member_map_.get(env_role.lower(), Role.VIEWER)
        self.default_role = resolved_role
        enforce_env = os.getenv("TENANT_WALL_ENFORCED", "true").lower()
        self.enforce_tenant_wall = (
            enforce_tenant_wall
            if enforce_tenant_wall is not None
            else enforce_env == "true"
        )

    # ------------------------------------------------------------------
    def extract_roles(self, claims: dict) -> Set[Role]:
        roles_raw = claims.get("roles") or claims.get("role") or []
        if isinstance(roles_raw, str):
            roles_raw = [roles_raw]
        roles: Set[Role] = set()
        for value in roles_raw:
            try:
                roles.add(Role.from_claim(str(value)))
            except ValueError:
                continue
        if not roles:
            roles = {self.default_role}
        return roles

    # ------------------------------------------------------------------
    def assert_authorized(
        self,
        roles: Set[Role],
        required_roles: Iterable[Role],
        allow_viewer: bool = False,
        allow_auditor: bool = False,
    ) -> None:
        allowed_roles = set(required_roles)
        if allow_viewer:
            allowed_roles.add(Role.VIEWER)
        if allow_auditor:
            allowed_roles.add(Role.AUDITOR)
        for role in roles:
            hierarchy = ROLE_HIERARCHY.get(role, {role})
            if hierarchy & allowed_roles:
                return
        raise AccessDeniedError("insufficient role")

    # ------------------------------------------------------------------
    def enforce_tenant_isolation(
        self,
        user_tenant: Optional[str],
        allowed_tenants: Sequence[str] | None,
        resource_tenant: Optional[str],
    ) -> None:
        if not self.enforce_tenant_wall:
            return
        if resource_tenant is None:
            return
        tenants = set()
        if user_tenant:
            tenants.add(user_tenant)
        if allowed_tenants:
            tenants.update({str(t) for t in allowed_tenants})
        if resource_tenant not in tenants:
            raise AccessDeniedError("tenant access denied")


__all__ = ["RBACManager", "Role", "AccessDeniedError", "ROLE_HIERARCHY"]
