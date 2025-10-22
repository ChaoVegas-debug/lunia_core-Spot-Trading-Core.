"""Logic for restoring from backups."""

from __future__ import annotations

import logging
from typing import Optional

from .backup_manager import SmartBackupManager
from .models import BackupMetadata, BackupResult
from .storage import BackupStorage

LOGGER = logging.getLogger(__name__)


class IntelligentRecoveryEngine:
    """Selects the best backup and coordinates restore steps."""

    def __init__(self, storage: BackupStorage | None = None) -> None:
        self.storage = storage or BackupStorage()
        self.backup_manager = SmartBackupManager(self.storage)

    def restore_to_optimal_state(self) -> BackupResult:
        candidate = self.find_optimal_backup()
        if not candidate:
            return BackupResult(success=False, message="no backups available")
        LOGGER.info("Restoring from backup %s", candidate.identifier)
        # Restoration is mocked; in production we'd untar and replace state.
        return BackupResult(success=True, metadata=candidate, message="restore:ok")

    def find_optimal_backup(self) -> Optional[BackupMetadata]:
        backups = self.storage.list_backups()
        if not backups:
            return None
        backups.sort(key=self.calculate_backup_score, reverse=True)
        return backups[0]

    def calculate_backup_score(self, metadata: BackupMetadata) -> float:
        backups = self.storage.list_backups()
        newest = max((item.created_at for item in backups), default=metadata.created_at)
        age_seconds = (newest - metadata.created_at).total_seconds()
        freshness = max(0.0, 1_000_000 - age_seconds)
        size_score = max(1.0, metadata.size_bytes / 1024)
        return freshness + size_score
