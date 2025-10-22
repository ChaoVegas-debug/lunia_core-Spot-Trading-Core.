from __future__ import annotations

from app.ai.research.filters import HMMFilter, KalmanFilter, wavelet_smooth
from app.data.feeds.market_feed import StaticPriceFeed


def test_kalman_filter_produces_smoother_series():
    feed = StaticPriceFeed([10, 10.5, 11, 50, 11.5, 12])
    filtered = KalmanFilter().run_on_feed(feed, "BTCUSDT")
    assert len(filtered) == 6
    assert filtered[-1] < 20  # the outlier should be dampened


def test_wavelet_filter_preserves_length():
    feed = StaticPriceFeed([1, 2, 3, 4, 5, 6])
    smoothed = wavelet_smooth(feed.get_prices("ETHUSDT"))
    assert len(smoothed) == 6
    assert abs(smoothed[1] - smoothed[0]) < 2


def test_hmm_filter_returns_probabilities():
    feed = StaticPriceFeed([100, 101, 102, 90, 89, 88])
    probs = HMMFilter().run_on_feed(feed, "SOLUSDT")
    assert len(probs) == 6
    assert all(0.0 <= value <= 1.0 for value in probs)
