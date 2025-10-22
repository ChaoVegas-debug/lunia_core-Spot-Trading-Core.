"""Lightweight Kalman filter for denoising price series.

The implementation avoids third party numerical libraries so it can run in
restricted offline environments.  It is intentionally simple: a single state
variable representing the price level and scalar process/measurement noise
parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from app.data.feeds.market_feed import PriceFeed, ensure_minimum_length


@dataclass
class KalmanFilterConfig:
    process_variance: float = 1e-3
    measurement_variance: float = 1e-2
    initial_estimate: float | None = None


class KalmanFilter:
    """One dimensional Kalman filter."""

    def __init__(self, config: KalmanFilterConfig | None = None) -> None:
        self.config = config or KalmanFilterConfig()

    def run(self, prices: Iterable[float]) -> List[float]:
        data = ensure_minimum_length(prices, 2)
        estimate = (
            self.config.initial_estimate
            if self.config.initial_estimate is not None
            else data[0]
        )
        error_covariance = self.config.measurement_variance
        smoothed: List[float] = []

        for price in data:
            # Prediction step
            prior_estimate = estimate
            prior_error_covariance = error_covariance + self.config.process_variance

            # Update step
            kalman_gain = prior_error_covariance / (
                prior_error_covariance + self.config.measurement_variance
            )
            estimate = prior_estimate + kalman_gain * (price - prior_estimate)
            error_covariance = (1 - kalman_gain) * prior_error_covariance
            smoothed.append(estimate)

        return smoothed

    def run_on_feed(
        self, feed: PriceFeed, symbol: str, limit: int = 500
    ) -> List[float]:
        return self.run(feed.get_prices(symbol, limit=limit))
