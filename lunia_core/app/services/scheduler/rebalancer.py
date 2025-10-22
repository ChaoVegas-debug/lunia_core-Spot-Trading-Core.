"""Scheduler task placeholder for rebalancing."""

"""Rebalancer utilities for Lunia cores."""
from __future__ import annotations

import json
import logging
import os
import statistics
import time
from collections import deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Deque, Dict, Iterable, Optional

from ...boot import CORES
from ...core.ai.agent import Agent
from ...core.bus.redis_bus import get_bus
from ...core.strategy import StrategyApplicator
from ...logging import audit_logger

LOG_PATH = Path(__file__).resolve().parents[4] / "logs" / "rebalancer.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


class VolatilityMonitor:
    """Lightweight realised-volatility monitor using recent price samples."""

    def __init__(
        self,
        agent: Agent,
        *,
        symbol: str = "BTCUSDT",
        window: int = 12,
        threshold_pct: float = float(os.getenv("REBALANCER_VOL_THRESHOLD", "45")),
        cooldown_seconds: int = 300,
    ) -> None:
        self.agent = agent
        self.symbol = symbol
        self.window = window
        self.threshold_pct = threshold_pct
        self.cooldown_seconds = cooldown_seconds
        self._prices: Deque[float] = deque(maxlen=window)
        self._last_trigger_ts: float = 0.0

    def evaluate(self) -> Optional[Dict[str, float]]:
        price_fetcher = getattr(self.agent.client, "get_price", None)
        if price_fetcher is None:
            return None
        try:
            price = float(price_fetcher(self.symbol))
        except Exception:  # pragma: no cover - data access errors
            logger.debug("Unable to fetch price for volatility monitor", exc_info=True)
            return None
        self._prices.append(price)
        if len(self._prices) < 3:
            return None
        returns = [
            (self._prices[idx] - self._prices[idx - 1]) / self._prices[idx - 1] * 100
            for idx in range(1, len(self._prices))
            if self._prices[idx - 1] > 0
        ]
        if not returns:
            return None
        realized = statistics.pstdev(returns) * (len(returns) ** 0.5)
        now = time.time()
        if (
            realized >= self.threshold_pct
            and now - self._last_trigger_ts >= self.cooldown_seconds
        ):
            self._last_trigger_ts = now
            payload = {
                "symbol": self.symbol,
                "volatility_pct": round(realized, 2),
                "threshold_pct": float(self.threshold_pct),
                "window": self.window,
            }
            return payload
        return None


class MarketEventDetector:
    """Detect sudden market moves using price deltas as a proxy for events."""

    def __init__(
        self,
        agent: Agent,
        *,
        symbol: str = "BTCUSDT",
        change_threshold_pct: float = float(
            os.getenv("REBALANCER_EVENT_THRESHOLD", "2.5")
        ),
        cooldown_seconds: int = 300,
    ) -> None:
        self.agent = agent
        self.symbol = symbol
        self.change_threshold_pct = change_threshold_pct
        self.cooldown_seconds = cooldown_seconds
        self._last_price: Optional[float] = None
        self._last_trigger_ts: float = 0.0

    def evaluate(self) -> Optional[Dict[str, float]]:
        fetcher = getattr(self.agent.client, "get_price", None)
        if fetcher is None:
            return None
        try:
            price = float(fetcher(self.symbol))
        except Exception:  # pragma: no cover - data access errors
            logger.debug("Market event detector failed to fetch price", exc_info=True)
            return None
        prev = self._last_price
        self._last_price = price
        if prev is None or prev <= 0:
            return None
        change_pct = abs((price - prev) / prev * 100)
        now = time.time()
        if (
            change_pct >= self.change_threshold_pct
            and now - self._last_trigger_ts >= self.cooldown_seconds
        ):
            self._last_trigger_ts = now
            payload = {
                "symbol": self.symbol,
                "change_pct": round(change_pct, 2),
                "current_price": price,
                "previous_price": prev,
            }
            return payload
        return None


