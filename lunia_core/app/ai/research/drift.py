"""Model drift monitoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from app.ai.research.versioning import VersionTracker


@dataclass
class DriftSample:
    metric_name: str
    baseline: float
    current: float
    context: Dict[str, str] | None = None


class DriftMonitor:
    """Monitors for changes in model metrics and emits alerts via VersionTracker."""

    def __init__(self, tracker: VersionTracker | None = None) -> None:
        self.tracker = tracker or VersionTracker()

    def process(self, samples: Iterable[DriftSample]) -> None:
        for sample in samples:
            self.tracker.check_drift(
                metric_name=sample.metric_name,
                baseline=sample.baseline,
                current=sample.current,
                context=sample.context,
            )
