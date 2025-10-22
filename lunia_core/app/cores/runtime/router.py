"""In-process router for signals between cores."""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, Dict, List

from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)

Handler = Callable[[Signal], Awaitable[None]]


class SignalRouter:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Handler]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, core_name: str, handler: Handler) -> None:
        async with self._lock:
            self._handlers.setdefault(core_name, []).append(handler)
            LOGGER.debug("Subscribed handler for %s", core_name)

    async def publish(self, signal: Signal) -> None:
        async with self._lock:
            handlers = list(self._handlers.get(signal.target_core, []))
        if not handlers:
            LOGGER.debug("No handlers registered for %s", signal.target_core)
            return
        await asyncio.gather(*(handler(signal) for handler in handlers))


ROUTER = SignalRouter()


__all__ = ["ROUTER", "SignalRouter"]
