"""Tests for canary execution and transaction cost analytics."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.capital.allocator import CapitalAllocator
from app.core.risk.manager import RiskLimits, RiskManager
from app.monitoring.abuse_detector import MarketAbuseMonitor
from app.risk.idempotency import IdempotencyStore
from app.strategies.live.canary import CanaryExecutionManager
from app.strategies.live.execution import LiveExecutionEngine
from app.strategies.live.shadow import ShadowTradingEngine
from app.strategies.live.tca import TCAAnalyzer


@pytest.fixture()
def risk_manager() -> RiskManager:
    monitor = MarketAbuseMonitor()
    monitor.disable()
    store = IdempotencyStore(ttl_seconds=60)
    store.clear()
    manager = RiskManager(
        limits=RiskLimits(
            max_daily_loss_pct=10.0,
            max_pos_leverage=5.0,
            max_symbol_risk_pct=50.0,
            max_symbol_exposure_pct=80.0,
        ),
        idempotency_store=store,
        abuse_monitor=monitor,
    )
    return manager


@pytest.fixture()
def allocator() -> CapitalAllocator:
    return CapitalAllocator(
        max_trade_pct=0.2,
        risk_per_trade_pct=0.02,
        max_symbol_exposure_pct=50.0,
        max_positions=5,
    )


def test_shadow_execution(
    tmp_path: Path, risk_manager: RiskManager, allocator: CapitalAllocator
) -> None:
    canary = CanaryExecutionManager(
        slo_trades=2, latency_threshold_ms=500.0, drawdown_limit_usd=500.0
    )
    shadow = ShadowTradingEngine(enabled=True)
    engine = LiveExecutionEngine(
        risk_manager=risk_manager,
        allocator=allocator,
        canary=canary,
        shadow=shadow,
        orders_log_path=tmp_path / "orders.jsonl",
        pnl_rollback_limit=1_000.0,
    )

    result = engine.execute_signal(
        strategy="micro_trend_scalper",
        symbol="BTCUSDT",
        side="BUY",
        price=25_000.0,
        qty=0.01,
        equity=50_000.0,
        weights={"micro_trend_scalper": 1.0},
        reserves={"portfolio": 0.1},
        cap_pct=0.5,
        stop_pct=0.02,
        leverage=1.0,
        symbol_limits={"fee_pct": 0.05},
        adapter_config={"exchange": "bybit"},
        idempotency_key="test-shadow",
    )

    assert result["status"] in {"FILLED", "OK"}
    assert result["shadow"] is True
    assert (tmp_path / "orders.jsonl").exists()
    lines = (tmp_path / "orders.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1


def test_canary_promotion_and_rollback() -> None:
    canary = CanaryExecutionManager(
        slo_trades=2, latency_threshold_ms=100.0, drawdown_limit_usd=10.0
    )
    base_notional = 1_000.0
    assert canary.scale_notional(base_notional) == pytest.approx(base_notional * 0.05)

    canary.record_result(pnl=5.0, latency_ms=50.0, success=True)
    canary.record_result(pnl=6.0, latency_ms=60.0, success=True)
    assert canary.is_production
    assert canary.scale_notional(base_notional) == pytest.approx(base_notional)

    canary.record_result(pnl=-20.0, latency_ms=200.0, success=False)
    assert canary.is_shadow
    assert canary.scale_notional(base_notional) == pytest.approx(base_notional * 0.05)


def test_tca_metrics() -> None:
    analyzer = TCAAnalyzer()
    metrics = analyzer.evaluate(
        expected_price=100.0,
        fill_price=101.0,
        qty=2.0,
        fees=1.0,
        latency_ms=45.0,
    )
    assert metrics.slippage_bp == pytest.approx(100.0)
    assert metrics.effective_cost_usd == pytest.approx(3.0)
    assert metrics.net_pnl == pytest.approx(-3.0)
