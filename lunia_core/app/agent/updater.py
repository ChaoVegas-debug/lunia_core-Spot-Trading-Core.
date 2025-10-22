"""Auto update agent coordinating git and health checks."""

from __future__ import annotations

import asyncio
import logging

from .git_manager import GitManager
from .health_check import HealthChecker
from .notifications import notify
from .rollback import RollbackManager

LOGGER = logging.getLogger(__name__)


class AutoUpdateAgent:
    def __init__(self) -> None:
        self.git = GitManager()
        self.health = HealthChecker()
        self.rollback = RollbackManager()

    async def run_once(self) -> None:
        notify("Starting update cycle")
        result = self.git.pull()
        notify(f"Git update result: {result[:80]}")
        await asyncio.sleep(0)
        report = await self.health.check()
        if report.get("issues"):
            notify("Health issues detected after update; considering rollback")
            self.rollback.rollback()
        else:
            notify("Update cycle finished successfully")
