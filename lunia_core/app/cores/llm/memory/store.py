"""Simple JSONL based memory store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable


class MemoryStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("logs/llm/memory.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def load(self, limit: int = 500) -> Iterable[Dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            lines = handle.readlines()[-limit:]
        return [json.loads(line) for line in lines if line.strip()]
