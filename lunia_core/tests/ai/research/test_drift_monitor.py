from __future__ import annotations

from app.ai.research.drift import DriftMonitor, DriftSample


class DummyTracker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, float, float]] = []

    def check_drift(
        self, metric_name: str, baseline: float, current: float, context=None
    ) -> None:
        self.calls.append((metric_name, baseline, current))


def test_drift_monitor_invokes_tracker():
    tracker = DummyTracker()
    monitor = DriftMonitor(tracker=tracker)  # type: ignore[arg-type]
    monitor.process([DriftSample(metric_name="sharpe", baseline=1.0, current=0.7)])
    assert tracker.calls == [("sharpe", 1.0, 0.7)]
