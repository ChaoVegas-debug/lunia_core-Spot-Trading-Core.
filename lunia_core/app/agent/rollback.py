"""Simple rollback helper."""

from __future__ import annotations

import logging
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class RollbackManager:
    def __init__(self, backups_dir: Path | None = None) -> None:
        self.backups_dir = backups_dir or Path("/opt/lunia_core/backups")

    def rollback(self) -> str:
        LOGGER.warning("Rollback requested (placeholder)")
        return "rollback executed"
