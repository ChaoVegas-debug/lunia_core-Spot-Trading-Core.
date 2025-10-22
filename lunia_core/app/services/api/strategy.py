"""Strategy management API (preview/assign/undo)."""

from __future__ import annotations

import logging
from typing import Dict, Optional

from app.api.middleware.auth import AuthError, authenticate_request
from app.auth.rbac import Role
from app.compat.flask import Blueprint, jsonify, request
from app.core.strategy import StrategyApplicator

logger = logging.getLogger(__name__)

bp = Blueprint("strategy", __name__)

_MANAGER: Optional[StrategyApplicator] = None


def init_blueprint(manager: StrategyApplicator | None = None) -> Blueprint:
    """Initialise blueprint with a shared strategy manager instance."""

    global _MANAGER
    _MANAGER = manager or StrategyApplicator()
    return bp


def _require_manager() -> StrategyApplicator:
    if _MANAGER is None:
        raise RuntimeError("Strategy manager not initialised")
    return _MANAGER


def _get_actor() -> str:
    try:
        context = authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER}, allow_viewer=False
        )
        return context.user_id
    except AuthError as exc:  # pragma: no cover - handled at endpoint level
        raise PermissionError(str(exc)) from exc


def _get_view_context():
    try:
        authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER},
            allow_viewer=True,
            allow_auditor=True,
        )
    except AuthError as exc:
        raise PermissionError(str(exc)) from exc


@bp.post("/strategy/apply")
def post_strategy_apply():
    try:
        actor = _get_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401

    manager = _require_manager()
    payload: Dict[str, object] = request.get_json(force=True) or {}
    try:
        preview = manager.preview(payload, actor=actor)
    except ValueError as exc:
        logger.warning("Strategy preview failed: %s", exc)
        return jsonify({"error": str(exc)}), 400
    return jsonify(preview)


@bp.post("/strategy/assign")
def post_strategy_assign():
    try:
        actor = _get_actor()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401

    manager = _require_manager()
    payload: Dict[str, object] = request.get_json(force=True) or {}
    try:
        result = manager.assign(payload, actor=actor)
    except ValueError as exc:
        logger.warning("Strategy assign failed: %s", exc)
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@bp.get("/portfolio/changes")
def get_portfolio_changes():
    try:
        _get_view_context()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401

    manager = _require_manager()
    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        limit = 20
    limit = max(1, min(limit, 200))
    changes = list(manager.recent_changes(limit=limit))
    return jsonify({"changes": changes, "count": len(changes), "limit": limit})


@bp.errorhandler(PermissionError)
def _handle_permission(error: PermissionError):
    return jsonify({"error": str(error)}), 403


__all__ = ["init_blueprint", "bp"]
