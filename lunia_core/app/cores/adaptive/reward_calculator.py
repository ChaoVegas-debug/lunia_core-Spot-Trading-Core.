"""Reward calculation helper."""

from __future__ import annotations

from typing import Dict


class RewardCalculator:
    def calculate(self, performance: Dict[str, float]) -> float:
        pnl = float(performance.get("pnl", 0.0))
        win_rate = float(performance.get("win_rate", 0.0))
        drawdown = float(performance.get("max_drawdown", 0.0))
        reward = pnl + 0.5 * win_rate - drawdown
        return reward
