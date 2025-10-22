import importlib

import pytest

pytest.importorskip("flask", reason="Flask not available in offline/proxy env")
pytestmark = pytest.mark.requires_flask


def test_manual_signal(monkeypatch):
    monkeypatch.setenv("BINANCE_USE_TESTNET", "false")
    monkeypatch.setenv("ENABLE_REDIS", "false")
    from app.services.api import flask_app

    importlib.reload(flask_app)
    client = flask_app.app.test_client()
    response = client.post(
        "/signal",
        json={"symbol": "BTCUSDT", "side": "BUY", "qty": 0.01},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "executed" in data
    assert isinstance(data["executed"], list)


def test_signals_endpoint_includes_layers(monkeypatch):
    monkeypatch.setenv("BINANCE_USE_TESTNET", "true")
    monkeypatch.setenv("ENABLE_REDIS", "false")
    monkeypatch.delenv("OPS_API_TOKEN", raising=False)
    from app.services.api import flask_app

    importlib.reload(flask_app)

    # Ensure orchestrator lookups are skipped for deterministic tests
    from app.services.api import signals as signals_api

    signals_api._ORCHESTRATOR = None

    def fake_gather_signals(*_args, **_kwargs):
        return {
            "signals": [
                {
                    "symbol": "BTCUSDT",
                    "side": "BUY",
                    "strategy": "demo",
                    "score": 0.8,
                    "qty": 0.01,
                    "price": 20_000.0,
                    "notional_usd": 200.0,
                    "stop_pct": 0.01,
                    "take_pct": 0.03,
                }
            ]
        }

    monkeypatch.setattr(flask_app.supervisor, "gather_signals", fake_gather_signals)

    client = flask_app.app.test_client()
    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, list)
    assert payload
    entry = payload[0]
    assert "explanation_layers" in entry
    assert "certainty_score" in entry
    assert "alternative_scenarios" in entry
    assert "risk_metrics" in entry
