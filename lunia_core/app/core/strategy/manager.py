"""Preview/apply/undo support for strategy presets and weights."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:  # pragma: no cover - redis optional
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None  # type: ignore

from app.core.ai.strategies import REGISTRY
from app.core.bus.redis_bus import get_bus
from app.core.metrics import strategy_applications_total
from app.core.state import get_state, set_state
from app.logging import audit_logger

LOG = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).resolve().parents[3] / "logs"
_DEFAULT_DIR.mkdir(parents=True, exist_ok=True)
_PREVIEW_PREFIX = "lunia:strategy:preview:"
_UNDO_PREFIX = "lunia:strategy:undo:"
_TTL_SECONDS = 30

_PRESET_WEIGHTS: Dict[str, Dict[str, float]] = {
    "conservative": {
        "bollinger_reversion": 0.28,
        "vwap_reversion": 0.22,
        "micro_trend_scalper": 0.16,
        "liquidity_snipe": 0.14,
        "stat_pairs": 0.10,
        "ema_rsi_trend": 0.10,
    },
    "balanced": {
        "micro_trend_scalper": 0.24,
        "scalping_breakout": 0.20,
        "bollinger_reversion": 0.18,
        "vwap_reversion": 0.14,
        "liquidity_snipe": 0.12,
        "macd_crossover": 0.12,
    },
    "aggressive": {
        "scalping_breakout": 0.24,
        "micro_trend_scalper": 0.20,
        "volatility_breakout": 0.18,
        "liquidity_snipe": 0.14,
        "ema_rsi_trend": 0.12,
        "grid_light": 0.12,
    },
}

_PRESET_CONFIDENCE = {
    "conservative": 0.74,
    "balanced": 0.78,
    "aggressive": 0.7,
}


class _TTLCache:
    """Simple in-memory TTL cache used when Redis is unavailable."""

    def __init__(self, ttl: int) -> None:
        self.ttl = ttl
        self._entries: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._lock = threading.Lock()

    def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> None:
        expires = time.time() + float(ttl or self.ttl)
        with self._lock:
            self._entries[key] = (expires, value)

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            record = self._entries.get(key)
            if not record:
                return None
            expires, value = record
            if expires < time.time():
                self._entries.pop(key, None)
                return None
            return value

    def delete(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)


class ChangeJournal:
    """Hash-chained record of strategy configuration changes."""

    def __init__(self, path: Path | None = None) -> None:
        base_dir = Path(os.getenv("STRATEGY_LOG_DIR", str(_DEFAULT_DIR)))
        base_dir.mkdir(parents=True, exist_ok=True)
        default_path = base_dir / "strategy_changes.jsonl"
        env_path = os.getenv("STRATEGY_CHANGE_LOG_PATH")
        self._path = path or (Path(env_path) if env_path else default_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def record(
        self, action: str, actor: Optional[str], payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor or "unknown",
            "payload": payload,
        }
        prev_hash = self._read_last_hash()
        entry["prev_hash"] = prev_hash
        encoded = json.dumps(entry, sort_keys=True, default=str).encode("utf-8")
        digest = __import__("hashlib").sha256(encoded).hexdigest()
        entry["hash"] = digest
        with self._lock:
            with self._path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        audit_logger.log_event(
            "strategy_change",
            {
                "action": action,
                "actor": entry["actor"],
                "hash": digest,
                "prev_hash": prev_hash,
            },
        )
        return entry

    def list_recent(self, limit: int = 20) -> Iterable[Dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        except Exception:
            LOG.warning("Unable to read strategy change journal", exc_info=True)
            return []
        if not lines:
            return []
        tail = lines[-max(limit, 1) :]
        return [json.loads(line) for line in tail]

    def _read_last_hash(self) -> Optional[str]:
        if not self._path.exists():
            return None
        try:
            lines = self._path.read_text(encoding="utf-8").strip().splitlines()
        except Exception:
            return None
        if not lines:
            return None
        try:
            payload = json.loads(lines[-1])
        except Exception:
            return None
        return payload.get("hash")


class PreviewEngine:
    """Build previews and maintain temporary state for confirmation/undo."""

    def __init__(
        self, *, ttl: int = _TTL_SECONDS, redis_url: str | None = None
    ) -> None:
        self.ttl = ttl
        self._redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._redis: Optional["redis.Redis"] = None
        if redis is not None and os.getenv("ENABLE_REDIS", "false").lower() == "true":
            try:  # pragma: no cover - redis optional
                self._redis = redis.from_url(
                    self._redis_url, decode_responses=True, socket_timeout=5
                )
                self._redis.ping()
            except Exception:
                self._redis = None
        self._cache = _TTLCache(self.ttl)

    # Redis helpers -----------------------------------------------------
    def _set_temp(
        self, key: str, value: Dict[str, Any], ttl: Optional[int] = None
    ) -> None:
        payload = json.dumps(value, default=str)
        if self._redis is not None:
            try:  # pragma: no cover - redis optional
                self._redis.set(key, payload, ex=ttl or self.ttl)
                return
            except Exception:
                self._redis = None
        self._cache.set(key, value, ttl or self.ttl)

    def _get_temp(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis is not None:
            try:  # pragma: no cover
                value = self._redis.get(key)
                if value is None:
                    return None
                return json.loads(value)
            except Exception:
                self._redis = None
        return self._cache.get(key)

    def _delete_temp(self, key: str) -> None:
        if self._redis is not None:
            try:  # pragma: no cover
                self._redis.delete(key)
                return
            except Exception:
                self._redis = None
        self._cache.delete(key)

    # Preview management ------------------------------------------------
    def create_preview(
        self, payload: Dict[str, Any], *, actor: str | None = None
    ) -> Dict[str, Any]:
        state = get_state()
        current_weights = dict(state.get("spot", {}).get("weights", {}))
        strategy_name = str(payload.get("strategy", "balanced")).lower()
        overrides = (
            payload.get("weights") if isinstance(payload.get("weights"), dict) else {}
        )
        new_weights = self._resolve_weights(strategy_name, overrides, current_weights)
        delta = self._compute_delta(current_weights, new_weights)
        if not delta:
            raise ValueError("no effective strategy change detected")
        preview_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl)
        explanation = self._build_explanation(strategy_name, delta, payload)
        preview_payload = {
            "id": preview_id,
            "strategy": strategy_name,
            "actor": actor,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "before": {"weights": current_weights},
            "after": {"weights": new_weights},
            "delta": delta,
            "explain": explanation,
        }
        self._set_temp(_PREVIEW_PREFIX + preview_id, preview_payload)
        return {
            "preview_id": preview_id,
            "strategy": strategy_name,
            "expires_at": expires_at.isoformat(),
            "preview": preview_payload["after"],
            "delta": delta,
            "explain": explanation,
        }

    def consume_preview(self, preview_id: str) -> Optional[Dict[str, Any]]:
        key = _PREVIEW_PREFIX + preview_id
        payload = self._get_temp(key)
        if payload:
            self._delete_temp(key)
        return payload

    def store_undo(
        self, preview_payload: Dict[str, Any], *, actor: str | None = None
    ) -> Dict[str, Any]:
        undo_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=self.ttl)
        snapshot = {
            "id": undo_id,
            "actor": actor,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "preview_id": preview_payload.get("id"),
            "before": preview_payload.get("before"),
            "after": preview_payload.get("after"),
        }
        self._set_temp(_UNDO_PREFIX + undo_id, snapshot)
        return snapshot

    def consume_undo(self, undo_id: str) -> Optional[Dict[str, Any]]:
        key = _UNDO_PREFIX + undo_id
        payload = self._get_temp(key)
        if payload:
            self._delete_temp(key)
        return payload

    # Helpers -----------------------------------------------------------
    def _resolve_weights(
        self,
        strategy_name: str,
        overrides: Dict[str, Any],
        current: Dict[str, float],
    ) -> Dict[str, float]:
        available = {name: float(value) for name, value in current.items()}
        preset = _PRESET_WEIGHTS.get(strategy_name)
        if preset:
            available = {name: float(value) for name, value in preset.items()}
        elif strategy_name not in {"balanced", "custom"} and not overrides:
            raise ValueError(f"unknown strategy preset: {strategy_name}")
        for name in REGISTRY.keys():
            available.setdefault(name, 0.0)
        for name, value in overrides.items():
            if name not in available:
                continue
            try:
                parsed = float(value)
            except (TypeError, ValueError):
                continue
            available[name] = max(parsed, 0.0)
        total = sum(v for v in available.values() if v > 0)
        if total <= 0:
            raise ValueError("strategy weights must sum to a positive value")
        normalized = {
            name: round((value / total), 6) if value > 0 else 0.0
            for name, value in available.items()
        }
        return normalized

    def _compute_delta(
        self, before: Dict[str, float], after: Dict[str, float]
    ) -> Dict[str, Dict[str, float]]:
        delta: Dict[str, Dict[str, float]] = {}
        keys = sorted(set(before.keys()) | set(after.keys()))
        for name in keys:
            before_val = round(float(before.get(name, 0.0)), 6)
            after_val = round(float(after.get(name, 0.0)), 6)
            diff = round(after_val - before_val, 6)
            if abs(diff) < 1e-6:
                continue
            delta[name] = {
                "before": before_val,
                "after": after_val,
                "delta": diff,
                "direction": "increase" if diff > 0 else "decrease",
            }
        return delta

    def _build_explanation(
        self,
        strategy_name: str,
        delta: Dict[str, Dict[str, float]],
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        confidence = _PRESET_CONFIDENCE.get(strategy_name, 0.68)
        ordered_changes = sorted(
            (
                {
                    "strategy": name,
                    "before": values["before"],
                    "after": values["after"],
                    "delta": values["delta"],
                    "direction": values["direction"],
                }
                for name, values in delta.items()
            ),
            key=lambda item: abs(item["delta"]),
            reverse=True,
        )
        top = ordered_changes[0] if ordered_changes else None
        summary = (
            f"Preset '{strategy_name}' rebalances {len(ordered_changes)} strategies"
            if ordered_changes
            else f"Preset '{strategy_name}' keeps existing allocations"
        )
        if payload.get("notes"):
            summary += f" ({payload['notes']})"
        rationale = None
        if top:
            if top["direction"] == "increase":
                rationale = (
                    f"Boosting {top['strategy']} to capture momentum opportunities."
                )
            else:
                rationale = (
                    f"Reducing exposure to {top['strategy']} to limit drawdown risk."
                )
        return {
            "summary": summary,
            "strategy": strategy_name,
            "confidence": round(confidence, 2),
            "changes": ordered_changes,
            "rationale": rationale,
            "generated_at": datetime.utcnow().isoformat(),
        }


class StrategyApplicator:
    """High-level API to preview, confirm, and undo strategy updates."""

    def __init__(
        self,
        preview_engine: PreviewEngine | None = None,
        change_journal: ChangeJournal | None = None,
    ) -> None:
        self.preview_engine = preview_engine or PreviewEngine()
        self.change_journal = change_journal or ChangeJournal()
        self.bus = get_bus()

    def preview(
        self, payload: Dict[str, Any], *, actor: str | None = None
    ) -> Dict[str, Any]:
        preview = self.preview_engine.create_preview(payload, actor=actor)
        event = {
            "preview_id": preview["preview_id"],
            "strategy": preview["strategy"],
            "delta": preview["delta"],
            "actor": actor or "unknown",
            "expires_at": preview["expires_at"],
        }
        self.bus.publish("strategy.change.preview", event)
        try:
            strategy_applications_total.labels(action="preview").inc()
        except Exception:
            LOG.debug("Unable to record strategy preview metric", exc_info=True)
        return preview

    def assign(
        self, payload: Dict[str, Any], *, actor: str | None = None
    ) -> Dict[str, Any]:
        action = str(payload.get("action", "confirm")).lower()
        if action == "undo":
            undo_id = payload.get("undo_id") or payload.get("preview_id")
            if not undo_id:
                raise ValueError("undo_id required for undo action")
            snapshot = self.preview_engine.consume_undo(str(undo_id))
            if snapshot is None:
                raise ValueError("undo window expired or already used")
            before = snapshot.get("before", {})
            weights = before.get("weights", {})
            set_state({"spot": {"weights": weights}})
            record = self.change_journal.record(
                "undo",
                actor,
                {
                    "undo_id": snapshot.get("id"),
                    "preview_id": snapshot.get("preview_id"),
                    "restored_weights": weights,
                },
            )
            self.bus.publish(
                "strategy.change.undo",
                {
                    "undo_id": snapshot.get("id"),
                    "preview_id": snapshot.get("preview_id"),
                    "actor": actor or "unknown",
                    "hash": record.get("hash"),
                },
            )
            try:
                strategy_applications_total.labels(action="undo").inc()
            except Exception:
                LOG.debug("Unable to record strategy undo metric", exc_info=True)
            return {
                "status": "restored",
                "restored": {"weights": weights},
                "change": record,
            }

        preview_id = payload.get("preview_id")
        if not preview_id:
            raise ValueError("preview_id required to confirm strategy change")
        preview_payload = self.preview_engine.consume_preview(str(preview_id))
        if preview_payload is None:
            raise ValueError("preview expired or already applied")
        after = preview_payload.get("after", {})
        weights = after.get("weights", {})
        set_state({"spot": {"weights": weights}})
        undo_snapshot = self.preview_engine.store_undo(preview_payload, actor=actor)
        record = self.change_journal.record(
            "confirm",
            actor,
            {
                "preview_id": preview_payload.get("id"),
                "strategy": preview_payload.get("strategy"),
                "delta": preview_payload.get("delta"),
                "applied_weights": weights,
            },
        )
        self.bus.publish(
            "strategy.change.confirm",
            {
                "preview_id": preview_payload.get("id"),
                "strategy": preview_payload.get("strategy"),
                "actor": actor or "unknown",
                "hash": record.get("hash"),
            },
        )
        try:
            strategy_applications_total.labels(action="confirm").inc()
        except Exception:
            LOG.debug("Unable to record strategy confirm metric", exc_info=True)
        return {
            "status": "applied",
            "applied": {"weights": weights},
            "undo_token": undo_snapshot.get("id"),
            "undo_expires_at": undo_snapshot.get("expires_at"),
            "explain": preview_payload.get("explain"),
            "change": record,
        }

    def recent_changes(self, limit: int = 20) -> Iterable[Dict[str, Any]]:
        return self.change_journal.list_recent(limit=limit)


__all__ = [
    "StrategyApplicator",
    "PreviewEngine",
    "ChangeJournal",
]
