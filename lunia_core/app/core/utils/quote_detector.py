"""Quote currency detection and preference management."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

AVAILABLE_QUOTES = ["USDT", "USDC", "EUR", "PLN"]
_MIN_BALANCE_THRESHOLD = 10.0
_CACHE_TTL_SECONDS = 300

_LOG_DIR = Path(__file__).resolve().parents[4] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
_DB_PATH = Path(__file__).resolve().parents[3] / "db" / "quote_prefs.db"
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

_cached_quote: Optional[str] = None
_cached_at: float = 0.0
_schema_initialized = False


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema() -> None:
    global _schema_initialized
    if _schema_initialized:
        return
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_preferences (
                user_id TEXT PRIMARY KEY,
                quote TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_runtime (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_balances (
                asset TEXT PRIMARY KEY,
                amount REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
    _schema_initialized = True


def _update_cache(quote: str) -> None:
    global _cached_quote, _cached_at
    _cached_quote = quote
    _cached_at = time.time()


def _store_runtime_value(key: str, value: Dict[str, object]) -> None:
    _ensure_schema()
    payload = json.dumps(value)
    now = time.time()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO quote_runtime(key, value, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """,
            (key, payload, now),
        )


def set_active_quote(quote: str, source: str = "manual") -> None:
    quote_upper = quote.upper()
    if quote_upper not in AVAILABLE_QUOTES:
        raise ValueError(f"Unsupported quote currency: {quote}")
    logger.info("Active quote set to %s (source=%s)", quote_upper, source)
    _store_runtime_value("active", {"quote": quote_upper, "source": source})
    _update_cache(quote_upper)


def _load_active_quote() -> Tuple[Optional[str], str]:
    _ensure_schema()
    with _connect() as conn:
        row = conn.execute(
            "SELECT value FROM quote_runtime WHERE key='active'"
        ).fetchone()
    if not row:
        return None, ""
    try:
        payload = json.loads(row["value"])
    except (TypeError, json.JSONDecodeError):
        return row["value"], ""
    return payload.get("quote"), str(payload.get("source", ""))


def set_user_quote(user_id: int | str, quote: str) -> None:
    quote_upper = quote.upper()
    if quote_upper not in AVAILABLE_QUOTES:
        raise ValueError("Unsupported quote currency")
    _ensure_schema()
    now = time.time()
    identifier = str(user_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO quote_preferences(user_id, quote, updated_at)
            VALUES(?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET quote=excluded.quote, updated_at=excluded.updated_at
            """,
            (identifier, quote_upper, now),
        )
    set_active_quote(quote_upper, source="user")


def get_user_quote(user_id: int | str) -> Optional[str]:
    _ensure_schema()
    identifier = str(user_id)
    with _connect() as conn:
        row = conn.execute(
            "SELECT quote FROM quote_preferences WHERE user_id=?",
            (identifier,),
        ).fetchone()
    if not row:
        return None
    return str(row["quote"])


def register_quote_balances(balances: Dict[str, Dict[str, float]]) -> None:
    """Persist snapshot of balances for quote detection."""
    if not isinstance(balances, dict):
        return
    _ensure_schema()
    now = time.time()
    with _connect() as conn:
        for asset, payload in balances.items():
            if asset.upper() not in AVAILABLE_QUOTES:
                continue
            free = float(payload.get("free", 0.0))
            locked = float(payload.get("locked", 0.0))
            amount = free + locked
            conn.execute(
                """
                INSERT INTO quote_balances(asset, amount, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(asset) DO UPDATE SET amount=excluded.amount, updated_at=excluded.updated_at
                """,
                (asset.upper(), amount, now),
            )


def _load_balance_snapshot() -> Dict[str, float]:
    _ensure_schema()
    with _connect() as conn:
        rows = conn.execute("SELECT asset, amount FROM quote_balances").fetchall()
    return {str(row["asset"]): float(row["amount"]) for row in rows}


def _detect_from_balances(snapshot: Dict[str, float]) -> Optional[str]:
    if not snapshot:
        return None
    ordered = ["USDT", "USDC", "EUR", "PLN"]
    for candidate in ordered:
        amount = float(snapshot.get(candidate, 0.0))
        if amount >= _MIN_BALANCE_THRESHOLD:
            return candidate
    for candidate in ordered:
        amount = float(snapshot.get(candidate, 0.0))
        if amount > 0:
            return candidate
    return None


def _default_quote() -> str:
    env_quote = os.getenv("DEFAULT_QUOTE", "USDT").upper()
    if env_quote in AVAILABLE_QUOTES:
        return env_quote
    return "USDT"


def get_current_quote(force_check: bool = False) -> str:
    """Return the active quote currency, auto-detecting when necessary."""
    global _cached_quote
    if (
        not force_check
        and _cached_quote
        and (time.time() - _cached_at) < _CACHE_TTL_SECONDS
    ):
        return _cached_quote

    active_quote, source = _load_active_quote()
    if active_quote and source != "auto":
        _update_cache(active_quote)
        return active_quote

    snapshot = _load_balance_snapshot() if force_check or not active_quote else {}
    detected = _detect_from_balances(snapshot) if snapshot else None

    if detected:
        set_active_quote(detected, source="auto")
        return detected

    if active_quote:
        _update_cache(active_quote)
        return active_quote

    fallback = _default_quote()
    set_active_quote(fallback, source="fallback")
    return fallback


def build_symbol(base: str, quote: Optional[str] = None) -> str:
    q = quote or get_current_quote()
    return f"{base.upper()}{q}"


def split_symbol(symbol: str) -> Tuple[str, str]:
    symbol_upper = symbol.upper()
    for candidate in sorted(AVAILABLE_QUOTES, key=len, reverse=True):
        if symbol_upper.endswith(candidate):
            return symbol_upper[: -len(candidate)], candidate
    if len(symbol_upper) > 4:
        return symbol_upper[:-4], symbol_upper[-4:]
    return symbol_upper, ""
