"""Idempotency utilities for risk validation."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    import redis  # type: ignore
except Exception:  # pragma: no cover - fallback when redis unavailable
    redis = None  # type: ignore


DEFAULT_TTL_SECONDS = 24 * 60 * 60
_PREFIX = "lunia:idemp:"
_GLOBAL_STORE: "IdempotencyStore | None" = None
_LOCK = threading.Lock()


@dataclass
class IdempotencyRecord:
    """Internal record for fallback storage."""

    expires_at: float


class IdempotencyStore:
    """Persist idempotency keys using Redis when available."""

    def __init__(
        self, url: str | None = None, ttl_seconds: int = DEFAULT_TTL_SECONDS
    ) -> None:
        self.url = url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.ttl_seconds = ttl_seconds
        self._redis: Optional["redis.Redis"] = None
        self._memory_store: Dict[str, IdempotencyRecord] = {}
        self._lock = threading.Lock()
        if redis is not None:
            try:
                self._redis = redis.from_url(
                    self.url, decode_responses=True, socket_timeout=5
                )
            except Exception:
                self._redis = None

    def _namespaced(self, key: str) -> str:
        return f"{_PREFIX}{key}"

    def exists(self, key: str) -> bool:
        if not key:
            return False
        if self._redis is not None:
            try:
                return bool(self._redis.exists(self._namespaced(key)))
            except Exception:
                self._redis = None
        now = time.time()
        with self._lock:
            record = self._memory_store.get(key)
            if record and record.expires_at > now:
                return True
            if record:
                del self._memory_store[key]
        return False

    def store(self, key: str) -> None:
        if not key:
            return
        if self._redis is not None:
            try:
                self._redis.set(self._namespaced(key), "1", ex=self.ttl_seconds)
                return
            except Exception:
                self._redis = None
        expires = time.time() + self.ttl_seconds
        with self._lock:
            self._memory_store[key] = IdempotencyRecord(expires_at=expires)

    def cleanup(self) -> None:
        if self._redis is not None:
            return
        now = time.time()
        with self._lock:
            expired = [
                key
                for key, record in self._memory_store.items()
                if record.expires_at <= now
            ]
            for key in expired:
                del self._memory_store[key]

    def clear(self) -> None:
        """Clear stored keys (primarily for tests)."""
        if self._redis is not None:
            try:
                keys = self._redis.keys(f"{_PREFIX}*")
                if keys:
                    self._redis.delete(*keys)
            except Exception:
                self._redis = None
        with self._lock:
            self._memory_store.clear()


def get_idempotency_store() -> IdempotencyStore:
    global _GLOBAL_STORE
    if _GLOBAL_STORE is None:
        with _LOCK:
            if _GLOBAL_STORE is None:
                _GLOBAL_STORE = IdempotencyStore()
    return _GLOBAL_STORE
