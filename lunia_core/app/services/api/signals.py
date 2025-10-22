"""Signals API blueprint providing enriched explainable cards."""

from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

from app.api.middleware.auth import AuthError, authenticate_request
from app.auth.rbac import Role
from app.compat.flask import Blueprint, jsonify, request
from app.core.metrics import explain_card_render_duration_seconds

try:  # pragma: no cover - optional orchestrator availability
    from app.ai.orchestrator import AGENT_ORCHESTRATOR as DEFAULT_ORCHESTRATOR
except Exception:  # pragma: no cover - orchestrator not bundled
    DEFAULT_ORCHESTRATOR = None  # type: ignore

LOGGER = logging.getLogger(__name__)

bp = Blueprint("signals", __name__, url_prefix="/signals")

_AGENT = None
_SUPERVISOR = None
_ORCHESTRATOR = DEFAULT_ORCHESTRATOR


def init_blueprint(agent, supervisor, orchestrator=None) -> Blueprint:
    """Initialise the signals blueprint with shared runtime dependencies."""

    global _AGENT, _SUPERVISOR, _ORCHESTRATOR
    _AGENT = agent
    _SUPERVISOR = supervisor
    if orchestrator is not None:
        _ORCHESTRATOR = orchestrator
    return bp


def _require_supervisor():
    if _SUPERVISOR is None:
        raise RuntimeError("Supervisor not initialised")
    return _SUPERVISOR


def _require_agent():
    if _AGENT is None:
        raise RuntimeError("Agent not initialised")
    return _AGENT


def _authorise_view() -> None:
    try:
        authenticate_request(
            required_roles={Role.ADMIN, Role.OWNER},
            allow_viewer=True,
            allow_auditor=True,
        )
    except AuthError as exc:
        LOGGER.warning("Signals request denied: %s", exc)
        raise PermissionError(str(exc)) from exc


def _normalize_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    if score <= 0:
        return 0.0
    if score <= 1:
        return round(min(score, 1.0), 4)
    # squeeze to (0,1)
    return round(min(score / (abs(score) + 1.0), 1.0), 4)


def _gather_consensus(symbol: str) -> Optional[Dict[str, Any]]:
    orchestrator = _ORCHESTRATOR
    if orchestrator is None:
        return None
    try:
        agent = _require_agent()
        supervisor = _require_supervisor()
        price_history = list(supervisor.price_history.get(symbol, []))
        balances = {}
        try:
            balances = agent.client.get_balances()  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - network failure fallback
            LOGGER.debug("Unable to fetch balances for consensus: %s", exc)
        portfolio = getattr(agent, "portfolio", None)
        equity = getattr(agent, "default_equity_usd", 10_000.0)
        return orchestrator.synthesise(
            symbol,
            portfolio=portfolio,
            price_history=price_history,
            equity_usd=equity,
            balances=balances,
            metadata={"source": "signals-api"},
        )
    except Exception as exc:  # pragma: no cover - orchestrator optional
        LOGGER.debug("Consensus synthesis failed for %s: %s", symbol, exc)
        return None


def _build_layers(
    signal: Mapping[str, Any], consensus: Optional[Mapping[str, Any]]
) -> Dict[str, Any]:
    side = str(signal.get("side", "")).upper() or "BUY"
    symbol = str(signal.get("symbol", ""))
    strategy = str(signal.get("strategy", "generic"))
    stop_pct = float(signal.get("stop_pct") or 0.0) * 100
    take_pct = float(signal.get("take_pct") or 0.0) * 100
    base_reason = ""
    if consensus:
        regime = consensus.get("regime", {})
        sentiment = consensus.get("sentiment", {})
        base_reason = f"Regime: {regime.get('label', 'neutral')} — Sentiment: {sentiment.get('score', 0):.2f}."
    beginner_summary = f"{side} {symbol} with target {take_pct:.1f}% and stop {stop_pct:.1f}% because momentum and risk checks align."
    if base_reason:
        beginner_summary += f" {base_reason}"

    trader_points: List[str] = []
    if consensus:
        risk_appetite = consensus.get("risk_appetite", {})
        trader_points.append(
            f"Risk level {risk_appetite.get('level', 'balanced')} with exposure {risk_appetite.get('exposure_pct', 0)}%."
        )
        trader_points.append(
            f"Confidence {consensus.get('confidence', 0.0):.2f}, aggregate score {consensus.get('aggregate_score', 0.0):.2f}."
        )
        trader_points.append(
            f"Strategy weight hint {consensus.get('weights', {}).get(strategy.split(':')[0], 0):.2f}."
        )
    else:
        trader_points.append(
            "Consensus data unavailable; using supervisor scores only."
        )

    pro_insights: Dict[str, Any] = {
        "strategy": strategy,
        "market_context": consensus.get("regime") if consensus else None,
        "weights": consensus.get("weights") if consensus else {},
    }

    return {
        "beginner": {
            "title": "Beginner",
            "summary": beginner_summary,
        },
        "trader": {
            "title": "Trader",
            "summary": "Focus on execution discipline and key metrics.",
            "bullets": trader_points,
        },
        "pro": {
            "title": "Pro",
            "summary": "Detailed context for discretionary overlay.",
            "details": pro_insights,
        },
    }


