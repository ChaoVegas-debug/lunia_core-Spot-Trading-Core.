"""Health monitoring utilities for Lunia cores."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import socket
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.logging.slo import SLOMonitor
from app.services.resilience import (engage_llm_fallback, enter_read_only_mode,
                                     promote_backup_exchange)

from .types import HealthIssue, HealthReport

LOGGER = logging.getLogger(__name__)
DEFAULT_COMPONENTS: Iterable[str] = (
    "api",
    "cores",
    "redis",
    "telemetry",
)


class ComprehensiveHealthMonitor:
    """Runs lightweight health checks and reports aggregated state."""

    def __init__(self, components: Iterable[str] | None = None) -> None:
        self.components = tuple(components or DEFAULT_COMPONENTS)
        self._previous_report: HealthReport | None = None
        self._prod_mode = os.getenv("INFRA_PROD_ENABLED", "false").lower() == "true"
        self._slo_monitor = SLOMonitor()

    async def perform_health_check(self) -> HealthReport:
        """Gather basic system metrics and detect anomalies."""

        timestamp = time.time()
        issues: List[HealthIssue] = []
        metrics: Dict[str, Any] = {
            "uptime_seconds": int(timestamp - ps_start_time()),
            "disk_free_mb": self._safe_disk_free_mb(),
            "load_avg": self._load_average(),
        }

        if not await self.check_api_connectivity():
            issues.append(
                HealthIssue(
                    component="api",
                    severity="critical",
                    description="FastAPI/Flask API is not responding",
                )
            )

        if not await self.check_core_heartbeats():
            issues.append(
                HealthIssue(
                    component="cores",
                    severity="warning",
                    description="One or more cores did not publish heartbeats",
                )
            )

        if metrics["disk_free_mb"] < 128:
            issues.append(
                HealthIssue(
                    component="storage",
                    severity="critical",
                    description="Low disk space",
                    details={"free_mb": metrics["disk_free_mb"]},
                )
            )

        if self._prod_mode:
            if not await self.check_exchange_connectivity():
                promote_backup_exchange(
                    "binance",
                    os.getenv("EXCHANGE_FAILOVER", "okx"),
                    "health_check_exchange",
                )
                issues.append(
                    HealthIssue(
                        component="exchange",
                        severity="critical",
                        description="Primary exchange unreachable, failover engaged",
                        details={"fallback": os.getenv("EXCHANGE_FAILOVER", "okx")},
                    )
                )

            if not await self.check_redis_resilience():
                enter_read_only_mode("redis health degraded")
                issues.append(
                    HealthIssue(
                        component="redis",
                        severity="critical",
                        description="Redis unavailable, read-only mode enabled",
                    )
                )

            if not await self.check_llm_budget():
                engage_llm_fallback("health_monitor")
                issues.append(
                    HealthIssue(
                        component="llm",
                        severity="warning",
                        description="LLM rate limit detected, switching to rule-based decisions",
                    )
                )

            slo_ok, slo_details = self._slo_monitor.evaluate(metrics)
            if not slo_ok:
                issues.append(
                    HealthIssue(
                        component="slo",
                        severity="warning",
                        description="SLO threshold breached",
                        details=slo_details,
                    )
                )

        report = HealthReport(
            timestamp=datetime.fromtimestamp(timestamp), issues=issues, metrics=metrics
        )
        self._previous_report = report
        LOGGER.debug("Health report generated: %s", json.dumps(report.to_dict()))
        return report

    async def check_api_connectivity(self) -> bool:
        host = os.getenv("HOST", "127.0.0.1")
        port = int(os.getenv("PORT", "8000"))
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=1.5
            )
        except Exception:
            return False
        else:
            writer.close()
            await writer.wait_closed()
            return True

    async def check_core_heartbeats(self) -> bool:
        """Placeholder heartbeat check: look for snapshot file updated recently."""

        snapshot_path = (
            Path(os.getenv("LUNIA_RUNTIME_DIR", "."))
            / "logs"
            / "cores"
            / "snapshot.json"
        )
        if not snapshot_path.exists():
            return True
        try:
            mtime = snapshot_path.stat().st_mtime
        except OSError:
            return False
        return (time.time() - mtime) < 180

    async def check_memory_usage(self) -> float:
        return float(os.getenv("MEMORY_USAGE_MB", "0"))

    async def check_latency_metrics(self) -> float:
        return float(os.getenv("AVG_LATENCY_MS", "0"))

    async def check_disk_space(self) -> float:
        return self._safe_disk_free_mb()

    async def check_network_connections(self) -> bool:
        try:
            socket.gethostbyname("api")
            return True
        except socket.error:
            return False

    async def check_redis_resilience(self) -> bool:
        status = os.getenv("REDIS_STATUS", "ok").lower()
        return status == "ok"

    async def check_llm_budget(self) -> bool:
        if os.getenv("LLM_RATE_LIMITED", "false").lower() == "true":
            return False
        return True

    async def trigger_immediate_recovery(self) -> None:
        LOGGER.warning("Immediate recovery requested by monitor")

    async def trigger_preventive_measures(self) -> None:
        LOGGER.info("Preventive measures triggered (placeholder)")

    def _safe_disk_free_mb(self) -> float:
        total, used, free = shutil.disk_usage(Path.cwd())
        return free / (1024 * 1024)

    def _load_average(self) -> Dict[str, float]:
        try:
            one, five, fifteen = os.getloadavg()
        except OSError:
            one = five = fifteen = 0.0
        return {"1m": round(one, 2), "5m": round(five, 2), "15m": round(fifteen, 2)}


def ps_start_time() -> float:
    """Return the process start timestamp as best-effort."""

    try:
        with open("/proc/self/stat", "r", encoding="utf-8") as handle:
            data = handle.read().split()
        # field 22 contains starttime in clock ticks
        clock_ticks = os.sysconf(os.sysconf_names["SC_CLK_TCK"])
        start_time_ticks = float(data[21])
        boot_time = 0.0
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("btime "):
                    boot_time = float(line.split()[1])
                    break
        return boot_time + start_time_ticks / clock_ticks
    except Exception:
        return time.time()
