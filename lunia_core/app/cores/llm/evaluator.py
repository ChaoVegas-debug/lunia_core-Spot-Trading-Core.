"""Evaluate LLM provider performance."""

from __future__ import annotations

from typing import Dict, Iterable


class ModelEvaluator:
    def evaluate(self, history: Iterable[Dict[str, float]]) -> Dict[str, float]:
        stats: Dict[str, float] = {"accuracy": 0.0, "latency_ms": 0.0}
        count = 0
        for row in history:
            count += 1
            stats["accuracy"] += float(row.get("accuracy", 0.0))
            stats["latency_ms"] += float(row.get("latency_ms", 0.0))
        if count:
            stats = {key: value / count for key, value in stats.items()}
        return stats
