"""Utility metrics for backtests."""

from __future__ import annotations

import math
from typing import Dict, Iterable, List


class BacktestMetrics:
    @staticmethod
    def compute(equity_curve: Iterable[float]) -> Dict[str, float]:
        values = list(equity_curve)
        if not values:
            return {"sharpe_ratio": 0.0, "max_drawdown": 0.0, "cagr": 0.0}
        returns = [0.0]
        for i in range(1, len(values)):
            prev = values[i - 1] or 1.0
            returns.append((values[i] - prev) / prev)
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / max(
            len(returns) - 1, 1
        )
        std_dev = math.sqrt(max(variance, 1e-9))
        sharpe = avg_return / std_dev if std_dev else 0.0
        max_drawdown = BacktestMetrics._max_drawdown(values)
        cagr = (values[-1] / max(values[0], 1.0)) ** (1 / max(len(values), 1)) - 1
        return {
            "sharpe_ratio": round(sharpe, 4),
            "max_drawdown": round(max_drawdown, 4),
            "cagr": round(cagr, 4),
        }

    @staticmethod
    def _max_drawdown(values: List[float]) -> float:
        peak = values[0]
        drawdown = 0.0
        for value in values:
            if value > peak:
                peak = value
            drawdown = min(drawdown, (value - peak) / peak if peak else 0.0)
        return abs(drawdown)
