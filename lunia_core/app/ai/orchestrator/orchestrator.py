"""Agent-level orchestrator that fuses multiple insight agents."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Mapping, MutableSequence, Optional, Sequence

from app.ai.agents import (RegimeInsightAgent, RiskInsightAgent,
                           SentimentInsightAgent)
from app.ai.agents.regime_agent import RegimeAssessment
from app.ai.agents.risk_agent import RiskAssessment
from app.ai.agents.sentiment_agent import SentimentAssessment
from app.ai.consensus_engine import (AgentOutcome, ConsensusEngine,
                                     ConsensusResult)
from app.compat.dotenv import load_dotenv
from app.core.portfolio.portfolio import Portfolio

try:  # pragma: no cover - optional supervisor fallback
    from app.core.ai.supervisor import Supervisor
except Exception:  # pragma: no cover
    Supervisor = None  # type: ignore

load_dotenv()

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentSnapshot:
    name: str
    outcome: AgentOutcome


class AgentOrchestrator:
    """Aggregate insight agents and return consensus suitable for dashboards."""

    def __init__(
        self,
        *,
        consensus_engine: ConsensusEngine | None = None,
        risk_agent: RiskInsightAgent | None = None,
        sentiment_agent: SentimentInsightAgent | None = None,
        regime_agent: RegimeInsightAgent | None = None,
        supervisor: Optional[Supervisor] = None,
        history_limit: int = 256,
    ) -> None:
        self.consensus = consensus_engine or ConsensusEngine()
        self.risk_agent = risk_agent or RiskInsightAgent()
        self.sentiment_agent = sentiment_agent or SentimentInsightAgent()
        self.regime_agent = regime_agent or RegimeInsightAgent()
        self.supervisor = supervisor or (
            Supervisor() if Supervisor is not None else None
        )
        self.history: MutableSequence[Dict[str, object]] = []
        self.history_limit = max(10, history_limit)

    def synthesise(
        self,
        asset: str,
        *,
        portfolio: Optional[Portfolio] = None,
        price_history: Optional[Sequence[float]] = None,
        equity_usd: float = 10_000.0,
        balances: Optional[Mapping[str, Mapping[str, float]]] = None,
        metadata: Optional[Mapping[str, object]] = None,
    ) -> Dict[str, object]:
        portfolio = portfolio or Portfolio()
        price_history = price_history or []
        balances = balances or {}
        metadata = metadata or {}
        asset = asset.upper()

        try:
            risk = self._assess_risk(asset, portfolio, equity_usd, balances)
            sentiment = self.sentiment_agent.assess(asset)
            regime = self.regime_agent.assess(asset, price_history)
            agent_snapshots = self._build_outcomes(risk, sentiment, regime)
            consensus = self.consensus.combine(
                [snapshot.outcome for snapshot in agent_snapshots]
            )
            for snapshot in agent_snapshots:
                self.consensus.record_accuracy(
                    snapshot.name, snapshot.outcome.confidence
                )
            payload = self._compose_payload(
                asset=asset,
                risk=risk,
                sentiment=sentiment,
                regime=regime,
                consensus=consensus,
                metadata=metadata,
            )
            self._remember(payload)
            LOGGER.info(
                "Orchestrator consensus asset=%s regime=%s confidence=%.3f",
                asset,
                payload["regime"].get("label"),
                payload["confidence"],
            )
            return payload
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Orchestrator failed for %s: %s", asset, exc)
            return self._fallback_payload(asset)

    # ------------------------------------------------------------------
    def _assess_risk(
        self,
        asset: str,
        portfolio: Portfolio,
        equity_usd: float,
        balances: Mapping[str, Mapping[str, float]],
    ) -> RiskAssessment:
        return self.risk_agent.assess(
            asset, portfolio, equity=equity_usd, balances=balances
        )

    def _build_outcomes(
        self,
        risk: RiskAssessment,
        sentiment: SentimentAssessment,
        regime: RegimeAssessment,
    ) -> Sequence[AgentSnapshot]:
        snapshots: list[AgentSnapshot] = []
        snapshots.append(
            AgentSnapshot(
                name="risk",
                outcome=AgentOutcome(
                    name="risk",
                    score=risk.score,
                    confidence=0.9 if risk.compliant else 0.4,
                    uncertainty=max(0.0, 1.0 - risk.score),
                    payload={"reason": risk.reason, "exposure_pct": risk.exposure_pct},
                ),
            )
        )
        snapshots.append(
            AgentSnapshot(
                name="sentiment",
                outcome=AgentOutcome(
                    name="sentiment",
                    score=sentiment.score,
                    confidence=sentiment.score,
                    uncertainty=max(0.0, 1.0 - sentiment.score),
                    payload={"reason": sentiment.reason, "source": sentiment.source},
                ),
            )
        )
        snapshots.append(
            AgentSnapshot(
                name="regime",
                outcome=AgentOutcome(
                    name="regime",
                    score=regime.score,
                    confidence=1.0 - min(1.0, abs(regime.volatility)),
                    uncertainty=max(0.1, min(0.9, abs(regime.volatility) / 10)),
                    payload={"reason": regime.reason, "regime": regime.regime},
                ),
            )
        )
        return snapshots

    def _compose_payload(
        self,
        *,
        asset: str,
        risk: RiskAssessment,
        sentiment: SentimentAssessment,
        regime: RegimeAssessment,
        consensus: ConsensusResult,
        metadata: Mapping[str, object],
    ) -> Dict[str, object]:
        timestamp = datetime.utcnow().isoformat()
        risk_level = self._risk_level(risk.score)
        recommendations = self._build_recommendations(
            risk, sentiment, regime, consensus
        )
        result = {
            "asset": asset,
            "timestamp": timestamp,
            "regime": {
                "label": regime.regime,
                "score": round(regime.score, 4),
                "volatility": regime.volatility,
                "reason": regime.reason,
            },
            "sentiment": {
                "score": round(sentiment.score, 4),
                "reason": sentiment.reason,
                "source": sentiment.source,
            },
            "risk_appetite": {
                "level": risk_level,
                "score": round(risk.score, 4),
                "reason": risk.reason,
                "exposure_pct": risk.exposure_pct,
                "leverage": risk.leverage,
            },
            "recommendations": recommendations,
            "confidence": consensus.confidence,
            "aggregate_score": consensus.aggregate_score,
            "weights": consensus.weights,
            "metadata": dict(metadata),
        }
        return result

    def _risk_level(self, score: float) -> str:
        if score >= 0.75:
            return "high"
        if score >= 0.5:
            return "balanced"
        return "defensive"

    def _build_recommendations(
        self,
        risk: RiskAssessment,
        sentiment: SentimentAssessment,
        regime: RegimeAssessment,
        consensus: ConsensusResult,
    ) -> Sequence[Dict[str, object]]:
        items: list[Dict[str, object]] = []
        weights = consensus.weights or {}
        if (
            sentiment.score >= 0.65
            and regime.regime == "uptrend"
            and risk.score >= 0.55
        ):
            items.append(
                {
                    "strategy": "trend_following",
                    "bias": "LONG",
                    "weight": round(weights.get("sentiment", 1.0), 4),
                    "reason": "Позитивный сентимент и восходящий тренд",
                }
            )
        if regime.regime == "downtrend" or risk.score < 0.45:
            items.append(
                {
                    "strategy": "risk_overlay",
                    "bias": "HEDGE",
                    "weight": round(weights.get("risk", 1.0), 4),
                    "reason": "Риск-менеджер рекомендует защиту",
                }
            )
        if not items:
            items.append(
                {
                    "strategy": "range_scalping",
                    "bias": "NEUTRAL",
                    "weight": round(weights.get("regime", 1.0), 4),
                    "reason": "Флэтовый рынок — допускается нейтральная стратегия",
                }
            )
        return items

    def _remember(self, payload: Mapping[str, object]) -> None:
        self.history.append(dict(payload))
        if len(self.history) > self.history_limit:
            del self.history[: len(self.history) - self.history_limit]

    def _fallback_payload(self, asset: str) -> Dict[str, object]:
        if self.supervisor is not None:
            try:
                snapshot = self.supervisor.gather_signals(symbols=[asset])
                return {
                    "asset": asset,
                    "timestamp": datetime.utcnow().isoformat(),
                    "regime": {
                        "label": "unknown",
                        "score": 0.0,
                        "volatility": 0.0,
                        "reason": "fallback",
                    },
                    "sentiment": {
                        "score": 0.5,
                        "reason": "fallback",
                        "source": "supervisor",
                    },
                    "risk_appetite": {
                        "level": "balanced",
                        "score": 0.5,
                        "reason": "fallback",
                        "exposure_pct": 0.0,
                        "leverage": 0.0,
                    },
                    "recommendations": snapshot.get("signals", []),
                    "confidence": 0.5,
                    "aggregate_score": 0.5,
                    "weights": {"supervisor": 1.0},
                    "metadata": {"fallback": True},
                }
            except Exception:  # pragma: no cover - supervisor may be absent
                pass
        return {
            "asset": asset,
            "timestamp": datetime.utcnow().isoformat(),
            "regime": {
                "label": "unknown",
                "score": 0.0,
                "volatility": 0.0,
                "reason": "orchestrator-error",
            },
            "sentiment": {"score": 0.5, "reason": "no-data", "source": "fallback"},
            "risk_appetite": {
                "level": "balanced",
                "score": 0.5,
                "reason": "fallback",
                "exposure_pct": 0.0,
                "leverage": 0.0,
            },
            "recommendations": [],
            "confidence": 0.5,
            "aggregate_score": 0.5,
            "weights": {},
            "metadata": {"fallback": True},
        }

    def record_feedback(self, outcomes: Mapping[str, bool]) -> None:
        for agent, success in outcomes.items():
            self.consensus.record_accuracy(agent, 1.0 if success else 0.0)

    def history_snapshot(self) -> Sequence[Dict[str, object]]:
        return tuple(self.history)
