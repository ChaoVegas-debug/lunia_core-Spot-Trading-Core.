from __future__ import annotations

import importlib
import sys
from pathlib import Path

# Ensure repository root is on sys.path so lunia_core package is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_telegram_optional_surface() -> None:
    telegram = importlib.import_module("lunia_core.app.services.telegram")
    assert hasattr(telegram, "is_available")
    assert isinstance(telegram.is_available(), bool)
    assert hasattr(telegram, "reason_unavailable")
    telegram.reason_unavailable()
