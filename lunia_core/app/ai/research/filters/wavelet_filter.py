"""Discrete wavelet transform based denoiser.

The implementation is intentionally tiny: it performs a single level Haar
transform and reconstructs the approximation coefficients to smooth out
high-frequency noise.  This keeps the dependency surface minimal while still
providing a meaningful wavelet style filter for research tasks.
"""

from __future__ import annotations

from typing import Iterable, List

from app.data.feeds.market_feed import PriceFeed, ensure_minimum_length


def _haar_forward(values: List[float]) -> tuple[List[float], List[float]]:
    approx: List[float] = []
    detail: List[float] = []
    for i in range(0, len(values), 2):
        pair = values[i : i + 2]
        if len(pair) < 2:
            pair = pair + [pair[-1]]
        avg = (pair[0] + pair[1]) / 2
        diff = (pair[0] - pair[1]) / 2
        approx.append(avg)
        detail.append(diff)
    return approx, detail


def _haar_inverse(approx: List[float], detail: List[float]) -> List[float]:
    reconstructed: List[float] = []
    for avg, diff in zip(approx, detail):
        reconstructed.extend([avg + diff, avg - diff])
    return reconstructed


def wavelet_smooth(prices: Iterable[float]) -> List[float]:
    data = ensure_minimum_length(prices, 4)
    approx, detail = _haar_forward(list(data))
    zeros = [0.0 for _ in detail]
    smoothed = _haar_inverse(approx, zeros)
    return smoothed[: len(data)]


def wavelet_smooth_on_feed(
    feed: PriceFeed, symbol: str, limit: int = 500
) -> List[float]:
    return wavelet_smooth(feed.get_prices(symbol, limit=limit))
