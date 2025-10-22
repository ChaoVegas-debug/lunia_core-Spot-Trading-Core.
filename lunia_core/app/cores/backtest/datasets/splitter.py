"""Dataset train/test split helpers."""

from __future__ import annotations

from typing import Iterable, List, Tuple


def time_split(
    series: Iterable[float], ratio: float = 0.7
) -> Tuple[List[float], List[float]]:
    values = list(series)
    idx = max(int(len(values) * ratio), 1)
    return values[:idx], values[idx:]
