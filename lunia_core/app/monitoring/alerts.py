"""Alert helpers for monitoring."""

from __future__ import annotations

import logging
import os
from typing import Dict

LOGGER = logging.getLogger(__name__)


class AlertManager:
    def __init__(self) -> None:
        self.chat_id = os.getenv("ALERT_TELEGRAM_CHAT_ID")

    def check_alerts(self, metrics: Dict[str, float]) -> None:
        if metrics.get("critical", False):
            self._trigger_alert("Critical condition detected")

    def notify_critical(
        self, message: str, context: Dict[str, str] | None = None
    ) -> None:
        """Log a critical alert.

        The implementation remains logging-only so it operates in offline test
        environments.  Integration with Telegram or other transports can be
        added later without changing the call sites.
        """

        extra = f" context={context}" if context else ""
        self._trigger_alert(f"{message}{extra}")

    def _trigger_alert(self, message: str) -> None:
        LOGGER.error("ALERT: %s", message)
        # Placeholder for Telegram integration
