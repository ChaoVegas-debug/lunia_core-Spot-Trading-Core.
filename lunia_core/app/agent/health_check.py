"""Basic health checker used by the updater."""

from __future__ import annotations

from typing import Dict

from app.self_healing.health_monitor import ComprehensiveHealthMonitor


class HealthChecker:
    def __init__(self) -> None:
        self.monitor = ComprehensiveHealthMonitor()

    async def check(self) -> Dict[str, object]:
        report = await self.monitor.perform_health_check()
        return report.to_dict()
