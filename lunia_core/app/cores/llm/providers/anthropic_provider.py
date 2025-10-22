"""Anthropic provider shim."""

from __future__ import annotations

import os
from typing import Dict


class AnthropicProvider:
    name = "anthropic"

    def available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def generate(self, prompt: str, **kwargs) -> Dict[str, object]:
        return {
            "provider": self.name,
            "prompt": prompt,
            "response": "Simulated Anthropic response",
            "meta": kwargs,
        }
