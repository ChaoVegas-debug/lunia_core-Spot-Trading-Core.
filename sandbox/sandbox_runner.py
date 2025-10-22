"""Isolated sandbox runner for Lunia strategies."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence

from app.core.ai.strategies import REGISTRY, StrategySignal
from app.cores.backtest.datasets.loader import DatasetLoader

SANDBOX_ENABLED = os.getenv("SANDBOX_ENABLED", "true").lower() != "false"
DEFAULT_SYMBOL = os.getenv("SANDBOX_DEFAULT_SYMBOL", "BTCUSDT")
DEFAULT_TIMEFRAME = os.getenv("SANDBOX_DEFAULT_TIMEFRAME", "1h")
DEFAULT_HISTORY_PATH = os.getenv("SANDBOX_HISTORY_PATH", "app/data/history/spot")
REPORTS_DIR = Path(os.getenv("SANDBOX_REPORTS_PATH", "reports"))
COMMISSION_RATE = float(os.getenv("SANDBOX_COMMISSION_RATE", "0.001"))
SLIPPAGE_RATE = float(os.getenv("SANDBOX_SLIPPAGE_RATE", "0.0002"))


@dataclass
class SandboxResult:
    strategy: str
    symbol: str
    date: dt.date
    timeframe: str
    trades: int
    pnl: float
    total_slippage: float
    total_commission: float
    average_latency_ms: float
    run_id: str
    report_path: str

    def to_dict(self) -> Dict[str, object]:
        data = asdict(self)
        data["date"] = self.date.isoformat()
        return data


def _load_series(
    loader: DatasetLoader, symbol: str, timeframe: str, date_value: dt.date
) -> Sequence[float]:
    end = date_value + dt.timedelta(days=1)
    return loader.load(symbol=symbol, timeframe=timeframe, start=date_value, end=end)


def _run_strategy(
    strategy_name: str,
    prices: Sequence[float],
    symbol: str,
    ctx: Dict[str, float],
) -> Dict[str, object]:
    strategy = REGISTRY.get(strategy_name)
    if strategy is None:
        raise ValueError(f"unknown strategy '{strategy_name}'")

    pnl = 0.0
    total_slippage = 0.0
    total_commission = 0.0
    latencies: List[float] = []
    trades = 0

    if len(prices) < 2:
        return {
            "pnl": pnl,
            "total_slippage": total_slippage,
            "total_commission": total_commission,
            "latencies": latencies,
            "trades": trades,
        }

    for idx in range(1, len(prices) - 1):
        window = prices[: idx + 1]
        tick_start = time.perf_counter()
        signals: Iterable[StrategySignal] = strategy(symbol, window, ctx)
        latency_ms = (time.perf_counter() - tick_start) * 1000
        latencies.append(latency_ms)
        if not signals:
            continue
        next_price = prices[idx + 1]
        for signal in signals:
            execution_price = signal.price
            slippage = execution_price * SLIPPAGE_RATE
            commission = execution_price * COMMISSION_RATE
            total_slippage += slippage
            total_commission += commission
            if signal.side.upper() == "BUY":
                pnl += (next_price - (execution_price + slippage)) - commission
            elif signal.side.upper() == "SELL":
                pnl += ((execution_price - slippage) - next_price) - commission
            trades += 1

    return {
        "pnl": pnl,
        "total_slippage": total_slippage,
        "total_commission": total_commission,
        "latencies": latencies,
        "trades": trades,
    }


def run_sandbox(
    strategy: str,
    date: dt.date,
    *,
    symbol: str = DEFAULT_SYMBOL,
    timeframe: str = DEFAULT_TIMEFRAME,
    history_path: str | Path = DEFAULT_HISTORY_PATH,
    ctx: Dict[str, float] | None = None,
    write_report: bool = True,
) -> SandboxResult:
    if not SANDBOX_ENABLED:
        raise RuntimeError("sandbox execution is disabled (SANDBOX_ENABLED=false)")

    loader = DatasetLoader(Path(history_path))
    prices = _load_series(loader, symbol, timeframe, date)
    if not prices:
        raise ValueError("no price data available for the requested parameters")

    context = {
        "tp_pct_default": 0.30,
        "sl_pct_default": 0.15,
    }
    if ctx:
        context.update(ctx)

    run_stats = _run_strategy(strategy, prices, symbol, context)
    latencies = run_stats["latencies"] or [0.0]
    average_latency = mean(latencies)
    run_id = uuid.uuid4().hex
    report_path = ""

    result = SandboxResult(
        strategy=strategy,
        symbol=symbol,
        date=date,
        timeframe=timeframe,
        trades=run_stats["trades"],
        pnl=run_stats["pnl"],
        total_slippage=run_stats["total_slippage"],
        total_commission=run_stats["total_commission"],
        average_latency_ms=average_latency,
        run_id=run_id,
        report_path=report_path,
    )

    if write_report:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        file_name = f"sandbox_{strategy}_{symbol}_{date.isoformat()}_{run_id}.json"
        report_file = REPORTS_DIR / file_name
        report_file.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
        result.report_path = str(report_file)

    return result


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Lunia strategy sandbox.")
    parser.add_argument("--strategy", required=True, help="Registered strategy name")
    parser.add_argument(
        "--date",
        required=True,
        help="Trading date in YYYY-MM-DD",
    )
    parser.add_argument("--symbol", default=DEFAULT_SYMBOL, help="Trading symbol")
    parser.add_argument(
        "--timeframe", default=DEFAULT_TIMEFRAME, help="Dataset timeframe (e.g. 1h)"
    )
    parser.add_argument(
        "--base-path",
        default=DEFAULT_HISTORY_PATH,
        help="Base path containing historical datasets",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing JSON report to the reports directory",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if not SANDBOX_ENABLED:
        print("Sandbox execution disabled via SANDBOX_ENABLED", file=sys.stderr)
        return 1
    args = _parse_args(argv)
    try:
        date_value = dt.datetime.strptime(args.date, "%Y-%m-%d").date()
    except ValueError as exc:
        print(f"Invalid date: {exc}", file=sys.stderr)
        return 2

    try:
        result = run_sandbox(
            strategy=args.strategy,
            date=date_value,
            symbol=args.symbol,
            timeframe=args.timeframe,
            history_path=args.base_path,
            write_report=not args.no_report,
        )
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Sandbox run failed: {exc}", file=sys.stderr)
        return 3

    print("Sandbox run completed")
    print(json.dumps(result.to_dict(), indent=2))
    if result.report_path:
        print(f"Report written to {result.report_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
