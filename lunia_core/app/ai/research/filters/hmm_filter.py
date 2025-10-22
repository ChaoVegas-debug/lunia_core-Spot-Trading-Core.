"""Simple hidden Markov model filter for regime detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from app.data.feeds.market_feed import PriceFeed, ensure_minimum_length


@dataclass
class HMMConfig:
    transition_matrix: tuple[tuple[float, float], tuple[float, float]] = (
        (0.9, 0.1),
        (0.1, 0.9),
    )
    means: tuple[float, float] = (0.0, 0.0)
    variances: tuple[float, float] = (1.0, 4.0)
    priors: tuple[float, float] = (0.5, 0.5)


def _gaussian_probability(value: float, mean: float, variance: float) -> float:
    if variance <= 0:
        return 0.0
    coeff = 1.0 / (variance * (2.0) ** 0.5)
    exponent = -((value - mean) ** 2) / (2 * variance)
    return coeff * (2.718281828459045**exponent)


class HMMFilter:
    """Two state hidden Markov model for regime probabilities."""

    def __init__(self, config: HMMConfig | None = None) -> None:
        self.config = config or HMMConfig()

    def run(self, returns: Iterable[float]) -> List[float]:
        data = ensure_minimum_length(returns, 2)
        probs: List[float] = []
        prev_state = list(self.config.priors)

        for value in data:
            likelihoods = [
                _gaussian_probability(
                    value, self.config.means[i], self.config.variances[i]
                )
                for i in range(2)
            ]
            predicted = [
                prev_state[0] * self.config.transition_matrix[0][i]
                + prev_state[1] * self.config.transition_matrix[1][i]
                for i in range(2)
            ]
            joint = [predicted[i] * likelihoods[i] for i in range(2)]
            normaliser = sum(joint) or 1e-12
            posterior = [value / normaliser for value in joint]
            probs.append(posterior[1])
            prev_state = posterior

        return probs

    def run_on_feed(
        self, feed: PriceFeed, symbol: str, limit: int = 500
    ) -> List[float]:
        prices = feed.get_prices(symbol, limit=limit)
        ensure_minimum_length(prices, 2)
        returns = [0.0]
        for prev, curr in zip(prices, prices[1:]):
            returns.append(curr - prev)
        return self.run(returns)
