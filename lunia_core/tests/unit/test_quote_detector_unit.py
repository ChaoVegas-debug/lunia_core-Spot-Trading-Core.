"""Unit tests for the quote detector utility."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.core.utils import quote_detector as qd


@pytest.mark.unit
def test_detects_preferred_quote_from_balances(temp_db: Path) -> None:
    qd.register_quote_balances(
        {
            "USDC": {"free": 20.0, "locked": 0.0},
            "USDT": {"free": 5.0, "locked": 0.0},
        }
    )
    assert qd.get_current_quote(force_check=True) == "USDC"


@pytest.mark.unit
def test_user_override_persists(temp_db: Path) -> None:
    qd.set_user_quote("42", "PLN")
    assert qd.get_user_quote("42") == "PLN"
    assert qd.get_current_quote(force_check=False) == "PLN"


@pytest.mark.unit
def test_fallback_to_default_quote(
    temp_db: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DEFAULT_QUOTE", "EUR")
    assert qd.get_current_quote(force_check=True) == "EUR"


@pytest.mark.unit
def test_symbol_helpers(temp_db: Path) -> None:
    qd.set_active_quote("USDT")
    assert qd.build_symbol("btc") == "BTCUSDT"
    assert qd.split_symbol("ETHUSDC") == ("ETH", "USDC")
    assert qd.split_symbol("DOGEUSDT") == ("DOGE", "USDT")
