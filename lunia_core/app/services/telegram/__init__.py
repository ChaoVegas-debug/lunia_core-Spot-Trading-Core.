"""Helpers for optional Telegram integrations."""
from importlib.util import find_spec


def is_available() -> bool:
    """Return True when the optional aiogram dependency can be imported."""
    return find_spec("aiogram") is not None
