"""Portfolio explainability engine assembling insights from AI agents."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any, Dict, Iterable, List, Mapping, Optional

from ...core.portfolio.portfolio import Portfolio
from ...core.utils import split_symbol
from ...cores.llm import MultiLLMOrchestrator
from ..agents import (RegimeInsightAgent, RiskInsightAgent,
                      SentimentInsightAgent)

LOGGER = logging.getLogger(__name__)


@dataclass
class DecisionNode:
    name: str
    score: float
    reason: str
    payload: Dict[str, Any]


class PortfolioExplainabilityEngine:
    """Combine multiple AI agents to produce explanation trees."""

    def __init__(
        self,
        *,
        risk_agent: RiskInsightAgent | None = None,
        sentiment_agent: SentimentInsightAgent | None = None,
        regime_agent: RegimeInsightAgent | None = None,
        llm_orchestrator: MultiLLMOrchestrator | None = None,
    ) -> None:
        self.risk_agent = risk_agent or RiskInsightAgent()
        self.sentiment_agent = sentiment_agent or SentimentInsightAgent()
        self.regime_agent = regime_agent or RegimeInsightAgent()
        self.llm_orchestrator = llm_orchestrator

    def explain_asset(
        self,
        asset: str,
        portfolio: Portfolio,
        *,
        equity: float,
        balances: Optional[Mapping[str, Dict[str, float]]] = None,
        price_history: Iterable[float] | None = None,
        use_llm: bool = True,
    ) -> Dict[str, Any]:
        asset = asset.upper()
        balances_map: Dict[str, Dict[str, float]] = {}
        if balances:
            balances_map = {
                key.upper(): {
                    "free": float(val.get("free", 0.0)),
                    "locked": float(val.get("locked", 0.0)),
                }
                for key, val in balances.items()
            }

        risk_assessment = self.risk_agent.assess(
            asset,
            portfolio,
            equity=equity,
            balances=balances_map if balances_map else None,
        )
        sentiment_assessment = self.sentiment_agent.assess(asset)
        regime_assessment = self.regime_agent.assess(asset, price_history or [])

        nodes: List[DecisionNode] = [
            DecisionNode(
                name="risk",
                score=risk_assessment.score,
                reason=risk_assessment.reason,
                payload={
                    "exposure_pct": risk_assessment.exposure_pct,
                    "leverage": risk_assessment.leverage,
                    "compliant": risk_assessment.compliant,
                },
            ),
            DecisionNode(
                name="sentiment",
                score=sentiment_assessment.score,
                reason=sentiment_assessment.reason,
                payload={
                    "source": sentiment_assessment.source,
                    "signals": sentiment_assessment.signals,
                },
            ),
            DecisionNode(
                name="regime",
                score=regime_assessment.score,
                reason=regime_assessment.reason,
                payload={
                    "regime": regime_assessment.regime,
                    "volatility": regime_assessment.volatility,
                },
            ),
        ]

        confidence = mean(node.score for node in nodes)
        confidence = max(0.0, min(confidence, 1.0))

        base_summary = "; ".join(f"{node.name}: {node.reason}" for node in nodes)

        explanation: Dict[str, Any] = {
            "asset": asset,
            "base_asset": split_symbol(asset)[0],
            "confidence": round(confidence, 4),
            "decision_tree": [asdict(node) for node in nodes],
            "summary": base_summary,
        }

        if use_llm and self.llm_orchestrator is not None:
            try:
                prompt = (
                    f"Объясни текущее решение по {asset} на основе риска, настроений и режима."
                    f" Данные: {base_summary}."
                )
                llm_response = self.llm_orchestrator.route_signal(
                    {
                        "type": "explain",
                        "symbol": asset,
                        "prompt": prompt,
                        "context": explanation,
                    }
                )
                if llm_response:
                    explanation["llm_summary"] = (
                        llm_response.get("summary")
                        or llm_response.get("text")
                        or str(llm_response)
                    )
                    confidence_hint = llm_response.get("confidence")
                    if confidence_hint is not None:
                        try:
                            llm_confidence = float(confidence_hint)
                            explanation["confidence"] = round(
                                max(0.0, min((confidence + llm_confidence) / 2, 1.0)), 4
                            )
                        except (TypeError, ValueError):
                            LOGGER.debug(
                                "LLM confidence hint invalid: %s", confidence_hint
                            )
            except (
                Exception
            ) as exc:  # pragma: no cover - LLM failures not deterministic
                LOGGER.warning("LLM explanation failed: %s", exc)
                explanation["llm_summary"] = "LLM недоступен"

        return explanation
