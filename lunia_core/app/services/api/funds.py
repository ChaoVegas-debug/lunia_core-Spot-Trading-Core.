"""Blueprint exposing funds in work controls."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.api.middleware.auth import AuthError, authenticate_request
from app.auth.rbac import Role
from app.compat.flask import Blueprint, jsonify, request
from app.core.funds import FundsManager
from app.core.utils.quote_detector import get_current_quote
from app.services.api.schemas import BalancesResponse

logger = logging.getLogger(__name__)

bp = Blueprint("funds", __name__, url_prefix="/funds")

_FUNDS_MANAGER: Optional[FundsManager] = None
_AGENT = None
_FUTURES_CLIENT = None


def init_blueprint(agent, futures_client, manager: FundsManager) -> Blueprint:
    global _FUNDS_MANAGER, _AGENT, _FUTURES_CLIENT
    _FUNDS_MANAGER = manager
    _AGENT = agent
    _FUTURES_CLIENT = futures_client
    return bp


def _require_manager() -> FundsManager:
    if _FUNDS_MANAGER is None:
        raise RuntimeError("FundsManager not initialised")
    return _FUNDS_MANAGER


def _get_actor() -> str:
    try:
        context = authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER}, allow_viewer=False
        )
        return context.user_id
    except AuthError as exc:  # pragma: no cover - handled in endpoint
        raise PermissionError(str(exc)) from exc


def _get_view_context(allow_lower: bool = True):
    try:
        return authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER},
            allow_viewer=allow_lower,
            allow_auditor=allow_lower,
        )
    except AuthError as exc:
        raise PermissionError(str(exc)) from exc


def _aggregate_balances() -> Dict[str, Any]:
    if _AGENT is None:
        raise RuntimeError("Agent not initialised")
    spot_balances = _AGENT.client.get_balances()
    aggregated: Dict[str, Dict[str, float]] = {}
    for asset, data in spot_balances.items():
        free = float(data.get("free", 0.0))
        locked = float(data.get("locked", 0.0))
        aggregated.setdefault(asset, {"total": 0.0})
        aggregated[asset]["total"] += free + locked
    futures_snapshot: Dict[str, Any] | None = None
    if _FUTURES_CLIENT is not None:
        try:
            futures_snapshot = _FUTURES_CLIENT.get_balance()
            asset = futures_snapshot.get("asset", get_current_quote())
            total = float(futures_snapshot.get("balance", 0.0))
            aggregated.setdefault(asset, {"total": 0.0})
            aggregated[asset]["total"] += total
        except Exception as exc:  # pragma: no cover - network failures fallback
            logger.warning("Unable to fetch futures balance: %s", exc)
            futures_snapshot = None
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "spot": spot_balances,
        "futures": futures_snapshot,
        "aggregated": {
            asset: {"total": round(data.get("total", 0.0), 8)}
            for asset, data in aggregated.items()
        },
    }


@bp.get("/limits")
def get_limits():
    try:
        _get_view_context(allow_lower=True)
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    manager = _require_manager()
    limits = manager.load_current_limits()
    pending = manager.peek_preview()
    response = {"limits": limits}
    if pending:
        response["pending_preview"] = pending
    return jsonify(response)


@bp.post("/limits/apply")
def post_limits_apply():
    try:
        actor = _get_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    manager = _require_manager()
    payload = request.get_json(force=True) or {}
    try:
        preview = manager.preview_changes(payload, actor=actor)
    except Exception as exc:  # pragma: no cover - validation errors
        logger.warning("Failed to preview funds limits: %s", exc)
        return jsonify({"error": str(exc)}), 400
    return jsonify(preview)


@bp.post("/limits/confirm")
def post_limits_confirm():
    try:
        actor = _get_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    manager = _require_manager()
    try:
        result = manager.confirm_changes(actor=actor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.post("/limits/undo")
def post_limits_undo():
    try:
        actor = _get_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    manager = _require_manager()
    try:
        result = manager.undo_changes(actor=actor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.get("/balances/check")
def get_balances_check():
    try:
        _get_view_context(allow_lower=True)
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401
    balances = _aggregate_balances()
    response = BalancesResponse(
        balances=[
            {"asset": asset, "free": data.get("total", 0.0), "locked": 0.0}
            for asset, data in balances["aggregated"].items()
        ]
    )
    payload = {
        "timestamp": balances["timestamp"],
        "spot": balances["spot"],
        "futures": balances.get("futures"),
        "aggregated": balances["aggregated"],
        "summary": response.dict(),
    }
    return jsonify(payload)


@bp.errorhandler(PermissionError)
def _handle_permission(error: PermissionError):
    return jsonify({"error": str(error)}), 403


__all__ = ["init_blueprint", "bp"]
