"""OpenAI provider shim."""

from __future__ import annotations

import os
from typing import Dict


class OpenAIProvider:
    name = "openai"

    def available(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def generate(self, prompt: str, **kwargs) -> Dict[str, object]:
        return {
            "provider": self.name,
            "prompt": prompt,
            "response": "Simulated OpenAI response",
            "meta": kwargs,
        }
