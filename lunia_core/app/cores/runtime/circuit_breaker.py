"""Simple circuit breaker implementation for cores."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Dict

LOGGER = logging.getLogger(__name__)


@dataclass
class CircuitBreaker:
    max_daily_loss_pct: float = 3.0
    max_position_loss_pct: float = 5.0
    cooldown_seconds: int = 900

    def __post_init__(self) -> None:
        self._state = "CLOSED"
        self._tripped_at = 0.0

    @classmethod
    def from_config(cls, payload: Dict[str, object]) -> "CircuitBreaker":
        return cls(
            max_daily_loss_pct=float(payload.get("max_daily_loss_pct", 3.0)),
            max_position_loss_pct=float(payload.get("max_position_loss_pct", 5.0)),
            cooldown_seconds=int(payload.get("cooldown_seconds", 900)),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_position_loss_pct": self.max_position_loss_pct,
            "cooldown_seconds": self.cooldown_seconds,
            "state": self._state,
            "tripped_at": self._tripped_at,
        }

    def evaluate(self, realised_loss_pct: float) -> bool:
        if self._state == "OPEN":
            if time.time() - self._tripped_at >= self.cooldown_seconds:
                LOGGER.info("Circuit breaker half-opening after cooldown")
                self._state = "HALF_OPEN"
            else:
                return False
        if realised_loss_pct >= self.max_position_loss_pct:
            LOGGER.warning("Circuit breaker tripped: %.2f%%", realised_loss_pct)
            self._state = "OPEN"
            self._tripped_at = time.time()
            return False
        if self._state == "HALF_OPEN":
            LOGGER.info("Circuit breaker closing after successful attempt")
            self._state = "CLOSED"
        return True


__all__ = ["CircuitBreaker"]
