"""Spot trading core built on top of existing agent infrastructure."""

from __future__ import annotations

import asyncio
import logging
from typing import List

from app.core.ai.agent import Agent
from app.core.ai.strategies import REGISTRY, StrategySignal
from app.core.ai.supervisor import Supervisor
from app.core.exchange.binance_spot import BinanceSpot
from app.core.risk.manager import RiskManager

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)


class SpotCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker
        self._agent = Agent(
            client=BinanceSpot(
                mock=True
            ),  # defaults to mock, real keys loaded by agent
            risk=RiskManager(),
            supervisor=Supervisor(client=BinanceSpot(mock=True)),
        )
        self._strategies = [name for name in REGISTRY.keys()]

    async def start(self) -> None:
        await super().start()
        LOGGER.info("Spot core started with %d strategies", len(self._strategies))

    async def tick(self) -> None:
        signals: List[StrategySignal] = []
        for name in self._strategies:
            strategy = REGISTRY[name]
            try:
                signal = strategy.generate()
            except Exception:  # pragma: no cover - strategy errors already logged
                LOGGER.exception("Strategy %s failed", name)
                continue
            if signal:
                signals.append(signal)
        for sig in signals:
            await self._process_signal(sig)
        await asyncio.sleep(0)

    async def _process_signal(self, strategy_signal: StrategySignal) -> None:
        if strategy_signal is None:
            return
        LOGGER.info("SpotCore executing %s", strategy_signal.symbol)
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._agent.place_spot_order(
                    symbol=strategy_signal.symbol,
                    side=strategy_signal.side,
                    qty=strategy_signal.qty,
                    price=strategy_signal.price,
                ),
            )
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Spot order failed: %s", exc)

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.info("Spot core received signal %s", signal)
        self.metadata.tags = tuple(sorted(set(self.metadata.tags + (signal.type,))))


__all__ = ["SpotCore"]
