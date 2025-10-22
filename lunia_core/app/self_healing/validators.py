"""Validation helpers for self-healing routines."""

from __future__ import annotations

import logging
import os
from shutil import disk_usage

from .types import RecoveryPlan, ValidationResult

LOGGER = logging.getLogger(__name__)


class SafeRecoveryValidator:
    """Performs basic guard checks before triggering recovery."""

    def __init__(self, min_free_mb: int | None = None) -> None:
        self.min_free_mb = min_free_mb or int(os.getenv("CRITICAL_MEMORY_MB", "1024"))

    def validate_recovery_safety(self, plan: RecoveryPlan) -> ValidationResult:
        reasons = []
        free_mb = disk_usage(os.getcwd()).free / (1024 * 1024)
        if free_mb < self.min_free_mb:
            reasons.append(
                f"Not enough disk space ({free_mb:.0f} MB < {self.min_free_mb} MB)"
            )
        if plan.issue_type == "storage" and "purge_old_backups" not in plan.actions:
            reasons.append("Storage recovery requires purge_old_backups action")
        if reasons:
            LOGGER.error("Recovery plan rejected: %s", reasons)
            return ValidationResult(valid=False, reasons=reasons)
        LOGGER.debug("Recovery plan validated: %s", plan)
        return ValidationResult(valid=True)
