"""Fallback provider used when others are unavailable."""

from __future__ import annotations

from typing import Dict


class FallbackProvider:
    name = "fallback"

    def available(self) -> bool:
        return True

    def generate(self, prompt: str, **kwargs) -> Dict[str, object]:
        return {
            "provider": self.name,
            "prompt": prompt,
            "response": "Fallback response",
            "meta": kwargs,
        }
