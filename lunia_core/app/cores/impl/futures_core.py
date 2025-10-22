"""Futures trading core leveraging Binance futures client."""

from __future__ import annotations

import asyncio
import logging

from app.core.exchange.binance_futures import BinanceFutures
from app.core.risk.manager import RiskManager

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


class FuturesCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker
        self.client = BinanceFutures(mock=True)
        self.risk = RiskManager()

    async def tick(self) -> None:
        await asyncio.sleep(0.5)

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.info("Futures core received %s", signal)


__all__ = ["FuturesCore"]
