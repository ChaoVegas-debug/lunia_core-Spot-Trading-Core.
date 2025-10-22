"""Consensus engine aggregating agent outcomes with decay-weighted accuracy."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AgentOutcome:
    """Represents a single agent evaluation used during consensus."""

    name: str
    score: float
    confidence: float
    uncertainty: float | None = None
    payload: Mapping[str, object] | None = None

    def normalised_score(self) -> float:
        return max(0.0, min(float(self.score), 1.0))

    def normalised_confidence(self) -> float:
        return max(0.0, min(float(self.confidence), 1.0))

    def normalised_uncertainty(self) -> float:
        if self.uncertainty is not None:
            return max(0.0, min(float(self.uncertainty), 1.0))
        return 1.0 - self.normalised_confidence()


@dataclass(frozen=True)
class ConsensusResult:
    """Aggregated consensus output for downstream consumers."""

    aggregate_score: float
    confidence: float
    uncertainty: float
    weights: Mapping[str, float]

    def as_dict(self) -> Dict[str, object]:
        return {
            "aggregate_score": self.aggregate_score,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "weights": dict(self.weights),
        }


class ConsensusEngine:
    """Fuse heterogeneous agent outcomes into a single confidence score."""

    def __init__(self, *, decay: float = 0.7, max_history: int = 50) -> None:
        self.decay = max(0.1, min(decay, 0.99))
        self.max_history = max(1, max_history)
        self._accuracy_history: Dict[str, List[float]] = {}

    def record_accuracy(self, agent: str, accuracy: float) -> None:
        """Persist recent accuracy so weights reflect fresh performance."""

        history = self._accuracy_history.setdefault(agent, [])
        history.append(max(0.0, min(float(accuracy), 1.0)))
        if len(history) > self.max_history:
            del history[: -self.max_history]
        logger.debug("Recorded accuracy for %s: %.4f", agent, history[-1])

    def weight_for(self, agent: str) -> float:
        history = self._accuracy_history.get(agent)
        if not history:
            return 1.0
        weighted = 0.0
        norm = 0.0
        for index, value in enumerate(reversed(history)):
            coeff = self.decay**index
            weighted += value * coeff
            norm += coeff
        normalised = weighted / norm if norm else sum(history) / len(history)
        return max(0.05, round(normalised, 6))

    def combine(self, outcomes: Sequence[AgentOutcome]) -> ConsensusResult:
        if not outcomes:
            return ConsensusResult(
                aggregate_score=0.0, confidence=0.0, uncertainty=1.0, weights={}
            )

        weights: Dict[str, float] = {}
        weighted_score = 0.0
        weighted_confidence = 0.0
        uncertainties: List[float] = []

        for outcome in outcomes:
            weight = self.weight_for(outcome.name)
            weights[outcome.name] = weight
            weighted_score += weight * outcome.normalised_score()
            weighted_confidence += weight * outcome.normalised_confidence()
            uncertainties.append(outcome.normalised_uncertainty())
            logger.debug(
                "Outcome %s -> score=%.3f confidence=%.3f weight=%.3f",
                outcome.name,
                outcome.score,
                outcome.confidence,
                weight,
            )

        total_weight = sum(weights.values()) or 1.0
        aggregate_score = max(0.0, min(weighted_score / total_weight, 1.0))
        base_confidence = max(0.0, min(weighted_confidence / total_weight, 1.0))

        # Dempster-Shafer inspired aggregation for uncertainty handling.
        combined_uncertainty = 1.0
        for value in uncertainties:
            combined_uncertainty *= max(0.0, min(value, 1.0))
        ds_factor = 1.0 - combined_uncertainty
        confidence = max(0.0, min(base_confidence * (0.5 + ds_factor / 2), 1.0))

        return ConsensusResult(
            aggregate_score=round(aggregate_score, 4),
            confidence=round(confidence, 4),
            uncertainty=round(combined_uncertainty, 4),
            weights=weights,
        )

    def load_history(self, payload: Mapping[str, Iterable[float]]) -> None:
        for agent, values in payload.items():
            cleaned = [max(0.0, min(float(v), 1.0)) for v in values]
            self._accuracy_history[agent] = cleaned[-self.max_history :]

    @property
    def history(self) -> Mapping[str, Sequence[float]]:
        return {
            agent: tuple(values) for agent, values in self._accuracy_history.items()
        }
