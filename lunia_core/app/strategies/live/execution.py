"""Execution engine for live strategies with safety controls."""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping

from app.core.capital.allocator import CapitalAllocator
from app.core.risk.manager import RiskManager
from app.strategies.adapters import (BybitProxyAdapter, KrakenProxyAdapter,
                                     OKXProxyAdapter)

from .canary import CanaryExecutionManager
from .shadow import ShadowTradingEngine
from .tca import TCAAnalyzer

logger = logging.getLogger(__name__)


class LiveExecutionEngine:
    """Coordinate live execution flows with shadow, canary and TCA controls."""

    def __init__(
        self,
        *,
        risk_manager: RiskManager,
        allocator: CapitalAllocator,
        canary: CanaryExecutionManager | None = None,
        shadow: ShadowTradingEngine | None = None,
        tca: TCAAnalyzer | None = None,
        orders_log_path: Path | None = None,
        pnl_rollback_limit: float = 100.0,
        latency_rollback_ms: float = 2_000.0,
    ) -> None:
        self.risk_manager = risk_manager
        self.allocator = allocator
        self.canary = canary or CanaryExecutionManager()
        self.shadow = shadow or ShadowTradingEngine()
        self.tca = tca or TCAAnalyzer()
        self.pnl_rollback_limit = abs(pnl_rollback_limit)
        self.latency_rollback_ms = latency_rollback_ms
        default_log_root = Path(__file__).resolve().parents[4] / "logs"
        self._orders_log = orders_log_path or default_log_root / "orders.jsonl"
        self._orders_log.parent.mkdir(parents=True, exist_ok=True)
        self._seen_orders: set[str] = set()

    def execute_signal(
        self,
        *,
        strategy: str,
        symbol: str,
        side: str,
        price: float,
        qty: float,
        equity: float,
        weights: Mapping[str, float],
        reserves: Mapping[str, float],
        cap_pct: float,
        stop_pct: float,
        leverage: float,
        symbol_limits: Mapping[str, float],
        adapter_config: Mapping[str, Any],
        idempotency_key: str | None = None,
        shadow_override: bool | None = None,
    ) -> Dict[str, Any]:
        budget = self.allocator.compute_budgets(
            equity=equity,
            cap_pct=cap_pct,
            reserves=reserves,
            weights=weights,
        )
        strategy_budget = budget.per_strategy.get(strategy, 0.0)
        risk_size = self.allocator.risk_size(
            equity=budget.tradable_equity, stop_pct=stop_pct
        )
        notional = min(strategy_budget, risk_size)
        notional = max(notional, 0.0)
        if notional == 0:
            return {"status": "SKIPPED", "reason": "no_budget"}

        scaled_notional = self.canary.scale_notional(notional)
        effective_price = max(price, 1e-9)
        qty_to_trade = qty if qty > 0 else scaled_notional / effective_price
        logger.info(
            "Executing strategy=%s symbol=%s side=%s notional=%.2f shadow=%s",
            strategy,
            symbol,
            side,
            scaled_notional,
            shadow_override if shadow_override is not None else self.shadow.enabled,
        )

        ok, reason = self.risk_manager.validate_order(
            equity_usd=float(equity),
            order_value_usd=float(scaled_notional),
            leverage=float(leverage),
            idempotency_key=idempotency_key,
            abuse_context={"strategy": strategy},
            symbol=symbol,
            side=side,
        )
        if not ok:
            return {"status": "REJECTED", "reason": reason}

        adapter = self._build_adapter(adapter_config)
        trade_id = uuid.uuid4().hex
        metadata: Dict[str, Any] = {"order_id": trade_id, "strategy": strategy}
        should_shadow = (
            shadow_override if shadow_override is not None else self.shadow.enabled
        )

        if should_shadow:
            trade = self.shadow.simulate_order(
                symbol=symbol,
                side=side,
                qty=qty_to_trade,
                price=effective_price,
                metadata=metadata,
            )
            fill_price = effective_price
            status = trade.status
            latency_ms = trade.latency_ms
        else:
            payload = {
                "symbol": symbol,
                "side": side,
                "qty": qty_to_trade,
                "price": effective_price,
            }
            response = adapter.place_order(**payload)
            status = response.status
            latency_ms = 0.0
            fill_price = effective_price

        fees = symbol_limits.get("fee_pct", 0.0) * scaled_notional / 100.0
        metrics = self.tca.evaluate(
            expected_price=price,
            fill_price=fill_price,
            qty=qty_to_trade,
            fees=fees,
            latency_ms=latency_ms,
        )
        self.risk_manager.register_pnl(metrics.net_pnl)
        self.canary.record_result(
            pnl=metrics.net_pnl,
            latency_ms=metrics.latency_ms,
            success=status == "FILLED" or status == "OK",
        )

        if (
            metrics.net_pnl <= -self.pnl_rollback_limit
            or metrics.latency_ms > self.latency_rollback_ms
        ):
            self.canary.trigger_rollback("slo_breach")
            self.shadow.enable()
            logger.warning(
                "Triggered rollback due to slo breach pnl=%.2f latency=%.2f",
                metrics.net_pnl,
                metrics.latency_ms,
            )

        record = {
            "order_id": trade_id,
            "timestamp": time.time(),
            "symbol": symbol,
            "side": side,
            "qty": qty_to_trade,
            "price": fill_price,
            "notional": scaled_notional,
            "strategy": strategy,
            "status": status,
            "shadow": should_shadow,
            "tca": asdict(metrics),
        }
        self._write_order(record)

        return {
            "status": status,
            "order_id": trade_id,
            "shadow": should_shadow,
            "notional": scaled_notional,
            "canary_mode": self.canary.state.mode,
            "tca": asdict(metrics),
        }

    def _write_order(self, record: MutableMapping[str, Any]) -> None:
        order_id = str(record.get("order_id"))
        if order_id in self._seen_orders:
            return
        self._seen_orders.add(order_id)
        with self._orders_log.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record) + "\n")

    @staticmethod
    def _build_adapter(
        config: Mapping[str, Any],
    ) -> BybitProxyAdapter | OKXProxyAdapter | KrakenProxyAdapter:
        exchange = str(config.get("exchange", "bybit")).lower()
        base_url = str(config.get("base_url", "https://proxy.example.com"))
        api_key = str(config.get("api_key", ""))
        api_secret = str(config.get("api_secret", ""))
        if exchange == "okx":
            return OKXProxyAdapter(
                base_url=base_url, api_key=api_key, api_secret=api_secret
            )
        if exchange == "kraken":
            return KrakenProxyAdapter(
                base_url=base_url, api_key=api_key, api_secret=api_secret
            )
        return BybitProxyAdapter(
            base_url=base_url, api_key=api_key, api_secret=api_secret
        )
