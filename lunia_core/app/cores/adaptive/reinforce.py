"""Adaptive reinforcement engine adjusting core weights."""

from __future__ import annotations

import logging
from typing import Dict

from .policy import EpsilonGreedyPolicy
from .reward_calculator import RewardCalculator
from .state_manager import ReinforcementStateManager

LOGGER = logging.getLogger(__name__)


class AdaptiveReinforcementEngine:
    def __init__(self) -> None:
        self.policy = EpsilonGreedyPolicy()
        self.reward_calc = RewardCalculator()
        self.state = ReinforcementStateManager()
        self.weights = self.state.load()

    def update_weights(
        self, performance: Dict[str, Dict[str, float]]
    ) -> Dict[str, float]:
        if not performance:
            return self.weights
        for core, metrics in performance.items():
            reward = self.reward_calc.calculate(metrics)
            current = self.weights.get(core, 1.0)
            updated = max(0.0, current + reward * 0.01)
            self.weights[core] = updated
            LOGGER.debug("Core %s weight updated to %.4f", core, updated)
        self._normalize()
        self.state.save(self.weights)
        self.policy.update()
        return self.weights

    def _normalize(self) -> None:
        total = sum(self.weights.values()) or 1.0
        for key in list(self.weights.keys()):
            self.weights[key] = self.weights[key] / total
