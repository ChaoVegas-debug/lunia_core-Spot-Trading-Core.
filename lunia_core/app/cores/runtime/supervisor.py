"""Async supervisor that manages core lifecycles."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress
from typing import Dict

from app.self_healing import (ComprehensiveHealthMonitor,
                              IntelligentAutoRecovery)

from ..signals.bus import BUS
from ..signals.rate_limiter import RateLimiter
from ..signals.schema import Signal
from .registry import REGISTRY

LOGGER = logging.getLogger(__name__)


DEFAULT_INTERVALS = {
    "default": 1.0,
    "SPOT": 2.0,
    "HFT": 0.3,
    "FUTURES": 1.0,
    "OPTIONS": 2.5,
    "ARBITRAGE": 2.0,
    "DEFI": 5.0,
    "LLM": 5.0,
}


class CoreSupervisor:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._task: asyncio.Task[None] | None = None
        self._rate_limiter = RateLimiter(capacity=30, refill_rate=0.5)

    async def start(self, intervals: Dict[str, float] | None = None) -> None:
        if self._task and not self._task.done():
            return
        self._loop = asyncio.get_event_loop()
        await REGISTRY.ensure_started(self._loop, intervals or DEFAULT_INTERVALS)
        self._task = self._loop.create_task(self._signal_consumer())
        LOGGER.info("Core supervisor started")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
        await REGISTRY.stop_all()
        LOGGER.info("Core supervisor stopped")

    async def _signal_consumer(self) -> None:
        async def _consume(signal: Signal) -> None:
            if not await self._rate_limiter.acquire():
                LOGGER.warning("Dropping signal due to rate limiting: %s", signal)
                return
            await REGISTRY.dispatch(signal)

        await BUS.subscribe(_consume)

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        return REGISTRY.snapshot()


class EnhancedCoreSupervisor(CoreSupervisor):
    def __init__(self) -> None:
        super().__init__()
        self._health_monitor: ComprehensiveHealthMonitor | None = None
        self._health_task: asyncio.Task[None] | None = None
        self._auto_recovery = IntelligentAutoRecovery()

    async def start(self, intervals: Dict[str, float] | None = None) -> None:
        await super().start(intervals)
        if self._health_task is None and self._self_healing_enabled():
            self._health_monitor = ComprehensiveHealthMonitor()
            loop = asyncio.get_event_loop()
            self._health_task = loop.create_task(self._health_loop())
            LOGGER.info("Health monitoring loop started")

    async def stop(self) -> None:
        if self._health_task:
            self._health_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._health_task
            self._health_task = None
        await super().stop()

    async def _health_loop(self) -> None:
        assert self._health_monitor is not None
        interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))
        while True:
            try:
                report = await self._health_monitor.perform_health_check()
                if report.has_critical_issues():
                    await self._auto_recovery.execute_recovery(
                        "auto", {"report": report.to_dict()}
                    )
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive
                LOGGER.exception("Health monitoring loop error: %s", exc)
                await asyncio.sleep(300)

    def _self_healing_enabled(self) -> bool:
        return os.getenv("SELF_HEALING_ENABLED", "true").lower() == "true"


SUPERVISOR = EnhancedCoreSupervisor()


__all__ = [
    "SUPERVISOR",
    "CoreSupervisor",
    "EnhancedCoreSupervisor",
    "DEFAULT_INTERVALS",
]
