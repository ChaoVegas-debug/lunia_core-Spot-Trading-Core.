"""Arbitrage core integrating existing arbitrage engine."""

from __future__ import annotations

import asyncio
import logging

from app.core.arbitrage.engine import ArbitrageEngine

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


class ArbitrageCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker
        self.engine = ArbitrageEngine()

    async def tick(self) -> None:
        await asyncio.get_event_loop().run_in_executor(None, self.engine.scan)

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.debug("Arbitrage core got signal %s", signal)


__all__ = ["ArbitrageCore"]
