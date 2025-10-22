"""Registry and lifecycle helpers for Lunia cores."""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, Iterable, Optional

from ..impl.arbitrage_core import ArbitrageCore
from ..impl.defi_core import DefiCore
from ..impl.futures_core import FuturesCore
from ..impl.hft_core import HFTCore
from ..impl.llm_core import LLMCore
from ..impl.options_core import OptionsCore
from ..impl.spot_core import SpotCore
from ..signals.schema import Signal
from ..state import get_state, set_state
from .base_core import BaseCore, CoreMetadata
from .circuit_breaker import CircuitBreaker

LOGGER = logging.getLogger(__name__)


CORE_FACTORY = {
    "SPOT": SpotCore,
    "HFT": HFTCore,
    "FUTURES": FuturesCore,
    "OPTIONS": OptionsCore,
    "ARBITRAGE": ArbitrageCore,
    "DEFI": DefiCore,
    "LLM": LLMCore,
}


class CoreRegistry:
    """Mutable registry backed by persistent state."""

    def __init__(self) -> None:
        self._instances: Dict[str, BaseCore] = {}
        self._lock = asyncio.Lock()
        self._load_from_state()

    def _load_from_state(self) -> None:
        state = get_state().get("cores", {})
        for name, payload in state.items():
            cls = CORE_FACTORY.get(name)
            if not cls:
                continue
            metadata = CoreMetadata(
                name=name,
                weight=float(payload.get("weight", 1.0)),
                enabled=bool(payload.get("enabled", True)),
                description=payload.get("description"),
                tags=tuple(payload.get("tags", [])),
            )
            breaker = CircuitBreaker.from_config(payload.get("circuit", {}))
            instance = cls(metadata=metadata, breaker=breaker)
            self._instances[name] = instance

        for name, cls in CORE_FACTORY.items():
            if name not in self._instances:
                metadata = CoreMetadata(name=name)
                self._instances[name] = cls(metadata=metadata, breaker=CircuitBreaker())
        self.persist()

    def persist(self) -> None:
        payload = {
            name: {
                "weight": inst.metadata.weight,
                "enabled": inst.metadata.enabled,
                "description": inst.metadata.description,
                "tags": list(inst.metadata.tags),
                "circuit": inst.circuit_breaker.to_dict(),
            }
            for name, inst in self._instances.items()
        }
        set_state({"cores": payload})

    # --- public API --------------------------------------------------
    def names(self) -> Iterable[str]:
        return self._instances.keys()

    def get(self, name: str) -> Optional[BaseCore]:
        return self._instances.get(name)

    async def ensure_started(
        self, loop: asyncio.AbstractEventLoop, intervals: Dict[str, float]
    ) -> None:
        async with self._lock:
            for name, instance in self._instances.items():
                if not instance.metadata.enabled:
                    continue
                interval = intervals.get(name, intervals.get("default", 1.0))
                instance.schedule(loop, interval)
                await instance.start()

    async def stop_all(self) -> None:
        async with self._lock:
            for instance in self._instances.values():
                await instance.stop()

    def set_weight(self, name: str, weight: float) -> None:
        instance = self._instances[name]
        instance.metadata.weight = weight
        self.persist()

    def toggle(self, name: str, enabled: bool) -> None:
        instance = self._instances[name]
        instance.metadata.enabled = enabled
        self.persist()

    async def dispatch(self, signal: Signal) -> None:
        target = self._instances.get(signal.target_core)
        if not target:
            LOGGER.warning("Unknown target core %s", signal.target_core)
            return
        await target.handle_signal(signal)

    def snapshot(self) -> Dict[str, Dict[str, object]]:
        return {name: core.describe() for name, core in self._instances.items()}


REGISTRY = CoreRegistry()


__all__ = ["REGISTRY", "CoreRegistry", "CORE_FACTORY"]
