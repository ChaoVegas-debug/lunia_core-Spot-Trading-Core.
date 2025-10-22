"""End-to-end integration workflow tests."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_flask]


def _reload(module_name: str):
    """Reload a module if already imported, otherwise import it."""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def test_workflow_e2e(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Exercise funds limits, strategy switches, and scheduler fallback flows."""

    pytest.importorskip("flask")

    # Ensure deterministic sandbox environment
    monkeypatch.setenv("ADMIN_TOKEN", "secret-token")
    monkeypatch.setenv("AUTH_DEFAULT_ROLE", "owner")
    monkeypatch.setenv("BINANCE_FORCE_MOCK", "true")
    monkeypatch.setenv("BINANCE_USE_TESTNET", "true")
    monkeypatch.setenv("BINANCE_FUTURES_TESTNET", "true")
    monkeypatch.setenv("ENABLE_REDIS", "false")
    monkeypatch.setenv("FUNDS_STATE_DIR", str(tmp_path / "funds"))
    monkeypatch.setenv("FUNDS_LIMITS_PATH", str(tmp_path / "funds" / "limits.json"))
    monkeypatch.setenv("FUNDS_AUDIT_PATH", str(tmp_path / "funds" / "audit.jsonl"))
    monkeypatch.setenv("STRATEGY_LOG_DIR", str(tmp_path / "strategy"))
    monkeypatch.setenv(
        "STRATEGY_CHANGE_LOG_PATH", str(tmp_path / "strategy" / "changes.jsonl")
    )

    # Redirect state/audit artefacts to the temporary workspace
    core_state = _reload("app.core.state")
    monkeypatch.setattr(
        core_state, "STATE_PATH", tmp_path / "state.json", raising=False
    )
    monkeypatch.setattr(core_state, "STATE_LOG", tmp_path / "state.log", raising=False)
    core_state._CURRENT_STATE = None  # reset cached runtime state
    core_state._write_state_file(core_state._DEFAULT_STATE)
    monkeypatch.setattr(
        core_state, "get_runtime_state", core_state.get_state, raising=False
    )

    audit_module = _reload("app.logging.audit")
    monkeypatch.setattr(
        audit_module.audit_logger, "log_path", tmp_path / "audit.log", raising=False
    )

    # Load Flask API and scheduler modules fresh with the sandbox configuration
    flask_module = _reload("app.services.api.flask_app")
    rebalancer_module = _reload("app.services.scheduler.rebalancer")

    app = flask_module.app
    funds_manager = flask_module.funds_manager
    strategy_applicator = flask_module.strategy_applicator

    client = app.test_client()

    # Baseline trade succeeds with relaxed exposure limits
    core_state.set_state({"spot": {"max_symbol_exposure_pct": 1.0}})
    baseline = client.post(
        "/trade/spot/demo",
        json={"symbol": "BTCUSDT", "side": "BUY", "qty": 0.1},
    )
    assert baseline.status_code == 200
    assert baseline.get_json()["ok"] is True

    admin_headers = {"X-Admin-Token": "secret-token"}

    # Step 1: adjust funds limits and ensure the agent enforces the tighter cap
    preview = client.post(
        "/api/v1/funds/limits/apply",
        headers=admin_headers,
        json={"global_limit": {"max_allocation_pct": 25}},
    )
    assert preview.status_code == 200

    confirmed = client.post("/api/v1/funds/limits/confirm", headers=admin_headers)
    payload = confirmed.get_json()
    assert confirmed.status_code == 200
    assert payload["applied"]["global"]["max_allocation_pct"] == 25

    refreshed = client.get("/api/v1/funds/limits", headers=admin_headers)
    assert refreshed.status_code == 200
    assert refreshed.get_json()["limits"]["global"]["max_allocation_pct"] == 25

    limits = funds_manager.load_current_limits()
    assert limits["global"]["max_allocation_pct"] == 25

    # Mirror the tightened limit into runtime exposure caps and verify large trades are blocked
    core_state.set_state(
        {
            "spot": {
                "max_symbol_exposure_pct": limits["global"]["max_allocation_pct"]
                / 100.0
            }
        }
    )
    blocked = client.post(
        "/trade/spot/demo",
        json={"symbol": "BTCUSDT", "side": "BUY", "qty": 0.6},
    )
    blocked_body = blocked.get_json()
    assert blocked.status_code == 400
    assert blocked_body["ok"] is False
    assert blocked_body["reason"] in {"over_exposure", "max_symbol_risk"}

    # Step 2: apply an aggressive strategy preset and ensure the change is recorded
    apply_resp = client.post(
        "/api/v1/strategy/apply",
        headers=admin_headers,
        json={"strategy": "aggressive", "notes": "integration"},
    )
    assert apply_resp.status_code == 200
    preview_id = apply_resp.get_json()["preview_id"]

    assign_resp = client.post(
        "/api/v1/strategy/assign",
        headers=admin_headers,
        json={"preview_id": preview_id},
    )
    assert assign_resp.status_code == 200

    state_after = core_state.get_state()
    weights_after = state_after["spot"]["weights"]
    assert weights_after["scalping_breakout"] > weights_after.get(
        "bollinger_reversion", 0.0
    )

    history = client.get("/api/v1/portfolio/changes", headers=admin_headers)
    history_payload = history.get_json()
    assert history.status_code == 200
    assert history_payload["count"] >= 1

    # Step 3: trigger the scheduler safeguard and verify the conservative preset is enforced
    rebalancer_module._trigger_safe_mode(  # type: ignore[attr-defined]
        strategy_applicator,
        "volatility-spike",
        {"volatility": {"volatility_pct": 80}},
    )
    safe_state = core_state.get_state()
    safe_weights = safe_state["spot"]["weights"]

    from app.core.strategy.manager import _PRESET_WEIGHTS

    conservative = _PRESET_WEIGHTS["conservative"]
    for name, expected in conservative.items():
        assert safe_weights.get(name, 0.0) == pytest.approx(expected, rel=1e-3)

    recent_changes = list(strategy_applicator.recent_changes(limit=2))
    assert recent_changes, "strategy journal should record scheduler changes"
    assert any(entry.get("actor") == "scheduler" for entry in recent_changes)
