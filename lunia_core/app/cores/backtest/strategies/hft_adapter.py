"""Extremely simple HFT adapter that emulates micro scalping."""

from __future__ import annotations

from typing import Iterable, List


class HFTStrategyAdapter:
    def __init__(self) -> None:
        self.last_trade_count = 0

    def simulate(
        self, strategy_name: str, dataset: Iterable[float], capital: float
    ) -> List[float]:
        equity = capital
        curve: List[float] = []
        self.last_trade_count = 0
        for idx, _ in enumerate(dataset):
            equity *= 1.0002 if idx % 2 == 0 else 0.9998
            self.last_trade_count += 1
            curve.append(equity)
        return curve
