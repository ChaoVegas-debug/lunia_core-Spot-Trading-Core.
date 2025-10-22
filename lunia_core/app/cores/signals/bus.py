"""Simple publish/subscribe bus with Redis fallback."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Awaitable, Callable

try:  # pragma: no cover - optional dependency
    import redis
except Exception:  # pragma: no cover
    redis = None

from .schema import Signal

LOGGER = logging.getLogger(__name__)
Subscriber = Callable[[Signal], Awaitable[None]]


class SignalBus:
    def __init__(self) -> None:
        self._queue: "asyncio.Queue[Signal]" = asyncio.Queue()
        self._redis_url = os.getenv("REDIS_URL")
        self._redis_client = None
        if self._redis_url and redis:
            try:
                self._redis_client = redis.StrictRedis.from_url(self._redis_url)
                self._redis_client.ping()
                LOGGER.info("Signal bus using Redis backend")
            except Exception:  # pragma: no cover - fallback to in-memory
                LOGGER.warning("Redis unavailable, falling back to in-memory bus")
                self._redis_client = None

    async def publish(self, signal: Signal) -> None:
        if self._redis_client:
            payload = json.dumps(signal.__dict__)
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: self._redis_client.publish("cores.signals", payload)
            )
        else:
            await self._queue.put(signal)

    async def subscribe(self, callback: Subscriber) -> None:
        if self._redis_client:
            loop = asyncio.get_running_loop()

            def _consume() -> None:
                pubsub = self._redis_client.pubsub()
                pubsub.subscribe("cores.signals")
                for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    data = json.loads(message["data"])
                    signal = Signal(**data)
                    asyncio.run_coroutine_threadsafe(callback(signal), loop)

            loop.run_in_executor(None, _consume)
        else:
            while True:
                signal = await self._queue.get()
                await callback(signal)


BUS = SignalBus()


__all__ = ["BUS", "SignalBus"]
