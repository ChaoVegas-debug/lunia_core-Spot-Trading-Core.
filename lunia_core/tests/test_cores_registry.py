from __future__ import annotations

import pytest
from app.cores.runtime.registry import REGISTRY


def test_registry_contains_default_cores():
    expected = {"SPOT", "HFT", "FUTURES", "OPTIONS", "ARBITRAGE", "DEFI", "LLM"}
    assert expected.issubset(set(REGISTRY.names()))


def test_toggle_and_weight():
    REGISTRY.toggle("SPOT", False)
    REGISTRY.set_weight("SPOT", 0.5)
    snapshot = REGISTRY.snapshot()["SPOT"]
    assert snapshot["enabled"] is False
    assert snapshot["weight"] == pytest.approx(0.5)
    REGISTRY.toggle("SPOT", True)
    REGISTRY.set_weight("SPOT", 1.0)
