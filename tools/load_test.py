"""Synthetic load testing tool for Lunia Core.

The script stresses the public API with concurrent requests to emulate
production usage (hundreds of users, live orders, backtests). It keeps the
implementation dependency-light so it can execute in restricted
environments; when the real :mod:`requests` package is missing the
compatibility layer from ``app.compat.requests`` is used transparently.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# Ensure the application package is importable when the script is executed from
# the repository root.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "lunia_core") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "lunia_core"))

from app.compat.requests import requests  # noqa: E402

API_URL = os.environ.get("LUNIA_API_URL", "http://127.0.0.1:8000")
DEFAULT_USERS = 120
DEFAULT_BACKTESTS = 12
DEFAULT_ORDERS_PER_MIN = 550


def _post_json(path: str, payload: Dict[str, Any]) -> Tuple[str, int, Dict[str, Any]]:
    """Send a POST request and capture timing/result."""

    url = f"{API_URL.rstrip('/')}/{path.lstrip('/')}"
    start = time.perf_counter()
    response = requests.post(url, json=payload, timeout=10)
    duration_ms = int((time.perf_counter() - start) * 1000)
    try:
        data = response.json() if response.text else {}
    except Exception:  # pragma: no cover - defensive
        data = {"raw": response.text}
    return url, duration_ms, data


def _trigger_trade(symbol: str) -> Dict[str, Any]:
    side = random.choice(["BUY", "SELL"])
    qty = random.uniform(0.0005, 0.002)
    _, latency_ms, payload = _post_json(
        "/trade/spot/demo",
        {"symbol": symbol, "side": side, "qty": round(qty, 6)},
    )
    payload["latency_ms"] = latency_ms
    return payload


def _trigger_ai_run() -> Dict[str, Any]:
    _, latency_ms, payload = _post_json("/ai/run", {})
    payload["latency_ms"] = latency_ms
    return payload


def _trigger_backtest(symbol: str, timeframe: str = "1h") -> Dict[str, Any]:
    payload = {
        "symbol": symbol,
        "timeframe": timeframe,
        "start_date": "2023-01-01",
        "end_date": "2023-03-31",
    }
    _, latency_ms, response = _post_json("/backtest/run", payload)
    response["latency_ms"] = latency_ms
    return response


def _load_plan(
    users: int,
    backtests: int,
    orders_per_minute: int,
    symbols: Iterable[str],
) -> List[Tuple[str, Dict[str, Any]]]:
    plan: List[Tuple[str, Dict[str, Any]]] = []
    per_user_orders = max(1, orders_per_minute // max(users, 1))
    for _ in range(users):
        for _ in range(per_user_orders):
            plan.append(("order", {"symbol": random.choice(list(symbols))}))
        plan.append(("ai", {}))
    for _ in range(backtests):
        plan.append(("backtest", {"symbol": random.choice(list(symbols))}))
    random.shuffle(plan)
    return plan


def execute_load_test(
    *,
    users: int = DEFAULT_USERS,
    backtests: int = DEFAULT_BACKTESTS,
    orders_per_minute: int = DEFAULT_ORDERS_PER_MIN,
    symbols: Iterable[str] = ("BTCUSDT", "ETHUSDT", "BNBUSDT"),
) -> Dict[str, Any]:
    """Execute the synthetic workload and collect aggregated metrics."""

    plan = _load_plan(users, backtests, orders_per_minute, symbols)
    results: List[Dict[str, Any]] = []
    lock = threading.Lock()

    def _execute(task: Tuple[str, Dict[str, Any]]) -> None:
        kind, meta = task
        try:
            if kind == "order":
                outcome = _trigger_trade(meta["symbol"])
            elif kind == "ai":
                outcome = _trigger_ai_run()
            else:
                outcome = _trigger_backtest(meta.get("symbol", "BTCUSDT"))
        except Exception as exc:  # pragma: no cover - network failure
            outcome = {"status": "error", "error": str(exc)}
        outcome["task"] = kind
        with lock:
            results.append(outcome)

    with ThreadPoolExecutor(max_workers=min(64, len(plan) or 1)) as executor:
        futures = [executor.submit(_execute, task) for task in plan]
        for future in as_completed(futures):
            future.result()

    orders = [r for r in results if r.get("task") == "order"]
    latencies = [r.get("latency_ms", 0) for r in results]
    avg_latency = sum(latencies) / max(len(latencies), 1)
    success = sum(1 for r in results if r.get("status") not in {"error", "REJECTED"})
    summary = {
        "total_tasks": len(results),
        "order_count": len(orders),
        "avg_latency_ms": round(avg_latency, 2),
        "success_rate_pct": round((success / max(len(results), 1)) * 100, 2),
    }
    return {"summary": summary, "results": results[:50]}


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lunia synthetic load tester")
    parser.add_argument("--users", type=int, default=DEFAULT_USERS)
    parser.add_argument("--backtests", type=int, default=DEFAULT_BACKTESTS)
    parser.add_argument("--orders", type=int, default=DEFAULT_ORDERS_PER_MIN)
    parser.add_argument(
        "--symbols", nargs="*", default=["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    )
    parser.add_argument(
        "--output", type=Path, default=Path("reports/load_test_summary.json")
    )
    args = parser.parse_args(argv)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = execute_load_test(
        users=args.users,
        backtests=args.backtests,
        orders_per_minute=args.orders,
        symbols=args.symbols,
    )
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
