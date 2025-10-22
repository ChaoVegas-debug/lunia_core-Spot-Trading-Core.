"""Simplified high-frequency trading core."""

from __future__ import annotations

import asyncio
import logging
import random

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


class HFTCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker
        self.health.details["latency_ms"] = 0.0

    async def tick(self) -> None:
        latency = random.uniform(1, 4)
        self.health.details["latency_ms"] = latency
        await asyncio.sleep(0.05)

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.debug("HFT core received %s", signal)


__all__ = ["HFTCore"]
