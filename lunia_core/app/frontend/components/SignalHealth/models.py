"""Data models for the Signal Health dashboard section."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Tuple


@dataclass(slots=True)
class FeatureHighlight:
    """Represents a feature surfaced in the signal health view."""

    name: str
    description: str
    importance: float
    tags: Tuple[str, ...]
    metrics: Tuple[str, ...]


@dataclass(slots=True)
class GrafanaPanel:
    """Link metadata for Grafana panels related to signal health."""

    title: str
    url: str
    panel_id: str


@dataclass(slots=True)
class SignalHealthSummary:
    """Aggregated information displayed in the signal health section."""

    enabled: bool
    accuracy: float
    llm_confidence: float
    sample_size: int
    top_features: Tuple[FeatureHighlight, ...]
    grafana_panels: Tuple[GrafanaPanel, ...]

    @classmethod
    def disabled(cls) -> "SignalHealthSummary":
        return cls(
            enabled=False,
            accuracy=0.0,
            llm_confidence=0.0,
            sample_size=0,
            top_features=tuple(),
            grafana_panels=tuple(),
        )

    def with_panels(self, panels: Iterable[GrafanaPanel]) -> "SignalHealthSummary":
        return SignalHealthSummary(
            enabled=self.enabled,
            accuracy=self.accuracy,
            llm_confidence=self.llm_confidence,
            sample_size=self.sample_size,
            top_features=self.top_features,
            grafana_panels=tuple(panels),
        )

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "accuracy": self.accuracy,
            "llm_confidence": self.llm_confidence,
            "sample_size": self.sample_size,
            "top_features": [
                {
                    "name": feature.name,
                    "description": feature.description,
                    "importance": feature.importance,
                    "tags": list(feature.tags),
                    "metrics": list(feature.metrics),
                }
                for feature in self.top_features
            ],
            "grafana_panels": [
                {"title": panel.title, "url": panel.url, "panel_id": panel.panel_id}
                for panel in self.grafana_panels
            ],
        }
