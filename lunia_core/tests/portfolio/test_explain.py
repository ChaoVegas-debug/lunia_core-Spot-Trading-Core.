"""Tests for the portfolio explanation endpoint."""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")
pytestmark = pytest.mark.requires_flask


def test_portfolio_explain_endpoint(monkeypatch) -> None:
    monkeypatch.setenv("BINANCE_USE_TESTNET", "false")
    monkeypatch.setenv("ENABLE_REDIS", "false")

    from app.services.api import flask_app

    importlib.reload(flask_app)
    client = flask_app.app.test_client()

    response = client.get("/api/portfolio/explain/BTCUSDT")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["asset"] == "BTCUSDT"
    assert "decision_tree" in payload
    assert isinstance(payload["decision_tree"], list)
    assert "confidence" in payload
    assert 0.0 <= payload["confidence"] <= 1.0
