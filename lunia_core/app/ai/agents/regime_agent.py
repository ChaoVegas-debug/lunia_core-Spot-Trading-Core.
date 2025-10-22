"""Market regime detection agent for explainability."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, List


@dataclass
class RegimeAssessment:
    score: float
    reason: str
    regime: str
    volatility: float


class RegimeInsightAgent:
    """Derive simple regime classification from price history."""

    def assess(self, asset: str, price_history: Iterable[float]) -> RegimeAssessment:
        prices: List[float] = [float(p) for p in price_history if p is not None]
        if len(prices) < 5:
            return RegimeAssessment(
                score=0.5,
                reason="Недостаточно истории цен — режим считается нейтральным",
                regime="neutral",
                volatility=0.0,
            )

        recent = prices[-5:]
        older = prices[-10:-5] or prices[-5:]
        recent_avg = mean(recent)
        older_avg = mean(older)
        diff = recent_avg - older_avg
        rel_change = diff / older_avg if older_avg else 0.0

        volatility = max(recent) - min(recent)
        if rel_change > 0.01:
            regime = "uptrend"
            score = 0.75 + min(rel_change, 0.05)
            reason = "Цены растут — тенденция положительная"
        elif rel_change < -0.01:
            regime = "downtrend"
            score = 0.25 + max(rel_change, -0.05)
            reason = "Нисходящий тренд — осторожность"
        else:
            regime = "range"
            score = 0.5
            reason = "Флэтовый рынок"

        score = max(0.0, min(score, 1.0))
        return RegimeAssessment(
            score=score,
            reason=reason,
            regime=regime,
            volatility=round(volatility, 6),
        )
