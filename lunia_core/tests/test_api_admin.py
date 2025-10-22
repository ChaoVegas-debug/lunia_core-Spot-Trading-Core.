"""Admin API smoke tests."""

import importlib

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")
pytestmark = pytest.mark.requires_flask


def _reload_app(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_REDIS", "false")
    monkeypatch.setenv("STRATEGY_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv(
        "STRATEGY_CHANGE_LOG_PATH", str(tmp_path / "logs" / "journal.jsonl")
    )
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    from app.services.api import flask_app

    importlib.reload(flask_app)
    return flask_app


def test_admin_endpoints_require_token(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    resp = client.get("/api/v1/admin/overview")
    assert resp.status_code == 403

    ok = client.get("/api/v1/admin/overview", headers={"X-Admin-Token": "secret-token"})
    assert ok.status_code == 200
    payload = ok.get_json()
    assert "funds" in payload


def test_admin_users_and_performance(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    headers = {"X-Admin-Token": "secret-token"}

    users_resp = client.get("/api/v1/admin/users", headers=headers)
    assert users_resp.status_code == 200
    users_payload = users_resp.get_json()
    assert "items" in users_payload

    perf_resp = client.get("/api/v1/admin/strategies/performance", headers=headers)
    assert perf_resp.status_code == 200
    perf_payload = perf_resp.get_json()
    assert "items" in perf_payload
