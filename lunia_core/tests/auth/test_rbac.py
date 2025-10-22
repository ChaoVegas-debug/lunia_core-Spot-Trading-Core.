from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.api.middleware import auth as auth_middleware
from app.api.middleware.auth import AuthError, authenticate_request
from app.auth import RBACManager, Role


@pytest.fixture(autouse=True)
def reset_env(monkeypatch):
    monkeypatch.delenv("OPS_API_TOKEN", raising=False)
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("AUTH_DEFAULT_ROLE", raising=False)
    monkeypatch.delenv("DEFAULT_TENANT", raising=False)
    monkeypatch.setenv("TENANT_WALL_ENFORCED", "true")
    # reset singletons
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager()
    auth_middleware._RBAC_MANAGER = RBACManager()
    auth_middleware._OIDC_CLIENT = auth_middleware.OIDCClient()
    auth_middleware.request = SimpleNamespace(headers={})
    yield
    auth_middleware.request = SimpleNamespace(headers={})


def _set_request_headers(headers: dict[str, str]) -> None:
    auth_middleware.request = SimpleNamespace(headers=headers)


def test_rbac_owner_allows_admin_routes(monkeypatch):
    monkeypatch.setenv("OPS_API_TOKEN", "legacy")
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager(legacy_token="legacy")
    _set_request_headers({"X-Admin-Token": "legacy"})
    context = authenticate_request(required_roles={Role.ADMIN, Role.OWNER})
    assert Role.OWNER in context.roles
    assert context.token_type in {"legacy", "jwt"}


def test_missing_token_raises_when_protected(monkeypatch):
    monkeypatch.setenv("OPS_API_TOKEN", "secret")
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager(legacy_token="secret")
    _set_request_headers({})
    with pytest.raises(AuthError):
        authenticate_request(required_roles={Role.ADMIN})


def test_oidc_payload_respected(monkeypatch):
    import json

    payload = {"sub": "oidc-user", "roles": ["viewer"], "tenant": "alpha"}
    _set_request_headers({"Authorization": f"Bearer {json.dumps(payload)}"})
    auth_middleware._OIDC_CLIENT = auth_middleware.OIDCClient(
        issuer_url="https://example.com", client_id="cli"
    )
    context = authenticate_request(required_roles={Role.VIEWER}, allow_viewer=True)
    assert context.user_id == "oidc-user"
    assert context.tenant_id == "alpha"


def test_chinese_wall_enforced(monkeypatch):
    monkeypatch.setenv("OPS_API_TOKEN", "legacy")
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager(legacy_token="legacy")
    _set_request_headers({"X-OPS-TOKEN": "legacy"})
    with pytest.raises(AuthError):
        authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER}, resource_tenant="beta"
        )


def test_viewer_can_access_read_only(monkeypatch):
    manager = RBACManager()
    roles = manager.extract_roles({"roles": ["viewer"]})
    manager.assert_authorized(roles, {Role.VIEWER}, allow_viewer=True)


def test_auditor_is_read_only(monkeypatch):
    manager = RBACManager()
    roles = manager.extract_roles({"roles": ["auditor"]})
    with pytest.raises(Exception):
        manager.assert_authorized(roles, {Role.ADMIN})
    manager.assert_authorized(roles, {Role.AUDITOR}, allow_auditor=True)
