"""Flask blueprint (and optional FastAPI router) exposing cores endpoints."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

try:  # pragma: no cover - optional FastAPI support
    from fastapi import APIRouter, HTTPException
except Exception:  # pragma: no cover
    APIRouter = None  # type: ignore
    HTTPException = Exception  # type: ignore

from app.backup import (BackupStorage, IntelligentRecoveryEngine,
                        SmartBackupManager)
from app.compat.flask import Blueprint, Response, jsonify, request
from app.cores.backtest import BacktestRunner
from app.cores.llm import MultiLLMOrchestrator
from app.monitoring.metrics import MONITORING
from app.self_healing import (ComprehensiveHealthMonitor,
                              IntelligentAutoRecovery)

from ..runtime.registry import REGISTRY
from ..runtime.supervisor import SUPERVISOR
from ..signals.schema import RiskEnvelope, Signal
from .models import (BackupRequest, CoreSnapshot, CoreStatus, RecoveryRequest,
                     SignalRequest, ToggleRequest, WeightRequest)

LOGGER = logging.getLogger(__name__)
blueprint = Blueprint("cores", __name__)
monitor = ComprehensiveHealthMonitor()
auto_recovery = IntelligentAutoRecovery()
backup_manager = SmartBackupManager()
recovery_engine = IntelligentRecoveryEngine()
storage = BackupStorage()
backtest_runner = BacktestRunner()
llm_orchestrator = MultiLLMOrchestrator()
OPS_TOKEN = os.getenv("OPS_API_TOKEN")


def _require_token() -> Any:
    if not OPS_TOKEN:
        return None
    header = request.headers.get("Authorization", "")
    if header != f"Bearer {OPS_TOKEN}":
        return jsonify({"error": "forbidden"}), 403
    return None


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
    return loop.run_until_complete(coro)


@blueprint.route("/cores/", methods=["GET"])
def list_cores() -> Any:
    snapshot = {
        name: CoreStatus(**payload) for name, payload in SUPERVISOR.snapshot().items()
    }
    return jsonify(CoreSnapshot(cores=snapshot).dict())


@blueprint.route("/cores/<name>/toggle", methods=["POST"])
def toggle_core(name: str) -> Any:
    payload = ToggleRequest.parse_obj(request.json or {})
    if name not in REGISTRY.names():
        return jsonify({"error": "unknown core"}), 404
    REGISTRY.toggle(name, payload.enabled)
    return jsonify({"name": name, "enabled": payload.enabled})


@blueprint.route("/cores/<name>/weight", methods=["POST"])
def update_weight(name: str) -> Any:
    payload = WeightRequest.parse_obj(request.json or {})
    if name not in REGISTRY.names():
        return jsonify({"error": "unknown core"}), 404
    REGISTRY.set_weight(name, payload.weight)
    return jsonify({"name": name, "weight": payload.weight})


@blueprint.route("/signals/ingest", methods=["POST"])
def ingest_signal() -> Any:
    data = SignalRequest.parse_obj(request.json or {})
    signal = Signal(
        type=data.type,
        target_core=data.target_core,
        symbol=data.symbol,
        side=data.side,
        confidence=data.confidence,
        reason=data.reason,
        correlation_id=data.correlation_id,
        timeframe=data.timeframe,
        metadata=data.metadata,
        risk=RiskEnvelope(**data.risk),
    )

    async def _dispatch() -> None:
        await SUPERVISOR.start()
        await REGISTRY.dispatch(signal)

    import asyncio

    asyncio.get_event_loop().create_task(_dispatch())
    return jsonify({"status": "accepted", "target": signal.target_core})


@blueprint.route("/system/health", methods=["GET"])
def system_health() -> Any:
    if (error := _require_token()) is not None:
        return error
    report = _run_async(monitor.perform_health_check())
    return jsonify(report.to_dict())


@blueprint.route("/system/backup", methods=["POST"])
def create_backup() -> Any:
    if (error := _require_token()) is not None:
        return error
    payload = BackupRequest.parse_obj(request.json or {})
    result = backup_manager.execute_smart_backup(trigger=payload.trigger or "auto")
    return jsonify(result.to_dict())


@blueprint.route("/system/recover", methods=["POST"])
def recover_system() -> Any:
    if (error := _require_token()) is not None:
        return error
    payload = RecoveryRequest.parse_obj(request.json or {})
    if payload.issue_type == "restore":
        result = recovery_engine.restore_to_optimal_state()
        return jsonify(result.to_dict())
    outcome = _run_async(
        auto_recovery.execute_recovery(payload.issue_type, payload.context)
    )
    return jsonify(outcome.to_dict())


@blueprint.route("/system/backups", methods=["GET"])
def list_backups() -> Any:
    if (error := _require_token()) is not None:
        return error
    backups = [meta.to_dict() for meta in storage.list_backups()]
    return jsonify({"backups": backups})


@blueprint.route("/backtest/results", methods=["GET"])
def backtest_results() -> Any:
    if (error := _require_token()) is not None:
        return error
    reports = backtest_runner.latest_reports()
    summary = (
        backtest_runner.reporter.generate_metrics_summary(
            [report.get("metrics", {}) for report in reports]
        )
        if reports
        else {}
    )
    return jsonify({"reports": reports, "summary": summary})


@blueprint.route("/llm/stats", methods=["GET"])
def llm_stats() -> Any:
    if (error := _require_token()) is not None:
        return error
    return jsonify(llm_orchestrator.evaluate_models())


@blueprint.route("/metrics", methods=["GET"])
def metrics() -> Any:
    data = MONITORING.export()
    return Response(data, mimetype="text/plain")


def get_fastapi_router() -> "APIRouter":  # pragma: no cover - optional
    if APIRouter is None:
        raise RuntimeError("FastAPI not available in this environment")
    router = APIRouter(prefix="/cores", tags=["cores"])

    @router.get("/")
    async def _list() -> Dict[str, Dict[str, Any]]:
        return SUPERVISOR.snapshot()

    @router.post("/{name}/toggle")
    async def _toggle(name: str, request_model: ToggleRequest) -> Dict[str, Any]:
        if name not in REGISTRY.names():
            raise HTTPException(status_code=404, detail="Unknown core")
        REGISTRY.toggle(name, request_model.enabled)
        return {"name": name, "enabled": request_model.enabled}

    @router.post("/{name}/weight")
    async def _weight(name: str, request_model: WeightRequest) -> Dict[str, Any]:
        if name not in REGISTRY.names():
            raise HTTPException(status_code=404, detail="Unknown core")
        REGISTRY.set_weight(name, request_model.weight)
        return {"name": name, "weight": request_model.weight}

    @router.post("/signals/ingest")
    async def _ingest(request_model: SignalRequest) -> Dict[str, Any]:
        signal = Signal(
            type=request_model.type,
            target_core=request_model.target_core,
            symbol=request_model.symbol,
            side=request_model.side,
            confidence=request_model.confidence,
            reason=request_model.reason,
            correlation_id=request_model.correlation_id,
            timeframe=request_model.timeframe,
            metadata=request_model.metadata,
            risk=RiskEnvelope(**request_model.risk),
        )
        await SUPERVISOR.start()
        await REGISTRY.dispatch(signal)
        return {"status": "accepted", "target": signal.target_core}

    @router.get("/system/health")
    async def _system_health() -> Dict[str, Any]:
        report = await monitor.perform_health_check()
        return report.to_dict()

    @router.post("/system/backup")
    async def _system_backup(req: BackupRequest) -> Dict[str, Any]:
        result = backup_manager.execute_smart_backup(trigger=req.trigger or "auto")
        return result.to_dict()

    @router.post("/system/recover")
    async def _system_recover(req: RecoveryRequest) -> Dict[str, Any]:
        if req.issue_type == "restore":
            return recovery_engine.restore_to_optimal_state().to_dict()
        outcome = await auto_recovery.execute_recovery(req.issue_type, req.context)
        return outcome.to_dict()

    @router.get("/system/backups")
    async def _system_backups() -> Dict[str, Any]:
        return {"backups": [meta.to_dict() for meta in storage.list_backups()]}

    @router.get("/backtest/results")
    async def _backtest_results() -> Dict[str, Any]:
        reports = backtest_runner.latest_reports()
        summary = (
            backtest_runner.reporter.generate_metrics_summary(
                [report.get("metrics", {}) for report in reports]
            )
            if reports
            else {}
        )
        return {"reports": reports, "summary": summary}

    @router.get("/llm/stats")
    async def _llm_stats() -> Dict[str, Any]:
        return llm_orchestrator.evaluate_models()

    return router


__all__ = ["blueprint", "get_fastapi_router"]
