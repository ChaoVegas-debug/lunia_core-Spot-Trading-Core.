"""Tiny in-memory cache for LLM responses."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class LLMCache:
    def __init__(self, ttl: int = 300) -> None:
        self.ttl = ttl
        self._store: Dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store:
            expires, value = self._store[key]
            if expires > time.time():
                return value
            self._store.pop(key, None)
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (time.time() + self.ttl, value)

    def clear(self) -> None:
        self._store.clear()
