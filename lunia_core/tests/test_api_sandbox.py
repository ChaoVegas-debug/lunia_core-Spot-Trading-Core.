import importlib
import time

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")
pytestmark = pytest.mark.requires_flask


def _reload_app(monkeypatch, tmp_path):
    monkeypatch.setenv("ENABLE_REDIS", "false")
    monkeypatch.setenv("INSTALL_BACKTEST", "1")
    from app.services.api import flask_app

    importlib.reload(flask_app)
    return flask_app


def test_sandbox_backtest_flow(monkeypatch, tmp_path):
    flask_app = _reload_app(monkeypatch, tmp_path)
    client = flask_app.app.test_client()

    run_resp = client.post(
        "/api/v1/sandbox/run",
        json={"strategy": "conservative", "days": 10, "initial_capital": 5000},
    )
    assert run_resp.status_code == 200
    payload = run_resp.get_json()
    job_id = payload["job_id"]
    assert payload["status"] in {"queued", "running", "completed"}

    # Poll until job completes (the synthetic engine usually finishes in milliseconds).
    for _ in range(5):
        job_resp = client.get(f"/api/v1/sandbox/{job_id}")
        assert job_resp.status_code == 200
        job = job_resp.get_json()
        if job["status"] == "completed":
            assert "result" in job
            metrics = job["result"]["metrics"]
            assert "total_return_pct" in metrics
            assert "equity_curve" in job["result"]
            break
        time.sleep(0.05)
    else:  # pragma: no cover - unexpected slow execution
        pytest.fail("backtest did not complete in time")
