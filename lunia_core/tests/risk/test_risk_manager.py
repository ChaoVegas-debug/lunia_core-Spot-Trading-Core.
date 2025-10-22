"""Unit tests for enhanced risk manager."""

from __future__ import annotations

import pytest
from app.core.risk.manager import RiskLimits, RiskManager
from app.monitoring.abuse_detector import MarketAbuseMonitor
from app.risk import get_idempotency_store


def setup_function() -> None:
    store = get_idempotency_store()
    store.clear()


def test_idempotency_blocks_duplicate_orders() -> None:
    store = get_idempotency_store()
    store.clear()
    manager = RiskManager(
        RiskLimits(),
        idempotency_store=store,
        abuse_monitor=MarketAbuseMonitor(min_notional_usd=0.0),
    )

    ok, reason = manager.validate_order(
        equity_usd=10_000,
        order_value_usd=50,
        leverage=1.0,
        idempotency_key="order-123",
        symbol="BTCUSDT",
        side="BUY",
    )
    assert ok, reason

    ok, reason = manager.validate_order(
        equity_usd=10_000,
        order_value_usd=50,
        leverage=1.0,
        idempotency_key="order-123",
        symbol="BTCUSDT",
        side="BUY",
    )
    assert not ok
    assert reason == "duplicate_order"


def test_market_abuse_detection_blocks_spoofing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = get_idempotency_store()
    store.clear()
    monitor = MarketAbuseMonitor(
        window_seconds=120,
        cancel_ratio_threshold=0.5,
        layering_threshold=1,
        min_notional_usd=0.0,
    )
    manager = RiskManager(RiskLimits(), idempotency_store=store, abuse_monitor=monitor)

    ok, reason = manager.validate_order(
        equity_usd=10_000,
        order_value_usd=80,
        leverage=1.0,
        symbol="ETHUSDT",
        side="SELL",
        abuse_context={"cancel_ratio": 0.8, "order_count": 5},
    )
    assert not ok
    assert reason in {"spoofing", "market_abuse_detected"}