def _build_risk_metrics(
    signal: Mapping[str, Any], consensus: Optional[Mapping[str, Any]]
) -> Dict[str, Any]:
    notional = float(signal.get("notional_usd") or 0.0)
    qty = float(signal.get("qty") or 0.0)
    stop_pct = float(signal.get("stop_pct") or 0.0)
    take_pct = float(signal.get("take_pct") or 0.0)
    risk_reward = None
    if stop_pct > 0:
        risk_reward = round(take_pct / stop_pct, 3)
    metrics: Dict[str, Any] = {
        "notional_usd": round(notional, 2),
        "position_size": round(qty, 8),
        "stop_loss_pct": round(stop_pct * 100, 2),
        "take_profit_pct": round(take_pct * 100, 2),
        "value_at_risk_usd": round(notional * stop_pct, 2),
    }
    if risk_reward is not None and math.isfinite(risk_reward):
        metrics["risk_reward_ratio"] = risk_reward
    if consensus:
        risk_appetite = consensus.get("risk_appetite", {})
        regime = consensus.get("regime", {})
        metrics.update(
            {
                "exposure_pct": risk_appetite.get("exposure_pct"),
                "leverage": risk_appetite.get("leverage"),
                "regime_volatility": regime.get("volatility"),
            }
        )
    return {k: v for k, v in metrics.items() if v is not None}


def _build_scenarios(
    signal: Mapping[str, Any],
    consensus: Optional[Mapping[str, Any]],
    certainty: float,
) -> List[Dict[str, Any]]:
    base_case = {
        "label": "Base case",
        "probability": round(certainty, 3),
        "action": "Execute",
        "summary": "Signal confidence above threshold; proceed with planned sizing.",
    }
    alt_probability = round(max(0.05, 1.0 - certainty) / 2, 3)
    downside = {
        "label": "Volatility spike",
        "probability": alt_probability,
        "action": "Defer",
        "summary": "Watch for increased volatility or liquidity gaps before entry.",
    }
    reversal = {
        "label": "Trend reversal",
        "probability": alt_probability,
        "action": "Decline",
        "summary": "Momentum fades or macro backdrop shifts; stand aside.",
    }
    if consensus and consensus.get("risk_appetite", {}).get("level") == "high":
        downside["action"] = "Reduce size"
    return [base_case, downside, reversal]


def _decorate_signal(signal: Mapping[str, Any]) -> Dict[str, Any]:
    enriched = dict(signal)
    symbol = str(enriched.get("symbol", "")).upper() or "BTCUSDT"
    consensus = _gather_consensus(symbol)
    signal_score = _normalize_score(enriched.get("score"))
    consensus_conf = _normalize_score(consensus.get("confidence")) if consensus else 0.0
    certainty = round(
        (signal_score + consensus_conf) / 2 if consensus else signal_score, 4
    )
    enriched["certainty_score"] = certainty
    enriched["explanation_layers"] = _build_layers(enriched, consensus)
    enriched["risk_metrics"] = _build_risk_metrics(enriched, consensus)
    enriched["alternative_scenarios"] = _build_scenarios(enriched, consensus, certainty)
    enriched.setdefault("generated_at", datetime.utcnow().isoformat())
    return enriched


@bp.get("/")
def list_signals():
    try:
        _authorise_view()
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 401

    status = (request.args.get("status") or "pending").lower()
    if status not in {"pending", "all"}:
        return jsonify({"error": "unsupported status"}), 400

    supervisor = _require_supervisor()
    try:
        payload = (
            supervisor.gather_signals()
            if status == "pending"
            else supervisor.get_signals()
        )
    except (
        Exception
    ) as exc:  # pragma: no cover - supervisor failures should be reported
        LOGGER.error("Failed to gather signals: %s", exc)
        return jsonify({"error": "unable to gather signals"}), 500

    raw_signals: Iterable[Mapping[str, Any]] = (
        payload.get("signals", []) if isinstance(payload, Mapping) else []
    )
    enriched = []
    for entry in raw_signals:
        start = time.perf_counter()
        decorated = _decorate_signal(entry)
        duration = max(time.perf_counter() - start, 0.0)
        try:
            explain_card_render_duration_seconds.observe(duration)
        except Exception:
            LOGGER.debug("Unable to record explain-card metric", exc_info=True)
        enriched.append(decorated)
    return jsonify(enriched)


@bp.errorhandler(PermissionError)
def _handle_permission(error: PermissionError):
    return jsonify({"error": str(error)}), 403


__all__ = ["init_blueprint", "bp"]
