"""Market abuse monitoring utilities."""

from __future__ import annotations

import os
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from app.logging import audit_logger


@dataclass
class AbuseSignal:
    """Result of an abuse detection evaluation."""

    flagged: bool
    reason: str
    score: float
    details: Dict[str, object]


@dataclass
class OrderSnapshot:
    """Order snapshot used for heuristic tracking."""

    ts: float
    symbol: str
    side: str
    notional: float
    metadata: Dict[str, object]


class MarketAbuseMonitor:
    """Detect simple spoofing/layering patterns using heuristics."""

    def __init__(
        self,
        *,
        window_seconds: int = 60,
        cancel_ratio_threshold: float = 0.6,
        layering_threshold: int = 4,
        min_notional_usd: float = 500.0,
    ) -> None:
        self.window_seconds = window_seconds
        self.cancel_ratio_threshold = cancel_ratio_threshold
        self.layering_threshold = layering_threshold
        self.min_notional_usd = min_notional_usd
        self.enabled = os.getenv("ABUSE_MONITOR_ENABLED", "true").lower() == "true"
        self._history: Deque[OrderSnapshot] = deque()

    def disable(self) -> None:
        self.enabled = False

    def _prune(self) -> None:
        cutoff = time.time() - self.window_seconds
        while self._history and self._history[0].ts < cutoff:
            self._history.popleft()

    def evaluate(
        self,
        *,
        symbol: str | None,
        side: str | None,
        notional_usd: float,
        metadata: Optional[Dict[str, object]] = None,
    ) -> AbuseSignal:
        if not self.enabled or not symbol or not side:
            return AbuseSignal(False, "", 0.0, {})

        metadata = metadata or {}
        snapshot = OrderSnapshot(
            ts=time.time(),
            symbol=symbol,
            side=side.upper(),
            notional=notional_usd,
            metadata=metadata,
        )
        self._history.append(snapshot)
        self._prune()

        if notional_usd < self.min_notional_usd:
            return AbuseSignal(False, "", 0.0, {})

        cancels_ratio = float(metadata.get("cancel_ratio", 0.0))
        layering_count = int(metadata.get("layering_count", 0))
        order_count = int(metadata.get("order_count", 0))
        spoof_flag = cancels_ratio >= self.cancel_ratio_threshold and order_count >= 3
        layering_flag = layering_count >= self.layering_threshold

        if spoof_flag or layering_flag:
            reason = "spoofing" if spoof_flag else "layering"
            score = max(cancels_ratio, layering_count / max(order_count, 1))
            details: Dict[str, object] = {
                "symbol": symbol,
                "side": side,
                "notional": notional_usd,
                "cancel_ratio": cancels_ratio,
                "layering_count": layering_count,
                "order_count": order_count,
            }
            audit_logger.log_event(
                "market_abuse_detected",
                {"reason": reason, **details},
            )
            return AbuseSignal(True, reason, score, details)

        return AbuseSignal(False, "", 0.0, {})


def get_abuse_monitor() -> MarketAbuseMonitor:
    return MarketAbuseMonitor()
