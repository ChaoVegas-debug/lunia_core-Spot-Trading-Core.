"""Validation helpers for datasets."""

from __future__ import annotations

from typing import Iterable


class DatasetValidator:
    def validate(self, series: Iterable[float]) -> None:
        values = list(series)
        if not values:
            raise ValueError("dataset is empty")
        if any(value < 0 for value in values):
            raise ValueError("dataset contains negative price")
