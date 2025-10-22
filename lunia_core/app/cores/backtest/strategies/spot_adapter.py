"""Adapter that reuses spot strategies in a simulated environment."""

from __future__ import annotations

from typing import Iterable, List

from app.core.ai.strategies import REGISTRY


class SpotStrategyAdapter:
    def __init__(self) -> None:
        self.last_trade_count = 0

    def simulate(
        self, strategy_name: str, dataset: Iterable[float], capital: float
    ) -> List[float]:
        prices = list(dataset)
        strategy = REGISTRY.get(strategy_name)
        if not strategy:
            return [capital for _ in prices]
        equity = capital
        curve: List[float] = []
        self.last_trade_count = 0
        for price in prices:
            signal = strategy.generate_signal("BTCUSDT", price=price)
            if signal and signal.side == "BUY":
                equity *= 1.001
                self.last_trade_count += 1
            elif signal and signal.side == "SELL":
                equity *= 0.999
                self.last_trade_count += 1
            curve.append(equity)
        return curve
