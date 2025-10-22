"""Smart backup coordinator for Lunia."""

from __future__ import annotations

import datetime as _dt
import logging
import os
import tarfile
import uuid
from pathlib import Path

from .models import BackupMetadata, BackupResult
from .storage import BackupStorage

LOGGER = logging.getLogger(__name__)


class SmartBackupManager:
    """Coordinate recurring backups with simple heuristics."""

    def __init__(self, storage: BackupStorage | None = None) -> None:
        self.storage = storage or BackupStorage()
        self.retention_days = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))

    def execute_smart_backup(self, trigger: str = "auto") -> BackupResult:
        strategy = self.determine_backup_strategy(trigger)
        identifier = (
            f"backup-{_dt.datetime.utcnow():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        )
        archive_path = self.storage.base_path / f"{identifier}.tar"
        archive_size = self._create_archive(archive_path)
        metadata = BackupMetadata(
            identifier=identifier,
            created_at=_dt.datetime.utcnow(),
            size_bytes=archive_size,
            strategy=strategy,
            path=archive_path,
        )
        self.storage.save_metadata(metadata)
        self._prune_retention()
        LOGGER.info("Backup completed: %s (%s)", identifier, strategy)
        return BackupResult(
            success=True, metadata=metadata, message=f"backup:{strategy}"
        )

    def determine_backup_strategy(self, trigger: str) -> str:
        mapping = {
            "auto": "scheduled",
            "pre_market_open": "pre_market",
            "post_market_close": "post_market",
            "emergency": "emergency",
        }
        return mapping.get(trigger, "scheduled")

    def _create_archive(self, archive_path: Path) -> int:
        source_dir = Path(os.getenv("LUNIA_RUNTIME_DIR", "/opt/lunia_core/lunia_core"))
        with tarfile.open(archive_path, "w") as archive:
            state_file = source_dir / "app" / "cores" / "state.py"
            if state_file.exists():
                archive.add(state_file, arcname="state.py")
            logs_dir = source_dir / "logs"
            if logs_dir.exists():
                archive.add(logs_dir, arcname="logs", recursive=True)
        return int(archive_path.stat().st_size)

    def _prune_retention(self) -> None:
        backups = self.storage.list_backups()
        cutoff = _dt.datetime.utcnow() - _dt.timedelta(days=self.retention_days)
        for backup in backups:
            if backup.created_at < cutoff:
                with suppress_error():
                    (self.storage.base_path / f"{backup.identifier}.json").unlink(
                        missing_ok=True
                    )
                with suppress_error():
                    backup.path.unlink(missing_ok=True)


class suppress_error:
    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        return True
