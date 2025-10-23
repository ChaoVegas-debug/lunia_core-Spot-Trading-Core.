import importlib
import os

import pytest

OFFLINE = os.getenv("OFFLINE_CI") == "1"

MODULES = [
    "lunia_core.app.core.scheduler",
    "lunia_core.app.core.guard",
    "lunia_core.app.services.telegram",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_import_matrix(module_name: str) -> None:
    if OFFLINE:
        # Modules should remain importable even without optional dependencies.
        pass
    module = importlib.import_module(module_name)
    assert module is not None
