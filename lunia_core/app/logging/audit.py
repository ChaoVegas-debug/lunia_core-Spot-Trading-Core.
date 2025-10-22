"""Audit logging utilities."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


def _default_log_path() -> Path:
    base = Path(__file__).resolve().parents[3] / "logs"
    base.mkdir(parents=True, exist_ok=True)
    return base / "audit.log"


class AuditLogger:
    """Structured audit logger with JSON output."""

    def __init__(self, log_path: Path | None = None) -> None:
        self.log_path = log_path or _default_log_path()
        self.logger = logging.getLogger("audit")

    def log_event(self, event_type: str, payload: Dict[str, Any] | None = None) -> None:
        entry = {
            "ts": datetime.utcnow().isoformat(),
            "event": event_type,
            "payload": payload or {},
            "host": os.getenv("HOSTNAME", "local"),
        }
        try:
            with self.log_path.open("a", encoding="utf-8") as fp:
                fp.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            self.logger.exception("Failed to write audit log entry")
        self.logger.info("AUDIT %s", entry)


audit_logger = AuditLogger()
