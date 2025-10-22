"""Storage abstraction for backups."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from .models import BackupMetadata

DEFAULT_PATH = Path(os.getenv("BACKUP_STORAGE_PATH", "/opt/lunia_core/backups"))


class BackupStorage:
    """Persist metadata and payloads for backups."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or DEFAULT_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)

    def list_backups(self) -> List[BackupMetadata]:
        items: List[BackupMetadata] = []
        for candidate in sorted(self.base_path.glob("*.json")):
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                items.append(
                    BackupMetadata(
                        identifier=data["identifier"],
                        created_at=_parse_datetime(data["created_at"]),
                        size_bytes=int(data.get("size_bytes", 0)),
                        strategy=data.get("strategy", "unknown"),
                        path=Path(data.get("path", candidate.with_suffix(".tar"))),
                        extra=data.get("extra", {}),
                    )
                )
            except Exception:
                continue
        return items

    def save_metadata(self, metadata: BackupMetadata) -> None:
        payload = {
            "identifier": metadata.identifier,
            "created_at": metadata.created_at.isoformat(),
            "size_bytes": metadata.size_bytes,
            "strategy": metadata.strategy,
            "path": str(metadata.path),
            "extra": metadata.extra,
        }
        (self.base_path / f"{metadata.identifier}.json").write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

    def prune_old(self, keep_last: int) -> None:
        backups = self.list_backups()
        for meta in backups[:-keep_last]:
            metadata_path = self.base_path / f"{meta.identifier}.json"
            archive_path = meta.path
            with suppress_error():
                metadata_path.unlink(missing_ok=True)
            with suppress_error():
                archive_path.unlink(missing_ok=True)


class suppress_error:
    def __enter__(self) -> None:  # noqa: D401
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: D401
        return True


def _parse_datetime(value: str):
    from datetime import datetime

    try:
        return datetime.fromisoformat(value)
    except Exception:
        return datetime.utcnow()
