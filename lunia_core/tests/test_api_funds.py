import importlib

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")
pytestmark = pytest.mark.requires_flask


def _reload_app(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_REDIS", "false")
    monkeypatch.setenv("FUNDS_STATE_DIR", str(tmp_path))
    from app.services.api import flask_app

    importlib.reload(flask_app)
    return flask_app


def test_funds_limits_preview_confirm_undo(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    # initial load
    limits_resp = client.get("/api/v1/funds/limits")
    assert limits_resp.status_code == 200
    payload = limits_resp.get_json()
    assert "limits" in payload
    assert payload["limits"]["global"]["max_allocation_pct"] == 100.0

    apply_resp = client.post("/api/v1/funds/limits/apply", json={"global_limit": 55})
    assert apply_resp.status_code == 200
    preview = apply_resp.get_json()
    assert preview["preview"]["global"]["max_allocation_pct"] == 55.0
    assert "preview_delta" in preview

    confirm_resp = client.post("/api/v1/funds/limits/confirm")
    assert confirm_resp.status_code == 200
    confirmed = confirm_resp.get_json()
    assert confirmed["applied"]["global"]["max_allocation_pct"] == 55.0

    undo_resp = client.post("/api/v1/funds/limits/undo")
    assert undo_resp.status_code == 200
    restored = undo_resp.get_json()
    assert restored["restored"]["global"]["max_allocation_pct"] == 100.0


def test_balances_check_endpoint(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    response = client.get("/api/v1/funds/balances/check")
    assert response.status_code == 200
    payload = response.get_json()
    assert "aggregated" in payload
    assert isinstance(payload["aggregated"], dict)
    summary = payload.get("summary", {})
    assert "balances" in summary
