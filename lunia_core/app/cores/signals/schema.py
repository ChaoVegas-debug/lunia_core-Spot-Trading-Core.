"""Signal models shared across cores."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class RiskEnvelope:
    max_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    stop_loss_pct: Optional[float] = None
    leverage: Optional[float] = None


@dataclass
class Signal:
    type: str
    target_core: str
    symbol: str
    side: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    correlation_id: Optional[str] = None
    timeframe: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk: RiskEnvelope = field(default_factory=RiskEnvelope)


__all__ = ["Signal", "RiskEnvelope"]
