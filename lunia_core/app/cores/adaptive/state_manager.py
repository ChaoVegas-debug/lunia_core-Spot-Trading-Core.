"""Persistence for reinforcement state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class ReinforcementStateManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path("logs/cores/reinforcement_state.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, float]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self, weights: Dict[str, float]) -> None:
        self.path.write_text(json.dumps(weights, indent=2), encoding="utf-8")
