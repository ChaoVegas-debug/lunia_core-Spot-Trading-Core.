import importlib
import os

import pytest


@pytest.mark.skipif(os.getenv("OFFLINE_CI") == "1", reason="offline mode")
def test_telegram_optional_imports() -> None:
    module = importlib.import_module("app.services.telegram")
    assert hasattr(module, "is_available")