class MacroCalendar:
    """Check static macro calendar for upcoming high-impact events."""

    def __init__(
        self,
        *,
        window_minutes: int = int(os.getenv("REBALANCER_MACRO_WINDOW_MIN", "180")),
        calendar_path: Optional[str] = None,
    ) -> None:
        configured = calendar_path or os.getenv("MACRO_CALENDAR_PATH")
        default_path = (
            Path(configured)
            if configured
            else Path(__file__).resolve().parents[4] / "data" / "macro_events.json"
        )
        self.path = default_path
        self.window_minutes = window_minutes
        self._acknowledged: set[str] = set()

    def upcoming(self) -> Optional[Dict[str, str]]:
        if not self.path.exists():
            return None
        try:
            raw = self.path.read_text(encoding="utf-8")
            if not raw.strip():
                return None
            data = json.loads(raw)
        except Exception:  # pragma: no cover - parsing errors
            logger.warning(
                "Unable to parse macro calendar at %s", self.path, exc_info=True
            )
            return None
        events: Iterable[Dict[str, str]] = data if isinstance(data, list) else []
        now = datetime.utcnow()
        window_end = now + timedelta(minutes=self.window_minutes)
        for event in events:
            ts = event.get("time") or event.get("timestamp")
            if not ts:
                continue
            try:
                event_time = datetime.fromisoformat(ts)
            except ValueError:
                continue
            if not (now <= event_time <= window_end):
                continue
            event_id = str(event.get("id") or event.get("name") or ts)
            if event_id in self._acknowledged:
                continue
            self._acknowledged.add(event_id)
            return {
                "event_id": event_id,
                "name": str(event.get("name", "macro-event")),
                "time": event_time.isoformat(),
                "impact": str(event.get("impact", "unknown")),
            }
        return None


def rebalance(agent: Agent) -> Dict[str, float]:
    """Compute simple target allocations and log."""
    portfolio = agent.portfolio
    balances = agent.client.get_balances()
    equity = portfolio.get_equity_usd(
        {asset: bal["free"] + bal["locked"] for asset, bal in balances.items()}
    )
    targets = {
        name: cfg["weight"] * equity
        for name, cfg in CORES.items()
        if cfg.get("enabled")
    }
    logger.info("Rebalance tick equity=%.2f targets=%s", equity, targets)
    return targets


def _trigger_safe_mode(
    strategy_applicator: StrategyApplicator, reason: str, context: Dict[str, object]
) -> None:
    """Switch spot strategies to the conservative preset and log the rationale."""

    try:
        preview = strategy_applicator.preview(
            {"strategy": "conservative", "notes": reason, "context": context},
            actor="scheduler",
        )
    except Exception as exc:  # pragma: no cover - preview failures
        logger.warning("Unable to generate safe strategy preview: %s", exc)
        return

    explain = preview.get("explain", {})
    try:
        strategy_applicator.assign(
            {"preview_id": preview["preview_id"]}, actor="scheduler"
        )
    except Exception as exc:  # pragma: no cover - confirm failures
        logger.warning("Failed to apply safe strategy automatically: %s", exc)
        return

    audit_logger.log_event(
        "scheduler.safe_strategy",
        {
            "reason": reason,
            "context": context,
            "explain": explain,
        },
    )
    logger.info("Safe strategy applied due to %s", reason)


def start_rebalancer(agent: Agent, interval_seconds: int = 900) -> None:
    bus = get_bus()
    strategy_applicator = StrategyApplicator()
    volatility_monitor = VolatilityMonitor(agent)
    market_detector = MarketEventDetector(agent)
    macro_calendar = MacroCalendar()

    logger.info("Starting rebalancer loop interval=%s", interval_seconds)
    while True:  # pragma: no cover - long-running loop
        rebalance(agent)

        triggers: list[tuple[str, Dict[str, object]]] = []

        volatility = volatility_monitor.evaluate()
        if volatility:
            bus.publish("scheduler.volatility_triggered", volatility)
            logger.info("Volatility trigger detected: %s", volatility)
            triggers.append(("volatility", volatility))

        market_event = market_detector.evaluate()
        if market_event:
            bus.publish("scheduler.market_event_detected", market_event)
            logger.info("Market event detected: %s", market_event)
            triggers.append(("market-event", market_event))

        macro_event = macro_calendar.upcoming()
        if macro_event:
            bus.publish("scheduler.macro_calendar_alert", macro_event)
            logger.info("Macro calendar alert: %s", macro_event)
            triggers.append(("macro", macro_event))

        if triggers:
            combined_context = {name: payload for name, payload in triggers}
            _trigger_safe_mode(
                strategy_applicator, "automated-scheduler-trigger", combined_context
            )

        time.sleep(interval_seconds)
