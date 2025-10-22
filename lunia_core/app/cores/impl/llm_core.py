"""Core responsible for ingesting and routing LLM signals."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from ..runtime.base_core import BaseCore, CoreMetadata
from ..runtime.circuit_breaker import CircuitBreaker
from ..runtime.router import ROUTER
from ..signals.schema import Signal

LOGGER = logging.getLogger(__name__)
LOG_PATH = Path("logs") / "llm"
LOG_PATH.mkdir(parents=True, exist_ok=True)


class LLMCore(BaseCore):
    def __init__(self, metadata: CoreMetadata, breaker: CircuitBreaker) -> None:
        super().__init__(metadata)
        self.circuit_breaker = breaker

    async def handle_signal(self, signal: Signal) -> None:
        LOGGER.info("LLM core relaying %s", signal)
        snapshot = LOG_PATH / "signals.jsonl"
        with snapshot.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(signal.__dict__, ensure_ascii=False) + "\n")
        await ROUTER.publish(signal)

    async def tick(self) -> None:
        await asyncio.sleep(5.0)


__all__ = ["LLMCore"]
