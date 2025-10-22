"""Offline-friendly performance harness tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest

from tools import load_test


@pytest.mark.unit
def test_load_plan_defaults():
    plan = load_test._load_plan(10, 2, 100, ["BTCUSDT", "ETHUSDT"])  # type: ignore[attr-defined]
    assert plan, "plan should not be empty"
    kinds = {item[0] for item in plan}
    assert {"order", "ai", "backtest"}.issubset(kinds)


def test_execute_load_test_offline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LUNIA_API_URL", "http://127.0.0.1:65535")
    report = load_test.execute_load_test(users=2, backtests=1, orders_per_minute=10)
    assert "summary" in report
    assert "total_tasks" in report["summary"]
    output = tmp_path / "summary.json"
    output.write_text(json.dumps(report), encoding="utf-8")
    assert output.exists()


@pytest.mark.parametrize("users", [5, 100])
def test_cli_entrypoint(tmp_path: Path, users: int):
    output = tmp_path / "out.json"
    exit_code = load_test.main(
        [
            "--users",
            str(users),
            "--backtests",
            "3",
            "--orders",
            "50",
            "--output",
            str(output),
        ]
    )
    assert exit_code == 0
    assert output.exists()
