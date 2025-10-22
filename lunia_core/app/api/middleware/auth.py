"""HTTP authentication helpers for Lunia APIs."""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Sequence, Set

from app.compat.flask import request

from ...auth import (AccessDeniedError, JWTManager, JWTValidationError,
                     RBACManager, Role)
from ...auth.sso import OIDCClient, OIDCConfigurationError


class AuthError(RuntimeError):
    """Raised when authentication or authorization fails."""


@dataclass
class AuthContext:
    user_id: str
    roles: Set[Role]
    tenant_id: Optional[str]
    claims: dict
    token_type: str = "jwt"
    scopes: Set[str] = field(default_factory=set)

    def has_role(self, role: Role) -> bool:
        return role in self.roles


_JWT_MANAGER = JWTManager()
_RBAC_MANAGER = RBACManager()
_OIDC_CLIENT = OIDCClient()


def get_jwt_manager() -> JWTManager:
    return _JWT_MANAGER


def get_rbac_manager() -> RBACManager:
    return _RBAC_MANAGER


def get_oidc_client() -> OIDCClient:
    return _OIDC_CLIENT


# ---------------------------------------------------------------------------
def _admin_token() -> Optional[str]:
    token = os.getenv("ADMIN_TOKEN")
    if token:
        return token.strip()
    return None


def ensure_admin_access() -> AuthContext | None:
    """Validate that a request carries admin credentials.

    A request is considered authorised if either the X-Admin-Token header matches the
    configured ``ADMIN_TOKEN`` environment variable, or the authenticated context
    resolves to an admin/owner role.
    """

    configured = _admin_token()
    supplied = request.headers.get("X-Admin-Token") or request.args.get("admin_token")
    if configured and supplied and hmac.compare_digest(supplied.strip(), configured):
        return AuthContext(
            user_id="admin-token",
            roles={Role.OWNER},
            tenant_id=os.getenv("DEFAULT_TENANT", "public"),
            claims={"token": "admin"},
            token_type="admin-token",
            scopes={"*"},
        )

    try:
        context = authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER}, allow_viewer=False
        )
    except AuthError:  # pragma: no cover - handled by caller
        raise
    return context


def require_admin(func: Callable):
    """Decorator enforcing admin token/role presence."""

    def wrapper(*args, **kwargs):
        try:
            ensure_admin_access()
        except AuthError as exc:
            raise exc
        return func(*args, **kwargs)

    wrapper.__name__ = getattr(func, "__name__", "wrapped")
    return wrapper


# ---------------------------------------------------------------------------
def _extract_token() -> Optional[str]:
    header = request.headers.get("Authorization")
    if header and header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    legacy = request.headers.get("X-OPS-TOKEN") or request.headers.get("X-Admin-Token")
    if legacy:
        return legacy
    return None


# ---------------------------------------------------------------------------
def _default_context() -> AuthContext:
    default_role = os.getenv("AUTH_DEFAULT_ROLE", Role.OWNER.value)
    role = Role(default_role) if default_role in Role._value2member_map_ else Role.OWNER
    tenant = os.getenv("DEFAULT_TENANT", "public")
    return AuthContext(
        user_id="anonymous",
        roles={role},
        tenant_id=tenant,
        claims={"anonymous": True},
        token_type="anonymous",
        scopes={"*"},
    )


# ---------------------------------------------------------------------------
def authenticate_request(
    required_roles: Iterable[Role] | None = None,
    allow_viewer: bool = False,
    allow_auditor: bool = False,
    resource_tenant: Optional[str] = None,
    allowed_tenants: Sequence[str] | None = None,
) -> AuthContext:
    token = _extract_token()
    jwt_manager = get_jwt_manager()
    rbac = get_rbac_manager()

    if token is None:
        if jwt_manager.legacy_token is None and os.getenv("OPS_API_TOKEN") is None:
            # fully open mode
            context = _default_context()
            _authorize(
                context,
                required_roles,
                allow_viewer,
                allow_auditor,
                resource_tenant,
                allowed_tenants,
            )
            return context
        raise AuthError("missing token")

    payload = None
    token_type = "jwt"
    try:
        payload = jwt_manager.decode(token)
        token_type = "legacy" if payload.get("legacy") else "jwt"
    except JWTValidationError:
        if get_oidc_client().is_enabled():
            try:
                payload = get_oidc_client().introspect_token(token)
                token_type = "oidc"
            except OIDCConfigurationError as exc:
                raise AuthError(str(exc)) from exc
        else:
            raise AuthError("invalid token")

    roles = rbac.extract_roles(payload)
    tenant = payload.get("tenant") or payload.get("tenant_id") or payload.get("org")
    scopes_raw = payload.get("scopes") or []
    if isinstance(scopes_raw, str):
        scopes_raw = [scopes_raw]
    context = AuthContext(
        user_id=str(
            payload.get("sub")
            or payload.get("user_id")
            or payload.get("email")
            or "unknown"
        ),
        roles=roles,
        tenant_id=tenant,
        claims=payload,
        token_type=token_type,
        scopes=set(scopes_raw),
    )
    _authorize(
        context,
        required_roles,
        allow_viewer,
        allow_auditor,
        resource_tenant,
        allowed_tenants,
    )
    return context


# ---------------------------------------------------------------------------
def _authorize(
    context: AuthContext,
    required_roles: Iterable[Role] | None,
    allow_viewer: bool,
    allow_auditor: bool,
    resource_tenant: Optional[str],
    allowed_tenants: Sequence[str] | None,
) -> None:
    if required_roles is None:
        required_roles = {Role.ADMIN, Role.OWNER}
    try:
        get_rbac_manager().assert_authorized(
            context.roles,
            required_roles,
            allow_viewer=allow_viewer,
            allow_auditor=allow_auditor,
        )
        get_rbac_manager().enforce_tenant_isolation(
            context.tenant_id, allowed_tenants, resource_tenant
        )
    except AccessDeniedError as exc:
        raise AuthError(str(exc)) from exc


# ---------------------------------------------------------------------------
def require_roles(
    roles: Iterable[Role],
    allow_viewer: bool = False,
    allow_auditor: bool = False,
    resource_tenant: Optional[str] = None,
    allowed_tenants: Sequence[str] | None = None,
):
    """Decorator ensuring a request has the desired role set."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            authenticate_request(
                required_roles=roles,
                allow_viewer=allow_viewer,
                allow_auditor=allow_auditor,
                resource_tenant=resource_tenant,
                allowed_tenants=allowed_tenants,
            )
            return func(*args, **kwargs)

        wrapper.__name__ = getattr(func, "__name__", "wrapped")
        return wrapper

    return decorator


__all__ = [
    "AuthContext",
    "AuthError",
    "authenticate_request",
    "ensure_admin_access",
    "require_admin",
    "require_roles",
    "get_jwt_manager",
    "get_rbac_manager",
    "get_oidc_client",
]
