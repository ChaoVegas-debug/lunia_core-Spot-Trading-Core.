"""Lightweight persistent state helpers for the cores runtime."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from threading import RLock
from typing import Any, Dict

from app.core.state import get_state as get_runtime_state
from app.core.state import set_state as set_runtime_state

LOGGER = logging.getLogger(__name__)
_STATE_LOCK = RLock()
_STATE_PATH = Path(
    os.getenv("LUNIA_CORES_STATE", Path("logs") / "cores" / "cores_state.json")
)
_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)


def _load_from_disk() -> Dict[str, Any]:
    if not _STATE_PATH.exists():
        return {}
    try:
        with _STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError:  # pragma: no cover - corrupted file fallback
        LOGGER.warning("Corrupted cores state file detected, ignoring contents")
        return {}


def _write_to_disk(payload: Dict[str, Any]) -> None:
    tmp_path = _STATE_PATH.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
    tmp_path.replace(_STATE_PATH)


def get_state() -> Dict[str, Any]:
    """Return the merged state from the core runtime and global runtime."""
    with _STATE_LOCK:
        disk_state = _load_from_disk()
        merged = {**disk_state}
        merged.setdefault("cores", {})
        return merged


def set_state(patch: Dict[str, Any]) -> Dict[str, Any]:
    """Persist the given patch and synchronise with the global runtime state."""
    with _STATE_LOCK:
        state = get_state()
        state.update(patch)
        _write_to_disk(state)
        try:
            runtime = get_runtime_state()
        except Exception:  # pragma: no cover - global state optional
            runtime = {}
        runtime.setdefault("cores", {}).update(state.get("cores", {}))
        try:
            set_runtime_state(runtime)
        except Exception:  # pragma: no cover - if global setter unavailable
            LOGGER.debug("Global runtime state update skipped", exc_info=True)
        return state
