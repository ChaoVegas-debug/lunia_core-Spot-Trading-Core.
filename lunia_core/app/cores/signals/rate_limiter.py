"""Simple token bucket rate limiter for signals."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass


@dataclass
class RateLimiter:
    capacity: int
    refill_rate: float

    def __post_init__(self) -> None:
        self._tokens = float(self.capacity)
        self._updated_at = time.time()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            now = time.time()
            delta = now - self._updated_at
            self._updated_at = now
            self._tokens = min(self.capacity, self._tokens + delta * self.refill_rate)
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False
