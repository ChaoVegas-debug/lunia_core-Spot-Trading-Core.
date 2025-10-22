"""Typed helpers for backup metadata."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass(slots=True)
class BackupMetadata:
    identifier: str
    created_at: _dt.datetime
    size_bytes: int
    strategy: str
    path: Path
    extra: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, object]:
        return {
            "identifier": self.identifier,
            "created_at": self.created_at.isoformat(),
            "size_bytes": self.size_bytes,
            "strategy": self.strategy,
            "path": str(self.path),
            "extra": self.extra,
        }


@dataclass(slots=True)
class BackupResult:
    success: bool
    metadata: Optional[BackupMetadata] = None
    message: str = ""

    def to_dict(self) -> Dict[str, object]:
        payload = {"success": self.success, "message": self.message}
        if self.metadata:
            payload["metadata"] = {
                "identifier": self.metadata.identifier,
                "created_at": self.metadata.created_at.isoformat(),
                "size_bytes": self.metadata.size_bytes,
                "strategy": self.metadata.strategy,
                "path": str(self.metadata.path),
                "extra": self.metadata.extra,
            }
        return payload
