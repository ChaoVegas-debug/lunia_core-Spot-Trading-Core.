"""Simplified futures adapter for backtests."""

from __future__ import annotations

from typing import Iterable, List


class FuturesStrategyAdapter:
    def __init__(self) -> None:
        self.last_trade_count = 0

    def simulate(
        self, strategy_name: str, dataset: Iterable[float], capital: float
    ) -> List[float]:
        prices = list(dataset)
        equity = capital
        self.last_trade_count = 0
        curve: List[float] = []
        for idx, price in enumerate(prices):
            if idx % 5 == 0:
                equity *= 1.002
                self.last_trade_count += 1
            elif idx % 7 == 0:
                equity *= 0.998
                self.last_trade_count += 1
            curve.append(equity)
        return curve
