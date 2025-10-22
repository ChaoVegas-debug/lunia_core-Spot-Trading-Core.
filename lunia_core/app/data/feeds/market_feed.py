"""Market data feed abstractions for research filters.

These utilities provide a thin wrapper around existing exchange clients.
The wrappers are intentionally lightweight so tests can supply in-memory
series without requiring network connectivity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Protocol


class PriceFeed(Protocol):
    """Protocol describing a price feed that can return historical prices."""

    def get_prices(self, symbol: str, limit: int = 500) -> List[float]: ...


@dataclass
class StaticPriceFeed:
    """Simple feed backed by a static iterable of prices.

    The feed copies the provided values to guarantee immutability between
    successive calls.  This is primarily useful in tests where deterministic
    behaviour is required.
    """

    prices: Iterable[float]

    def get_prices(self, symbol: str, limit: int = 500) -> List[float]:
        series = list(self.prices)
        if limit:
            return series[-limit:]
        return series


def ensure_minimum_length(series: Iterable[float], minimum: int) -> List[float]:
    """Return the series as a list and enforce a minimum length."""

    data = list(series)
    if len(data) < minimum:
        raise ValueError(f"expected at least {minimum} points, received {len(data)}")
    return data
