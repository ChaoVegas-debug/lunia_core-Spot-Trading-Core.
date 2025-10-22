from __future__ import annotations

import logging

import pytest
from app.ai.agents.regime_agent import RegimeAssessment
from app.ai.agents.risk_agent import RiskAssessment
from app.ai.agents.sentiment_agent import SentimentAssessment
from app.ai.consensus_engine import AgentOutcome, ConsensusEngine
from app.ai.orchestrator.orchestrator import AgentOrchestrator
from app.core.portfolio.portfolio import Portfolio


def test_consensus_engine_prefers_recent_accuracy() -> None:
    engine = ConsensusEngine(decay=0.6)
    for value in (1.0, 0.8, 0.9):
        engine.record_accuracy("risk", value)
    for value in (0.2, 0.1, 0.0):
        engine.record_accuracy("sentiment", value)

    result = engine.combine(
        [
            AgentOutcome(name="risk", score=0.8, confidence=0.85),
            AgentOutcome(name="sentiment", score=0.6, confidence=0.6),
        ]
    )

    assert result.weights["risk"] > result.weights["sentiment"]
    assert 0.0 <= result.confidence <= 1.0


class _StaticRiskAgent:
    def assess(self, asset, portfolio, *, equity, balances=None):
        return RiskAssessment(
            score=0.82,
            reason="Капитал в пределах лимитов",
            exposure_pct=12.0,
            leverage=1.2,
            compliant=True,
        )


class _StaticSentimentAgent:
    def assess(self, asset: str) -> SentimentAssessment:
        return SentimentAssessment(
            score=0.88,
            reason="Сильный позитивный сентимент",
            source="research",
            signals=[],
        )


class _StaticRegimeAgent:
    def assess(self, asset: str, price_history):
        return RegimeAssessment(
            score=0.76,
            reason="Устойчивый восходящий тренд",
            regime="uptrend",
            volatility=0.02,
        )


def test_orchestrator_produces_confident_payload(
    caplog: pytest.LogCaptureFixture,
) -> None:
    orchestrator = AgentOrchestrator(
        consensus_engine=ConsensusEngine(decay=0.7),
        risk_agent=_StaticRiskAgent(),
        sentiment_agent=_StaticSentimentAgent(),
        regime_agent=_StaticRegimeAgent(),
        history_limit=10,
        supervisor=None,
    )

    caplog.set_level(logging.INFO)
    payload = orchestrator.synthesise(
        "BTCUSDT",
        portfolio=Portfolio(),
        price_history=[30000, 30200, 30500, 30750, 31000, 31500],
        equity_usd=25_000,
        balances={"BTC": {"free": 0.5}},
    )

    assert payload["confidence"] > 0.7
    assert payload["regime"]["label"] == "uptrend"
    assert payload["risk_appetite"]["level"] == "high"
    assert any("confidence" in message for message in caplog.messages)
    assert len(orchestrator.history_snapshot()) == 1


class _FailingRiskAgent:
    def assess(
        self, asset, portfolio, *, equity, balances=None
    ):  # pragma: no cover - used in fallback test
        raise RuntimeError("risk agent offline")


class _FallbackSupervisor:
    def gather_signals(self, symbols=None):
        return {"signals": [{"strategy": "fallback", "bias": "NEUTRAL"}]}


def test_orchestrator_fallbacks_to_supervisor() -> None:
    orchestrator = AgentOrchestrator(
        consensus_engine=ConsensusEngine(decay=0.5),
        risk_agent=_FailingRiskAgent(),
        sentiment_agent=_StaticSentimentAgent(),
        regime_agent=_StaticRegimeAgent(),
        supervisor=_FallbackSupervisor(),
    )

    payload = orchestrator.synthesise("ETHUSDT", portfolio=Portfolio())

    assert payload["metadata"].get("fallback") is True
    assert payload["recommendations"]
    assert payload["confidence"] == 0.5
