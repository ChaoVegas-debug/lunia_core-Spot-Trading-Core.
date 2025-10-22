"""Local model provider shim."""

from __future__ import annotations

import os
from typing import Dict


class LocalLLMProvider:
    name = "local"

    def available(self) -> bool:
        return bool(os.getenv("LOCAL_LLM_MODEL_PATH"))

    def generate(self, prompt: str, **kwargs) -> Dict[str, object]:
        return {
            "provider": self.name,
            "prompt": prompt,
            "response": "Simulated local model response",
            "meta": kwargs,
        }
