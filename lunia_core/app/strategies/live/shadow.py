"""Shadow trading utilities."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ShadowTrade:
    """Result of a simulated trade."""

    order_id: str
    symbol: str
    side: str
    qty: float
    price: float
    status: str
    latency_ms: float
    metadata: Dict[str, Any]


class ShadowTradingEngine:
    """Simulate order execution without touching live markets."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def simulate_order(
        self,
        *,
        symbol: str,
        side: str,
        qty: float,
        price: float,
        metadata: Dict[str, Any] | None = None,
    ) -> ShadowTrade:
        """Return a deterministic fill for the provided order."""

        start = time.perf_counter()
        order_id = metadata.get("order_id") if metadata else None
        if not order_id:
            order_id = uuid.uuid4().hex
        latency_ms = (time.perf_counter() - start) * 1000.0
        trade = ShadowTrade(
            order_id=order_id,
            symbol=symbol,
            side=side,
            qty=float(qty),
            price=float(price),
            status="FILLED",
            latency_ms=latency_ms,
            metadata={"shadow": True, **(metadata or {})},
        )
        return trade
