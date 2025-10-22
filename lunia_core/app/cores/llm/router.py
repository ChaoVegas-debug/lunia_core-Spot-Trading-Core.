"""Routing logic between LLM providers."""

from __future__ import annotations

from typing import Dict


class LLMRouter:
    def select_provider(
        self, signal: Dict[str, object], preferred: str | None = None
    ) -> str:
        if preferred:
            return preferred
        signal_type = str(signal.get("type", "trade")).lower()
        if signal_type == "analysis":
            return "anthropic"
        if signal_type == "override":
            return "openai"
        return "local"
