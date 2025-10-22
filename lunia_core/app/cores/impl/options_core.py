"""Options core placeholder with simulated strategies."""

from __future__ import annotations

import asyncio
import logging

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


class OptionsCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker

    async def tick(self) -> None:
        await asyncio.sleep(1.5)

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.info("Options core received %s", signal)


__all__ = ["OptionsCore"]
