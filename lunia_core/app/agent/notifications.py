"""Notification helpers for the updater."""

from __future__ import annotations

import logging

LOGGER = logging.getLogger(__name__)


def notify(message: str) -> None:
    LOGGER.info("[agent] %s", message)
