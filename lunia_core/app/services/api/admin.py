"""Admin endpoints secured via token/RBAC."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.api.middleware.auth import AuthError, ensure_admin_access
from app.compat.flask import Blueprint, jsonify, request
from app.core.funds import FundsManager
from app.core.state import get_runtime_state
from app.core.strategy.manager import StrategyApplicator
from app.db import reporting

bp = Blueprint("admin", __name__, url_prefix="/admin")

_FUNDS_MANAGER: Optional[FundsManager] = None
_STRATEGY_APPLICATOR: Optional[StrategyApplicator] = None


def init_blueprint(manager: FundsManager, applicator: StrategyApplicator) -> Blueprint:
    """Initialise blueprint with dependencies."""

    global _FUNDS_MANAGER, _STRATEGY_APPLICATOR
    _FUNDS_MANAGER = manager
    _STRATEGY_APPLICATOR = applicator
    return bp


def _ensure_admin_actor() -> str:
    try:
        context = ensure_admin_access()
    except AuthError as exc:
        raise PermissionError(str(exc)) from exc
    return context.user_id if context else "admin-token"


def _collect_recent_users(search: str | None = None) -> List[Dict[str, Any]]:
    criteria = (search or "").strip().lower()
    seen: Dict[str, Dict[str, Any]] = {}

    if _STRATEGY_APPLICATOR is not None:
        for record in _STRATEGY_APPLICATOR.recent_changes(limit=100):
            actor = (record.get("actor") or "unknown").strip() or "unknown"
            if criteria and criteria not in actor.lower():
                continue
            entry = seen.setdefault(
                actor,
                {
                    "user_id": actor,
                    "sources": set(),
                    "last_action": None,
                    "last_seen": None,
                },
            )
            entry["sources"].add("strategy")
            entry["last_action"] = record.get("action")
            entry["last_seen"] = record.get("ts")

    try:
        trades = reporting.list_trades(limit=500)
    except Exception:  # pragma: no cover - offline DB errors are tolerated
        trades = []
    for trade in trades:
        actor = (trade.get("strategy") or "unknown").strip() or "unknown"
        if criteria and criteria not in actor.lower():
            continue
        entry = seen.setdefault(
            actor,
            {
                "user_id": actor,
                "sources": set(),
                "last_action": None,
                "last_seen": None,
            },
        )
        entry["sources"].add("trades")
        entry["last_action"] = "trade"
        entry["last_seen"] = trade.get("timestamp")

    results: List[Dict[str, Any]] = []
    for actor, data in seen.items():
        results.append(
            {
                "user_id": actor,
                "last_action": data.get("last_action"),
                "last_seen": data.get("last_seen"),
                "sources": sorted(data.get("sources", [])),
            }
        )
    results.sort(
        key=lambda item: (item.get("last_seen") or "", item.get("user_id") or ""),
        reverse=True,
    )
    return results


def _strategy_performance() -> List[Dict[str, Any]]:
    try:
        rows = reporting.list_trades(limit=5000)
    except Exception:  # pragma: no cover - offline DB errors are tolerated
        rows = []
    summary: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        strategy = (row.get("strategy") or "unknown").strip() or "unknown"
        stats = summary.setdefault(
            strategy, {"trades": 0, "total_pnl": 0.0, "last_trade": None}
        )
        stats["trades"] += 1
        try:
            stats["total_pnl"] += float(row.get("pnl") or 0.0)
        except (TypeError, ValueError):
            pass
        stats["last_trade"] = stats["last_trade"] or row.get("timestamp")
    ordered = [
        {
            "strategy": name,
            "trades": data["trades"],
            "total_pnl": round(float(data["total_pnl"]), 8),
            "last_trade": data["last_trade"],
        }
        for name, data in summary.items()
    ]
    ordered.sort(key=lambda item: item["total_pnl"], reverse=True)
    return ordered


@bp.get("/overview")
def get_overview():
    try:
        actor = _ensure_admin_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403

    state = get_runtime_state()
    funds = _FUNDS_MANAGER.load_current_limits() if _FUNDS_MANAGER else {}
    pending = _FUNDS_MANAGER.peek_preview() if _FUNDS_MANAGER else None
    recent = (
        list(_STRATEGY_APPLICATOR.recent_changes(limit=5))
        if _STRATEGY_APPLICATOR
        else []
    )

    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "actor": actor,
        "state": {
            "auto_mode": state.get("auto_mode"),
            "global_stop": state.get("global_stop"),
            "spot": state.get("spot", {}),
            "ops": state.get("ops", {}),
        },
        "funds": {"limits": funds, "pending": pending},
        "recent_strategy_changes": recent,
    }
    return jsonify(payload)


@bp.get("/users")
def get_users():
    try:
        _ensure_admin_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403

    search = request.args.get("search")
    users = _collect_recent_users(search)
    return jsonify({"count": len(users), "items": users})


@bp.get("/strategies/performance")
def get_strategy_performance():
    try:
        _ensure_admin_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403

    metrics = _strategy_performance()
    return jsonify({"count": len(metrics), "items": metrics})


@bp.errorhandler(PermissionError)
def _handle_permission(error: PermissionError):
    return jsonify({"error": str(error)}), 403


__all__ = ["init_blueprint", "bp"]
