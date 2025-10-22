"""Pytest configuration and fixtures for Lunia core tests."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import types
from pathlib import Path
from typing import Dict, Generator

import pytest

fakeredis_available = True
try:  # pragma: no cover - optional dependency
    import fakeredis  # type: ignore
except Exception:  # pragma: no cover - offline fallback
    fakeredis = None  # type: ignore
    fakeredis_available = False


class InMemoryRedis:
    """Minimal Redis-compatible stub for offline test environments."""

    def __init__(self) -> None:
        self._kv: Dict[str, str] = {}

    def ping(self) -> bool:  # pragma: no cover - trivial
        return True

    def get(self, key: str):  # type: ignore[no-untyped-def]
        return self._kv.get(key)

    def set(self, key: str, value):  # type: ignore[no-untyped-def]
        self._kv[key] = value
        return True

    def publish(self, channel: str, message):  # type: ignore[no-untyped-def]
        return 1


def _redis_client():  # type: ignore[no-untyped-def]
    if fakeredis is not None:
        return fakeredis.FakeStrictRedis()
    return InMemoryRedis()


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def pytest_configure(config: pytest.Config) -> None:  # pragma: no cover - pytest hook
    """Register custom markers used across the test-suite."""

    config.addinivalue_line("markers", "requires_flask: marks tests that need Flask")
    config.addinivalue_line("markers", "integration: integration level tests")
    config.addinivalue_line("markers", "unit: unit level tests")


@pytest.fixture()
def temp_db(monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Provide a temporary sqlite database for quote detector tests."""

    from app.core.utils import quote_detector

    with tempfile.NamedTemporaryFile(suffix=".db", delete=True) as handle:
        db_path = Path(handle.name)
        monkeypatch.setattr(quote_detector, "_DB_PATH", db_path)
        monkeypatch.setattr(quote_detector, "_schema_initialized", False)
        # reset caches
        monkeypatch.setattr(quote_detector, "_cached_quote", None)
        monkeypatch.setattr(quote_detector, "_cached_at", 0.0)
        yield db_path
        if db_path.exists():  # cleanup any leftover
            sqlite3.connect(db_path).close()


@pytest.fixture()
def redis_client(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Provide a Redis-compatible client patched into redis library APIs."""

    client = _redis_client()
    try:
        import redis  # type: ignore
    except Exception:  # pragma: no cover - redis missing
        redis = types.SimpleNamespace()  # type: ignore

    setattr(redis, "StrictRedis", lambda *args, **kwargs: client)
    setattr(redis, "Redis", lambda *args, **kwargs: client)
    setattr(redis, "from_url", lambda *args, **kwargs: client)
    sys.modules.setdefault("redis", redis)  # ensure imports receive the stub
    return client


@pytest.fixture(autouse=True)
def _autouse_redis(redis_client):  # type: ignore[no-untyped-def]
    """Ensure Redis patches are active for all tests."""

    return redis_client


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> Dict[str, str]:
    """Provide default environment variables for tests."""

    env = {
        "EXCHANGE_MODE": "mock",
        "TELEGRAM_BOT_TOKEN": "dummy",
        "ADMIN_CHAT_ID": "1",
        "BINANCE_FORCE_MOCK": "true",
        "BINANCE_LIVE_TRADING": "false",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env
