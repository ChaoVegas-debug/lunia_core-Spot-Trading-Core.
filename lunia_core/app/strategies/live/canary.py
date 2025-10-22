"""Canary execution helpers."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass
class CanaryState:
    mode: str = "canary"  # canary | production | shadow
    success_count: int = 0
    failure_count: int = 0
    cumulative_pnl: float = 0.0
    recent_latency: Deque[float] = field(default_factory=lambda: deque(maxlen=20))
    rollback_reason: str | None = None


class CanaryExecutionManager:
    """Manage staged rollout of live orders."""

    def __init__(
        self,
        *,
        initial_fraction: float = 0.05,
        slo_trades: int = 10,
        latency_threshold_ms: float = 1500.0,
        drawdown_limit_usd: float = 50.0,
    ) -> None:
        self.initial_fraction = max(0.0, min(1.0, initial_fraction)) or 0.05
        self.slo_trades = max(1, int(slo_trades))
        self.latency_threshold_ms = max(1.0, float(latency_threshold_ms))
        self.drawdown_limit_usd = float(drawdown_limit_usd)
        self.state = CanaryState()

    @property
    def is_shadow(self) -> bool:
        return self.state.mode == "shadow"

    @property
    def is_production(self) -> bool:
        return self.state.mode == "production"

    def set_shadow(self) -> None:
        self.state = CanaryState(mode="shadow")

    def scale_notional(self, notional: float) -> float:
        if notional <= 0:
            return 0.0
        if self.state.mode == "production":
            return notional
        return notional * self.initial_fraction

    def record_result(self, *, pnl: float, latency_ms: float, success: bool) -> None:
        self.state.recent_latency.append(float(latency_ms))
        self.state.cumulative_pnl += float(pnl)
        if success:
            self.state.success_count += 1
        else:
            self.state.failure_count += 1
        if self.state.cumulative_pnl <= -abs(self.drawdown_limit_usd):
            self.trigger_rollback("drawdown_limit")
            return
        if any(lat > self.latency_threshold_ms for lat in self.state.recent_latency):
            self.trigger_rollback("latency_limit")
            return
        if (
            self.state.mode != "production"
            and self.state.success_count >= self.slo_trades
        ):
            avg_latency = sum(self.state.recent_latency) / max(
                1, len(self.state.recent_latency)
            )
            if (
                avg_latency <= self.latency_threshold_ms
                and self.state.cumulative_pnl >= 0
            ):
                self.state.mode = "production"

    def trigger_rollback(self, reason: str) -> None:
        self.state = CanaryState(mode="shadow", rollback_reason=reason)
        self.state.failure_count = 1

    def reset(self) -> None:
        self.state = CanaryState()
