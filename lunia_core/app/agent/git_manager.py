"""Utilities for interacting with git."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class GitManager:
    def __init__(self, repo_path: Path | None = None) -> None:
        self.repo_path = repo_path or Path(".")

    def pull(self) -> str:
        try:
            output = subprocess.check_output(["git", "pull"], cwd=self.repo_path)
            return output.decode("utf-8")
        except Exception as exc:  # pragma: no cover - environment specific
            LOGGER.error("git pull failed: %s", exc)
            return "git pull failed"
