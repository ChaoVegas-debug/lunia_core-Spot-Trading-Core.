"""Simple historical backtesting support."""

from __future__ import annotations

import datetime as _dt
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from .datasets.loader import DatasetLoader
from .metrics import BacktestMetrics
from .report import BacktestReportGenerator
from .strategies.futures_adapter import FuturesStrategyAdapter
from .strategies.hft_adapter import HFTStrategyAdapter
from .strategies.spot_adapter import SpotStrategyAdapter

LOGGER = logging.getLogger(__name__)


@dataclass
class StrategyConfig:
    name: str
    core_type: str
    params: Dict[str, float] | None = None


@dataclass
class BacktestResult:
    strategy: StrategyConfig
    equity_curve: List[float]
    trades: int
    metrics: Dict[str, float]
    started_at: _dt.datetime
    completed_at: _dt.datetime


class BacktestRunner:
    """Executes simplified backtests for Lunia strategies."""

    def __init__(self, data_dir: Path | None = None) -> None:
        self.data_dir = data_dir or Path("app/data/history")
        self.loader = DatasetLoader(self.data_dir)
        self.reporter = BacktestReportGenerator()
        self.adapters = {
            "SPOT": SpotStrategyAdapter(),
            "FUTURES": FuturesStrategyAdapter(),
            "HFT": HFTStrategyAdapter(),
        }

    def run_strategy(
        self,
        strategy_name: str,
        core_type: str,
        symbol: str,
        timeframe: str,
        start_date: _dt.date,
        end_date: _dt.date,
        initial_capital: float = 10_000.0,
    ) -> BacktestResult:
        dataset = self.loader.load(symbol, timeframe, start_date, end_date)
        adapter = self.adapters.get(core_type.upper())
        if not adapter:
            raise ValueError(f"Unsupported core type: {core_type}")
        LOGGER.info("Running backtest %s/%s for %s", core_type, strategy_name, symbol)
        equity_curve = adapter.simulate(strategy_name, dataset, initial_capital)
        trades = adapter.last_trade_count
        metrics = BacktestMetrics.compute(equity_curve)
        now = _dt.datetime.utcnow()
        return BacktestResult(
            strategy=StrategyConfig(name=strategy_name, core_type=core_type.upper()),
            equity_curve=equity_curve,
            trades=trades,
            metrics=metrics,
            started_at=now,
            completed_at=now,
        )

    def compare_strategies(
        self, strategies: Sequence[StrategyConfig], benchmark: str | None = None
    ) -> Dict[str, Dict[str, float]]:
        results: Dict[str, Dict[str, float]] = {}
        for config in strategies:
            result = self.run_strategy(
                config.name,
                config.core_type,
                symbol=(
                    config.params.get("symbol", "BTCUSDT")
                    if config.params
                    else "BTCUSDT"
                ),
                timeframe=(
                    config.params.get("timeframe", "1h") if config.params else "1h"
                ),
                start_date=_dt.date.today() - _dt.timedelta(days=30),
                end_date=_dt.date.today(),
            )
            results[config.name] = result.metrics
        if benchmark:
            results["benchmark"] = {"name": benchmark}
        return results

    def optimize_parameters(
        self,
        strategy_class: str,
        parameter_ranges: Dict[str, Iterable[float]],
        metric: str = "sharpe_ratio",
    ) -> Dict[str, float]:
        best_score = float("-inf")
        best_params: Dict[str, float] = {}
        for param, values in parameter_ranges.items():
            for value in values:
                score = value  # placeholder heuristic
                if score > best_score:
                    best_score = score
                    best_params = {param: float(value)}
        LOGGER.info("Optimization completed for %s -> %s", strategy_class, best_params)
        return {"metric": metric, "best_params": best_params, "score": best_score}

    def latest_reports(self, limit: int = 5) -> List[Dict[str, object]]:
        history_dir = Path("logs/backtests")
        if not history_dir.exists():
            return []
        reports = sorted(history_dir.glob("*.json"), reverse=True)[:limit]
        payload: List[Dict[str, object]] = []
        for path in reports:
            try:
                payload.append(json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
        return payload
