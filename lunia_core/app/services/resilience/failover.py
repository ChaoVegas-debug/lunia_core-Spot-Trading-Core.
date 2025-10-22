"""Failover helpers orchestrated by chaos testing and self-healing."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from ...core import state

LOG_DIR = Path(__file__).resolve().parents[4] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
FAILOVER_STATE = LOG_DIR / "failover.json"
READ_ONLY_MARKER = LOG_DIR / "redis-read-only.flag"
LLM_FALLBACK_MARKER = LOG_DIR / "llm-fallback.flag"

LOGGER = logging.getLogger(__name__)


def _feature_enabled() -> bool:
    return os.getenv("INFRA_PROD_ENABLED", "false").lower() == "true"


def promote_backup_exchange(
    primary: str, fallback: str, reason: str | None = None
) -> Dict[str, Any]:
    """Persistently switch to a backup exchange without touching core modules."""

    payload = {
        "primary": primary,
        "active": fallback,
        "reason": reason or "auto_failover",
        "timestamp": datetime.utcnow().isoformat(),
    }
    FAILOVER_STATE.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    LOGGER.warning("Exchange failover activated", extra=payload)
    if _feature_enabled():
        state.set_state(
            {
                "manual_override": True,
                "manual_strategy": {"name": "failover", "pair": "*", "bias": fallback},
            }
        )
    return payload


def enter_read_only_mode(reason: str) -> None:
    """Toggle trading switches off so the platform operates in read-only mode."""

    READ_ONLY_MARKER.write_text(reason, encoding="utf-8")
    LOGGER.error("Redis outage detected, switching to read-only mode: %s", reason)
    state.set_state({"trading_on": False, "agent_on": False})


def clear_read_only_mode() -> None:
    if READ_ONLY_MARKER.exists():
        READ_ONLY_MARKER.unlink()
    state.set_state({"trading_on": True, "agent_on": True})


def engage_llm_fallback(trigger: str) -> None:
    """Swap to rule-based decisions when LLMs refuse service."""

    LLM_FALLBACK_MARKER.write_text(trigger, encoding="utf-8")
    LOGGER.warning("LLM rate limit encountered; engaging rule-based fallback")
    state.set_state({"manual_override": True})


def release_llm_fallback() -> None:
    if LLM_FALLBACK_MARKER.exists():
        LLM_FALLBACK_MARKER.unlink()
    state.set_state({"manual_override": False})
