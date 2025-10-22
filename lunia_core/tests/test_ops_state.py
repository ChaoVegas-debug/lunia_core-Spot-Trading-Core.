import os

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")

from app.api.middleware import auth as auth_middleware
from app.core.state import reset_state
from app.services.api.flask_app import app


@pytest.fixture(autouse=True)
def _reset_state():
    reset_state()
    yield
    reset_state()


@pytest.fixture
def client(monkeypatch):
    monkeypatch.delenv("OPS_API_TOKEN", raising=False)
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_ops_state_get(client):
    resp = client.get("/ops/state")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["auto_mode"] in {True, False}


def test_ops_state_toggle_requires_token(monkeypatch):
    monkeypatch.setenv("OPS_API_TOKEN", "secret")
    auth_middleware._JWT_MANAGER = auth_middleware.JWTManager(legacy_token="secret")
    app.config["TESTING"] = True
    with app.test_client() as client:
        resp = client.post("/ops/auto_off")
        assert resp.status_code == 403
        resp = client.post(
            "/ops/auto_off", headers={"X-Admin-Token": os.getenv("OPS_API_TOKEN")}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["auto_mode"] is False
