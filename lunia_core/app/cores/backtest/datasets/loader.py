"""Load historical datasets for backtests."""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import List

from .validator import DatasetValidator


class DatasetLoader:
    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path
        self.validator = DatasetValidator()

    def load(
        self,
        symbol: str,
        timeframe: str,
        start: _dt.date,
        end: _dt.date,
    ) -> List[float]:
        path = self.base_path / symbol.upper() / f"{timeframe}.json"
        if not path.exists():
            return self._synthetic_series(start, end)
        data = json.loads(path.read_text(encoding="utf-8"))
        series = [float(entry.get("close", 0.0)) for entry in data]
        self.validator.validate(series)
        return series

    def _synthetic_series(self, start: _dt.date, end: _dt.date) -> List[float]:
        days = max((end - start).days, 1)
        return [100.0 + i for i in range(days + 1)]
