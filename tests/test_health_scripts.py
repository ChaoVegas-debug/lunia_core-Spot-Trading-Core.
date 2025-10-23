import importlib
import os

import pytest

OFFLINE = os.getenv("OFFLINE_CI") == "1" or os.getenv("SKIP_INFRA") == "1"


def test_health_scripts_importable() -> None:
    if OFFLINE:
        pytest.skip("offline mode")
    for name in (
        "scripts.health.redis_check",
        "scripts.health.rabbitmq_check",
        "scripts.health.all_checks",
    ):
        module = importlib.import_module(name)
        assert callable(getattr(module, "main", None))
