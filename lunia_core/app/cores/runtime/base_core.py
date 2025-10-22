"""Base primitives for cores in the Lunia runtime."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


@dataclass
class CoreMetadata:
    """Basic configuration for a runtime core."""

    name: str
    weight: float = 1.0
    enabled: bool = True
    description: str | None = None
    tags: tuple[str, ...] = ()


@dataclass
class CoreHealth:
    status: str = "unknown"
    details: Dict[str, Any] = field(default_factory=dict)


class BaseCore:
    """Abstract asynchronous core."""

    def __init__(self, metadata: CoreMetadata) -> None:
        self.metadata = metadata
        self._task: Optional[asyncio.Task[None]] = None
        self._stopping = asyncio.Event()
        self.health = CoreHealth(status="initialising")

    # --- lifecycle -----------------------------------------------------
    async def start(self) -> None:  # pragma: no cover - base skeleton
        LOGGER.debug("Core %s start called", self.metadata.name)
        self._stopping.clear()
        self.health.status = "running"

    async def stop(self) -> None:
        LOGGER.debug("Core %s stopping", self.metadata.name)
        self._stopping.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:  # pragma: no cover - expected
                pass
        self.health.status = "stopped"

    async def tick(self) -> None:  # pragma: no cover - to be overridden
        await asyncio.sleep(0)

    async def handle_signal(
        self, signal: Signal
    ) -> None:  # pragma: no cover - optional
        LOGGER.info("Core %s ignoring signal %s", self.metadata.name, signal.type)

    async def health_check(self) -> CoreHealth:
        return self.health

    def describe(self) -> Dict[str, Any]:
        return {
            "name": self.metadata.name,
            "weight": self.metadata.weight,
            "enabled": self.metadata.enabled,
            "status": self.health.status,
            "tags": list(self.metadata.tags),
        }

    # --- scheduling helpers -------------------------------------------
    def schedule(self, loop: asyncio.AbstractEventLoop, interval: float) -> None:
        async def _runner() -> None:
            LOGGER.info("Core %s runner started", self.metadata.name)
            while not self._stopping.is_set():
                try:
                    await self.tick()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - logging only
                    LOGGER.exception(
                        "Core %s tick failure: %s", self.metadata.name, exc
                    )
                    self.health.status = "error"
                await asyncio.sleep(interval)
            LOGGER.info("Core %s runner stopped", self.metadata.name)

        if self._task and not self._task.done():
            raise RuntimeError(f"Core {self.metadata.name} already scheduled")
        self._task = loop.create_task(_runner(), name=f"core:{self.metadata.name}")


__all__ = ["BaseCore", "CoreMetadata", "CoreHealth"]
