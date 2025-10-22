"""SLO monitoring helpers for automated remediation."""

from __future__ import annotations

import logging
import os
from typing import Dict, Tuple

LOGGER = logging.getLogger(__name__)


class SLOMonitor:
    """Evaluates latency and error SLOs based on lightweight metrics."""

    def __init__(self) -> None:
        self.latency_ms = float(os.getenv("SLO_LATENCY_THRESHOLD_MS", "500"))
        self.error_budget = float(os.getenv("SLO_ERROR_RATE", "0.01"))

    def evaluate(self, metrics: Dict[str, object]) -> Tuple[bool, Dict[str, float]]:
        """Return whether SLOs are respected along with diagnostic details."""

        latency = float(
            metrics.get("avg_request_latency_ms", os.getenv("AVG_LATENCY_MS", "0"))
        )
        error_rate = float(metrics.get("error_rate", os.getenv("ERROR_RATE", "0")))
        within_latency = latency <= self.latency_ms
        within_errors = error_rate <= self.error_budget
        healthy = within_latency and within_errors
        details = {
            "latency_ms": round(latency, 2),
            "latency_budget_ms": self.latency_ms,
            "error_rate": round(error_rate, 4),
            "error_budget": self.error_budget,
        }
        if not healthy:
            LOGGER.warning("SLO breach detected: %s", details)
        return healthy, details
