from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Iterable

import pytest
from app.core.ai.strategies import REGISTRY, StrategySignal, register


def _write_dataset(
    base: Path, symbol: str, timeframe: str, closes: Iterable[float]
) -> None:
    symbol_dir = base / symbol.upper()
    symbol_dir.mkdir(parents=True, exist_ok=True)
    payload = [{"close": value} for value in closes]
    (symbol_dir / f"{timeframe}.json").write_text(json.dumps(payload), encoding="utf-8")


def _load_runner(monkeypatch: pytest.MonkeyPatch, enabled: str = "true"):
    import importlib

    monkeypatch.setenv("SANDBOX_ENABLED", enabled)
    # ensure defaults for other environment variables to avoid leaking state
    monkeypatch.setenv("SANDBOX_HISTORY_PATH", "app/data/history/spot")
    monkeypatch.setenv("SANDBOX_REPORTS_PATH", "reports")
    import sandbox.sandbox_runner as sandbox_runner

    return importlib.reload(sandbox_runner)


@pytest.fixture(name="registered_strategy")
def fixture_registered_strategy():
    strategy_name = "sandbox_test"
    original = REGISTRY.get(strategy_name)

    def _strategy(symbol: str, prices, ctx) -> list[StrategySignal]:
        if len(prices) < 3:
            return []
        side = "BUY" if len(prices) % 2 == 0 else "SELL"
        price = float(prices[-1])
        signal = StrategySignal(
            symbol=symbol,
            side=side,
            score=1.0,
            price=price,
            stop_pct=ctx.get("sl_pct_default", 0.1),
            take_pct=ctx.get("tp_pct_default", 0.2),
            strategy=strategy_name,
            meta={},
        )
        return [signal]

    register(strategy_name, _strategy)
    yield strategy_name
    if original is not None:
        REGISTRY[strategy_name] = original
    else:
        REGISTRY.pop(strategy_name, None)


def test_run_sandbox_collects_metrics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, registered_strategy: str
):
    closes = [100 + i for i in range(40)]
    dataset_root = tmp_path / "datasets"
    _write_dataset(dataset_root, "TESTUSD", "1h", closes)
    sandbox_runner = _load_runner(monkeypatch, enabled="true")

    result = sandbox_runner.run_sandbox(
        strategy=registered_strategy,
        date=date(2024, 1, 1),
        symbol="TESTUSD",
        timeframe="1h",
        history_path=dataset_root,
    )

    assert result.trades > 0
    assert result.pnl != 0 or result.total_commission >= 0
    assert result.report_path
    report_path = Path(result.report_path)
    assert report_path.exists()
    report_data = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_data["strategy"] == registered_strategy
    assert report_data["trades"] == result.trades


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_cli_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    closes = [100 + (i * 0.5) for i in range(60)]
    dataset_root = tmp_path / "datasets"
    _write_dataset(dataset_root, "TESTUSD", "1h", closes)
    _load_runner(monkeypatch, enabled="true")

    env = dict(os.environ)
    env.update({"SANDBOX_ENABLED": "true"})
    existing_path = env.get("PYTHONPATH", "")
    path_entries = [str(PROJECT_ROOT)]
    if existing_path:
        path_entries.append(existing_path)
    env["PYTHONPATH"] = ":".join(path_entries)
    command = [
        sys.executable,
        "sandbox/sandbox_runner.py",
        "--strategy=ema_rsi_trend",
        "--date=2024-01-01",
        "--symbol=TESTUSD",
        "--timeframe=1h",
        f"--base-path={dataset_root}",
        "--no-report",
    ]
    completed = subprocess.run(
        command, capture_output=True, text=True, env=env, check=True
    )
    assert "Sandbox run completed" in completed.stdout
    assert '"pnl"' in completed.stdout


def test_disabled_sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    closes = [100 + i for i in range(20)]
    dataset_root = tmp_path / "datasets"
    _write_dataset(dataset_root, "TESTUSD", "1h", closes)
    sandbox_runner = _load_runner(monkeypatch, enabled="false")

    with pytest.raises(RuntimeError):
        sandbox_runner.run_sandbox(
            strategy="ema_rsi_trend",
            date=date(2024, 1, 1),
            symbol="TESTUSD",
            timeframe="1h",
            history_path=dataset_root,
        )
