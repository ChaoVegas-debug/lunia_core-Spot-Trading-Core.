"""Transaction cost analysis helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TCAMetrics:
    slippage_bp: float
    effective_cost_usd: float
    fees_usd: float
    latency_ms: float
    implementation_shortfall: float
    net_pnl: float


class TCAAnalyzer:
    """Compute transaction cost analytics for executions."""

    def evaluate(
        self,
        *,
        expected_price: float,
        fill_price: float,
        qty: float,
        fees: float,
        latency_ms: float,
    ) -> TCAMetrics:
        qty = max(0.0, float(qty))
        expected_price = float(expected_price)
        fill_price = float(fill_price)
        fees = float(fees)
        latency_ms = float(latency_ms)

        notional_expected = expected_price * qty
        notional_fill = fill_price * qty
        slippage = notional_fill - notional_expected
        slippage_bp = 0.0
        if expected_price:
            slippage_bp = (fill_price - expected_price) / expected_price * 10_000.0
        implementation_shortfall = slippage + fees
        effective_cost = implementation_shortfall
        net_pnl = -effective_cost
        return TCAMetrics(
            slippage_bp=slippage_bp,
            effective_cost_usd=effective_cost,
            fees_usd=fees,
            latency_ms=latency_ms,
            implementation_shortfall=implementation_shortfall,
            net_pnl=net_pnl,
        )
