"""Helpers for portfolio explanation endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from ..ai.explainability import PortfolioExplainabilityEngine
from ..core.portfolio.portfolio import Portfolio
from ..core.state import get_state as get_runtime_state
from ..cores.llm import MultiLLMOrchestrator

LOGGER = logging.getLogger(__name__)

_ORCHESTRATOR: Optional[MultiLLMOrchestrator] = None
_ENGINE: Optional[PortfolioExplainabilityEngine] = None


def _get_orchestrator() -> Optional[MultiLLMOrchestrator]:
    global _ORCHESTRATOR
    if _ORCHESTRATOR is None:
        try:
            _ORCHESTRATOR = MultiLLMOrchestrator()
        except Exception as exc:  # pragma: no cover - orchestration optional
            LOGGER.warning("LLM orchestrator unavailable: %s", exc)
            _ORCHESTRATOR = None
    return _ORCHESTRATOR


def get_engine() -> PortfolioExplainabilityEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = PortfolioExplainabilityEngine(llm_orchestrator=_get_orchestrator())
    return _ENGINE


def build_portfolio_explanation(
    asset: str,
    portfolio: Portfolio,
    *,
    equity_hint: Optional[float] = None,
    balances: Optional[Dict[str, Dict[str, float]]] = None,
    price_history: Iterable[float] | None = None,
) -> Dict[str, Any]:
    runtime = get_runtime_state()
    equity_default = float(runtime.get("portfolio_equity", 10_000.0))
    equity = equity_hint if equity_hint is not None else equity_default
    engine = get_engine()
    return engine.explain_asset(
        asset,
        portfolio,
        equity=equity,
        balances=balances,
        price_history=price_history,
    )
