"""Sentiment insight agent providing qualitative market view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ...services.ai_research.worker import (get_priority_scores,
                                            run_research_now)


@dataclass
class SentimentAssessment:
    score: float
    reason: str
    source: str
    signals: List[Dict[str, object]]


class SentimentInsightAgent:
    """Evaluate sentiment based on research worker output."""

    def assess(self, asset: str) -> SentimentAssessment:
        asset = asset.upper()
        cached = get_priority_scores()
        if asset in cached:
            confidence = max(0.0, min(float(cached[asset]), 1.0))
            return SentimentAssessment(
                score=confidence,
                reason=f"Приоритет из AI-исследования: {confidence:.2f}",
                source="cached",
                signals=[],
            )

        results = run_research_now([asset], mode="manual")
        if results:
            result = results[0]
            confidence = max(0.0, min(float(result.get("confidence", 0.6)), 1.0))
            comment = str(result.get("comment", "")) or "Сигналы исследователя"
            return SentimentAssessment(
                score=confidence,
                reason=comment,
                source="research",
                signals=[result],
            )

        return SentimentAssessment(
            score=0.5,
            reason="Данных от исследователя нет — нейтральное мнение",
            source="missing",
            signals=[],
        )
