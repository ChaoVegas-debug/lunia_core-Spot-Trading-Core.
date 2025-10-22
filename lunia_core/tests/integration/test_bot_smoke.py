"""Ensure Telegram bot can start in dry-run mode."""

from __future__ import annotations

import pytest
from app.services.telegram import bot as bot_module

pytestmark = [pytest.mark.integration]


def test_bot_create_app(mock_env: dict[str, str]) -> None:
    bot, dp = bot_module.create_app(dry_run=True)
    assert bot is not None
    assert dp is not None
    assert isinstance(dp.handlers["message"], dict)
