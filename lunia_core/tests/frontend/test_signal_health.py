"""Tests for the Signal Health frontend helpers."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from app.frontend.components.SignalHealth import (
    collect_signal_health_summary, is_signal_health_enabled)


@dataclass
class _StubOrchestrator:
    history: list[dict]


def test_signal_health_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_SIGNAL_HEALTH_ENABLED", "false")
    assert not is_signal_health_enabled()
    summary = collect_signal_health_summary()
    assert summary.enabled is False
    assert summary.top_features == ()


def test_signal_health_summary_with_data(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRONTEND_SIGNAL_HEALTH_ENABLED", "true")
    monkeypatch.setenv("GRAFANA_BASE_URL", "http://grafana")
    monkeypatch.setenv("GRAFANA_SIGNAL_DASHBOARD", "sig")
    orchestrator = _StubOrchestrator(
        history=[
            {"provider": "openai", "confidence": 0.7},
            {"provider": "anthropic", "accuracy": 0.9},
        ]
    )
    trades = [
        {"pnl": 10.0},
        {"pnl": -5.0},
        {"pnl": 0.0},  # ignored
    ]
    summary = collect_signal_health_summary(
        orchestrator=orchestrator, trades=trades, limit=2
    )
    assert summary.enabled is True
    assert summary.sample_size == 2
    assert summary.accuracy == pytest.approx(0.5, rel=1e-3)
    assert summary.llm_confidence == pytest.approx(0.8, rel=1e-3)
    assert len(summary.top_features) == 2
    assert summary.grafana_panels[0].url.startswith("http://grafana/d/sig")


def test_signal_health_summary_handles_missing_trades(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FRONTEND_SIGNAL_HEALTH_ENABLED", "true")
    orchestrator = _StubOrchestrator(history=[{"accuracy": 0.95}])
    summary = collect_signal_health_summary(
        orchestrator=orchestrator, trades=[], limit=1
    )
    assert summary.sample_size == 1
    assert summary.accuracy == pytest.approx(1.0)
