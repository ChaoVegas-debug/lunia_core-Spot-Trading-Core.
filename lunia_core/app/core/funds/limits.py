"""Management of funds-in-work limits and previews."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:  # pragma: no cover - redis optional in offline environments
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis optional
    redis = None  # type: ignore

from app.core.metrics import funds_limits_changes_total
from app.logging import audit_logger

LOG = logging.getLogger(__name__)

_DEFAULT_DIR = Path(__file__).resolve().parents[3] / "logs"
_PREVIEW_KEY = "lunia:funds:preview"
_UNDO_KEY = "lunia:funds:undo"
_TTL_SECONDS = 30


@dataclass
class GlobalLimit:
    """Global percentage cap for capital allocation."""

    max_allocation_pct: float = 100.0
    notes: str | None = None

    @classmethod
    def from_payload(cls, payload: Any) -> "GlobalLimit":
        if payload is None:
            return cls()
        if isinstance(payload, (int, float)):
            return cls(max_allocation_pct=float(payload))
        if isinstance(payload, dict):
            value = payload.get(
                "max_allocation_pct",
                payload.get("global_limit", payload.get("percent")),
            )
            notes = payload.get("notes")
            try:
                percent = float(value) if value is not None else 100.0
            except (TypeError, ValueError):
                percent = 100.0
            return cls(max_allocation_pct=percent, notes=notes)
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        return {"max_allocation_pct": self.max_allocation_pct, "notes": self.notes}


@dataclass
class ExchangeLimit:
    """Per-exchange exposure settings."""

    exchange: str
    max_usd: float | None = None
    max_pct: float | None = None
    enabled: bool = True

    @classmethod
    def from_payload(cls, name: str, payload: Any) -> "ExchangeLimit":
        exchange = (name or "").upper()
        if isinstance(payload, (int, float)):
            return cls(exchange=exchange, max_pct=float(payload))
        if isinstance(payload, dict):
            max_usd = payload.get("max_usd", payload.get("usd"))
            max_pct = payload.get("max_pct", payload.get("pct"))
            enabled = payload.get("enabled", True)
            try:
                max_usd_val = float(max_usd) if max_usd is not None else None
            except (TypeError, ValueError):
                max_usd_val = None
            try:
                max_pct_val = float(max_pct) if max_pct is not None else None
            except (TypeError, ValueError):
                max_pct_val = None
            return cls(
                exchange=exchange,
                max_usd=max_usd_val,
                max_pct=max_pct_val,
                enabled=bool(enabled),
            )
        return cls(exchange=exchange)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exchange": self.exchange,
            "max_usd": self.max_usd,
            "max_pct": self.max_pct,
            "enabled": self.enabled,
        }


@dataclass
class PortfolioLimit:
    """Per-portfolio or symbol exposure settings."""

    symbol: str
    max_usd: float | None = None
    max_pct: float | None = None
    strategy: str | None = None

    @classmethod
    def from_payload(cls, name: str, payload: Any) -> "PortfolioLimit":
        symbol = (name or "").upper()
        if isinstance(payload, (int, float)):
            return cls(symbol=symbol, max_usd=float(payload))
        if isinstance(payload, dict):
            max_usd = payload.get("max_usd", payload.get("usd"))
            max_pct = payload.get("max_pct", payload.get("pct"))
            strategy = payload.get("strategy")
            try:
                max_usd_val = float(max_usd) if max_usd is not None else None
            except (TypeError, ValueError):
                max_usd_val = None
            try:
                max_pct_val = float(max_pct) if max_pct is not None else None
            except (TypeError, ValueError):
                max_pct_val = None
            return cls(
                symbol=symbol,
                max_usd=max_usd_val,
                max_pct=max_pct_val,
                strategy=strategy,
            )
        return cls(symbol=symbol)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "max_usd": self.max_usd,
            "max_pct": self.max_pct,
            "strategy": self.strategy,
        }


class _TTLCache:
    """In-memory TTL cache used when Redis is unavailable."""

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


class FundsManager:
    """Manage fund allocation limits with preview/confirm semantics."""

    def __init__(
        self,
        *,
        storage_path: Path | None = None,
        audit_path: Path | None = None,
        redis_url: str | None = None,
    ) -> None:
        base_dir = Path(os.getenv("FUNDS_STATE_DIR", str(_DEFAULT_DIR)))
        base_dir.mkdir(parents=True, exist_ok=True)
        self._limits_path = storage_path or Path(
            os.getenv("FUNDS_LIMITS_PATH", base_dir / "funds_limits.json")
        )
        self._limits_path.parent.mkdir(parents=True, exist_ok=True)
        self._audit_path = audit_path or Path(
            os.getenv("FUNDS_AUDIT_PATH", base_dir / "funds_limits_chain.jsonl")
        )
        self._audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._redis_url = redis_url or os.getenv(
            "REDIS_URL", "redis://localhost:6379/0"
        )
        self._redis: Optional["redis.Redis"] = None
        if redis is not None:
            try:  # pragma: no cover - redis optional
                self._redis = redis.from_url(
                    self._redis_url, decode_responses=True, socket_timeout=5
                )
            except Exception:
                self._redis = None
        self._cache = _TTLCache(_TTL_SECONDS)
        self._lock = threading.Lock()
        self._audit_lock = threading.Lock()

    # ------------------------------------------------------------------
    def load_current_limits(self) -> Dict[str, Any]:
        with self._lock:
            if not self._limits_path.exists():
                return self._default_payload()
            try:
                data = json.loads(self._limits_path.read_text(encoding="utf-8"))
                return self._normalize(data)
            except Exception:
                LOG.exception("Failed to load funds limits; returning defaults")
                return self._default_payload()

    # ------------------------------------------------------------------
    def preview_changes(
        self, payload: Dict[str, Any], *, actor: str | None = None
    ) -> Dict[str, Any]:
        current = self.load_current_limits()
        merged = self._merge_limits(current, payload)
        delta = self._compute_delta(current, merged)
        expires_at = datetime.utcnow().timestamp() + _TTL_SECONDS
        preview_payload = {
            "limits": merged,
            "delta": delta,
            "actor": actor,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": datetime.utcfromtimestamp(expires_at).isoformat(),
        }
        self._set_temp(_PREVIEW_KEY, preview_payload, ttl=_TTL_SECONDS)
        LOG.info("Funds limit preview stored by %s", actor or "unknown")
        try:
            funds_limits_changes_total.labels(action="preview").inc()
        except Exception:
            LOG.debug("Unable to record preview metric", exc_info=True)
        return {
            "preview": merged,
            "preview_delta": delta,
            "expires_at": preview_payload["expires_at"],
        }

    # ------------------------------------------------------------------
    def confirm_changes(self, *, actor: str | None = None) -> Dict[str, Any]:
        preview = self._get_temp(_PREVIEW_KEY)
        if not preview:
            raise ValueError("no pending preview to confirm")
        current = self.load_current_limits()
        new_limits = preview.get("limits", self._default_payload())
        with self._lock:
            self._limits_path.write_text(
                json.dumps(self._augment_with_metadata(new_limits, actor), indent=2),
                encoding="utf-8",
            )
        self._delete_temp(_PREVIEW_KEY)
        undo_payload = {
            "limits": current,
            "actor": actor,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": datetime.utcfromtimestamp(
                time.time() + _TTL_SECONDS
            ).isoformat(),
        }
        self._set_temp(_UNDO_KEY, undo_payload, ttl=_TTL_SECONDS)
        self._append_audit_chain(
            "confirm", actor, {"delta": preview.get("delta"), "applied": new_limits}
        )
        LOG.info("Funds limits confirmed by %s", actor or "unknown")
        try:
            funds_limits_changes_total.labels(action="confirm").inc()
        except Exception:
            LOG.debug("Unable to record confirm metric", exc_info=True)
        return {
            "status": "confirmed",
            "applied": new_limits,
            "undo_expires_at": undo_payload["expires_at"],
        }

    # ------------------------------------------------------------------
    def undo_changes(self, *, actor: str | None = None) -> Dict[str, Any]:
        snapshot = self._get_temp(_UNDO_KEY)
        if not snapshot:
            raise ValueError("no undo snapshot available")
        limits = snapshot.get("limits", self._default_payload())
        with self._lock:
            self._limits_path.write_text(
                json.dumps(self._augment_with_metadata(limits, actor), indent=2),
                encoding="utf-8",
            )
        self._delete_temp(_UNDO_KEY)
        self._append_audit_chain("undo", actor, {"restored": limits})
        LOG.info("Funds limits restored by %s", actor or "unknown")
        try:
            funds_limits_changes_total.labels(action="undo").inc()
        except Exception:
            LOG.debug("Unable to record undo metric", exc_info=True)
        return {"status": "restored", "restored": limits}

    # ------------------------------------------------------------------
    def peek_preview(self) -> Optional[Dict[str, Any]]:
        return self._get_temp(_PREVIEW_KEY)

    # ------------------------------------------------------------------
    def _augment_with_metadata(
        self, limits: Dict[str, Any], actor: str | None
    ) -> Dict[str, Any]:
        enriched = json.loads(json.dumps(limits))  # deep copy via json
        enriched["updated_at"] = datetime.utcnow().isoformat()
        if actor:
            enriched["updated_by"] = actor
        return enriched

    # ------------------------------------------------------------------
    def _set_temp(self, key: str, value: Dict[str, Any], ttl: int) -> None:
        if self._redis is not None:
            try:  # pragma: no cover - redis optional
                self._redis.set(key, json.dumps(value), ex=ttl)
                return
            except Exception:
                self._redis = None
        self._cache.set(key, value, ttl)

    # ------------------------------------------------------------------
    def _get_temp(self, key: str) -> Optional[Dict[str, Any]]:
        if self._redis is not None:
            try:  # pragma: no cover - redis optional
                value = self._redis.get(key)
                if value is None:
                    return None
                return json.loads(value)
            except Exception:
                self._redis = None
        return self._cache.get(key)

    # ------------------------------------------------------------------
    def _delete_temp(self, key: str) -> None:
        if self._redis is not None:
            try:  # pragma: no cover - redis optional
                self._redis.delete(key)
                return
            except Exception:
                self._redis = None
        self._cache.delete(key)

    # ------------------------------------------------------------------
    def _merge_limits(
        self, current: Dict[str, Any], changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = json.loads(json.dumps(current))  # deep copy
        global_payload = changes.get("global_limit")
        if global_payload is not None:
            result["global"] = GlobalLimit.from_payload(global_payload).to_dict()
        exchanges_payload = changes.get("exchange_limits")
        if exchanges_payload is not None:
            updated: Dict[str, Dict[str, Any]] = {}
            if isinstance(exchanges_payload, dict):
                iterator = exchanges_payload.items()
            elif isinstance(exchanges_payload, list):
                iterator = (
                    (item.get("exchange"), item)
                    for item in exchanges_payload
                    if isinstance(item, dict)
                )
            else:
                iterator = []
            for name, payload in iterator:
                if not name:
                    continue
                limit = ExchangeLimit.from_payload(name, payload)
                updated[limit.exchange] = limit.to_dict()
            result["exchanges"].update(updated)
        portfolio_payload = changes.get("portfolio_limits")
        if portfolio_payload is not None:
            updated_pf: Dict[str, Dict[str, Any]] = {}
            if isinstance(portfolio_payload, dict):
                iterator = portfolio_payload.items()
            elif isinstance(portfolio_payload, list):
                iterator = (
                    (item.get("symbol"), item)
                    for item in portfolio_payload
                    if isinstance(item, dict)
                )
            else:
                iterator = []
            for name, payload in iterator:
                if not name:
                    continue
                limit = PortfolioLimit.from_payload(name, payload)
                updated_pf[limit.symbol] = limit.to_dict()
            result["portfolio"].update(updated_pf)
        return result

    # ------------------------------------------------------------------
    def _compute_delta(
        self, old: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        delta: Dict[str, Any] = {}
        if old.get("global") != new.get("global"):
            delta["global_limit"] = {
                "before": old.get("global"),
                "after": new.get("global"),
            }
        if old.get("exchanges") != new.get("exchanges"):
            exchange_delta: Dict[str, Any] = {}
            all_exchanges = set(old.get("exchanges", {}).keys()) | set(
                new.get("exchanges", {}).keys()
            )
            for name in sorted(all_exchanges):
                if old.get("exchanges", {}).get(name) != new.get("exchanges", {}).get(
                    name
                ):
                    exchange_delta[name] = {
                        "before": old.get("exchanges", {}).get(name),
                        "after": new.get("exchanges", {}).get(name),
                    }
            if exchange_delta:
                delta["exchange_limits"] = exchange_delta
        if old.get("portfolio") != new.get("portfolio"):
            portfolio_delta: Dict[str, Any] = {}
            all_symbols = set(old.get("portfolio", {}).keys()) | set(
                new.get("portfolio", {}).keys()
            )
            for symbol in sorted(all_symbols):
                if old.get("portfolio", {}).get(symbol) != new.get("portfolio", {}).get(
                    symbol
                ):
                    portfolio_delta[symbol] = {
                        "before": old.get("portfolio", {}).get(symbol),
                        "after": new.get("portfolio", {}).get(symbol),
                    }
            if portfolio_delta:
                delta["portfolio_limits"] = portfolio_delta
        return delta

    # ------------------------------------------------------------------
    def _default_payload(self) -> Dict[str, Any]:
        return {
            "global": GlobalLimit().to_dict(),
            "exchanges": {},
            "portfolio": {},
        }

    # ------------------------------------------------------------------
    def _normalize(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = self._default_payload()
        if isinstance(payload, dict):
            if "global" in payload:
                normalized["global"] = GlobalLimit.from_payload(
                    payload.get("global")
                ).to_dict()
            if isinstance(payload.get("exchanges"), dict):
                normalized["exchanges"] = {
                    name: ExchangeLimit.from_payload(name, value).to_dict()
                    for name, value in payload["exchanges"].items()
                }
            if isinstance(payload.get("portfolio"), dict):
                normalized["portfolio"] = {
                    name: PortfolioLimit.from_payload(name, value).to_dict()
                    for name, value in payload["portfolio"].items()
                }
        return normalized

    # ------------------------------------------------------------------
    def _append_audit_chain(
        self, action: str, actor: str | None, payload: Dict[str, Any]
    ) -> None:
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "action": action,
            "actor": actor or "unknown",
            "payload": payload,
        }
        prev_hash = self._read_last_hash()
        entry["prev_hash"] = prev_hash
        try:
            encoded = json.dumps(entry, sort_keys=True).encode("utf-8")
        except TypeError:
            safe_entry = json.loads(json.dumps(entry, default=str, sort_keys=True))
            encoded = json.dumps(safe_entry, sort_keys=True).encode("utf-8")
            entry = safe_entry
        digest = __import__("hashlib").sha256(encoded).hexdigest()
        entry["hash"] = digest
        with self._audit_lock:
            try:
                with self._audit_path.open("a", encoding="utf-8") as fp:
                    fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                LOG.exception("Failed to append funds audit chain entry")
        audit_logger.log_event(
            "funds_limits_action",
            {
                "action": action,
                "actor": entry["actor"],
                "hash": digest,
                "prev_hash": prev_hash,
            },
        )

    # ------------------------------------------------------------------
    def _read_last_hash(self) -> Optional[str]:
        if not self._audit_path.exists():
            return None
        try:
            lines = self._audit_path.read_text(encoding="utf-8").strip().splitlines()
            if not lines:
                return None
            last = json.loads(lines[-1])
            return last.get("hash")
        except Exception:
            LOG.warning("Unable to read previous funds audit hash", exc_info=True)
            return None


__all__ = [
    "FundsManager",
    "GlobalLimit",
    "ExchangeLimit",
    "PortfolioLimit",
]
