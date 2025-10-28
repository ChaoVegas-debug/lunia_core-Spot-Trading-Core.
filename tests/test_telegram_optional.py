import os, sys, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lunia_core.app.services import telegram

def test_telegram_optional_surface():
    assert hasattr(telegram, "is_available")
    assert isinstance(telegram.is_available(), bool)
    _ = telegram.reason_unavailable()
