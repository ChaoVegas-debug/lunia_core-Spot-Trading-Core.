"""Integration style smoke tests for the Flask API."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_flask]


def test_health_and_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services.api.flask_app import app

    with app.test_client() as client:
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json.get("status") == "ok"

        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert b"process_start_time_seconds" in metrics.data
