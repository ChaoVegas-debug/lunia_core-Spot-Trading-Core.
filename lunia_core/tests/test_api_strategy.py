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
    from app.services.api import flask_app

    importlib.reload(flask_app)
    return flask_app


def test_strategy_preview_confirm_undo(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    preview_resp = client.post(
        "/api/v1/strategy/apply", json={"strategy": "conservative"}
    )
    assert preview_resp.status_code == 200
    preview_payload = preview_resp.get_json()
    assert preview_payload["strategy"] == "conservative"
    assert preview_payload["delta"]
    preview_id = preview_payload["preview_id"]

    confirm_resp = client.post(
        "/api/v1/strategy/assign", json={"preview_id": preview_id}
    )
    assert confirm_resp.status_code == 200
    confirm_payload = confirm_resp.get_json()
    assert confirm_payload["status"] == "applied"
    assert "undo_token" in confirm_payload
    undo_token = confirm_payload["undo_token"]

    changes_resp = client.get("/api/v1/portfolio/changes")
    assert changes_resp.status_code == 200
    changes_payload = changes_resp.get_json()
    assert changes_payload["count"] >= 1

    undo_resp = client.post(
        "/api/v1/strategy/assign", json={"undo_id": undo_token, "action": "undo"}
    )
    assert undo_resp.status_code == 200
    undo_payload = undo_resp.get_json()
    assert undo_payload["status"] == "restored"

    second_changes = client.get("/api/v1/portfolio/changes").get_json()
    assert second_changes["count"] >= 2

    from app.core.state import reset_state

    reset_state()
