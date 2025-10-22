"""High level orchestrator that selects LLM providers and caches responses."""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

from .cache import LLMCache
from .evaluator import ModelEvaluator
from .providers import (AnthropicProvider, FallbackProvider, LocalLLMProvider,
                        OpenAIProvider)
from .router import LLMRouter

LOGGER = logging.getLogger(__name__)


class MultiLLMOrchestrator:
    def __init__(self) -> None:
        self.router = LLMRouter()
        self.cache = LLMCache()
        self.evaluator = ModelEvaluator()
        self.providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "local": LocalLLMProvider(),
            "fallback": FallbackProvider(),
        }
        self.history: list[Dict[str, Any]] = []

    def route_signal(
        self, signal: Dict[str, Any], preferred_provider: str | None = None
    ) -> Dict[str, Any]:
        cache_key = f"{signal.get('type')}:{signal.get('symbol')}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        provider_key = self.router.select_provider(signal, preferred_provider)
        provider = self.providers.get(provider_key) or self.providers["fallback"]
        if not provider.available():
            provider = self.providers["fallback"]
        response = provider.generate(signal.get("prompt", ""), signal=signal)
        self.cache.set(cache_key, response)
        self.history.append(
            {"provider": provider.name, "accuracy": 1.0, "latency_ms": 100}
        )
        LOGGER.info("LLM signal routed to %s", provider.name)
        return response

    def evaluate_models(self) -> Dict[str, float]:
        return self.evaluator.evaluate(self.history)

    def train_from_history(self, training_data: Iterable[Dict[str, Any]]) -> None:
        self.history.extend(training_data)
