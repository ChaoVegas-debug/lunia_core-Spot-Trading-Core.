"""Policies for adaptive reinforcement."""

from __future__ import annotations

import random
from typing import Dict


class EpsilonGreedyPolicy:
    def __init__(self, epsilon: float = 0.1, decay: float = 0.99) -> None:
        self.epsilon = epsilon
        self.decay = decay

    def select(self, weights: Dict[str, float]) -> str:
        if not weights:
            raise ValueError("weights cannot be empty")
        if random.random() < self.epsilon:
            return random.choice(list(weights.keys()))
        return max(weights.items(), key=lambda item: item[1])[0]

    def update(self) -> None:
        self.epsilon = max(0.01, self.epsilon * self.decay)
