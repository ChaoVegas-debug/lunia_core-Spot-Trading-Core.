"""Sandbox backtesting blueprint."""

from __future__ import annotations

import logging
from typing import Optional

from app.api.middleware.auth import AuthError, authenticate_request
from app.auth.rbac import Role
from app.backtester.engine import BacktestJobManager, BacktestRequest
from app.compat.flask import Blueprint, jsonify, request
from app.compat.pydantic import ValidationError
from app.services.api.schemas import (SandboxJobResponse, SandboxRunRequest,
                                      SandboxRunResponse)

logger = logging.getLogger(__name__)

bp = Blueprint("sandbox", __name__, url_prefix="/sandbox")

_MANAGER: Optional[BacktestJobManager] = None


def init_blueprint(manager: BacktestJobManager) -> Blueprint:
    global _MANAGER
    _MANAGER = manager
    return bp


def _require_manager() -> BacktestJobManager:
    if _MANAGER is None:
        raise RuntimeError("BacktestJobManager not initialised")
    return _MANAGER


def _auth(required_roles: set[Role], allow_lower: bool) -> None:
    authenticate_request(
        required_roles=required_roles,
        allow_viewer=allow_lower,
        allow_auditor=allow_lower,
    )


@bp.post("/run")
def run_backtest():
    try:
        _auth({Role.ADMIN, Role.OWNER}, allow_lower=True)
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 401

    manager = _require_manager()
    payload = request.get_json(force=True) or {}
    try:
        model = SandboxRunRequest.parse_obj(payload)
    except ValidationError as exc:
        logger.warning("sandbox.run.invalid %s", exc)
        return jsonify({"error": exc.errors()}), 400

    job = manager.submit(
        BacktestRequest(
            strategy=model.strategy,
            days=model.days,
            initial_capital=model.initial_capital,
        )
    )
    response = SandboxRunResponse(job_id=job.job_id, status=job.status)
    return jsonify(response.dict())


@bp.get("/<job_id>")
def get_job(job_id: str):
    try:
        _auth({Role.ADMIN, Role.OWNER}, allow_lower=True)
    except AuthError as exc:
        return jsonify({"error": str(exc)}), 401

    manager = _require_manager()
    data = manager.to_dict(job_id)
    if not data:
        return jsonify({"error": "job not found"}), 404
    response = SandboxJobResponse.parse_obj(data)
    return jsonify(response.dict())
