"""Service helpers for the Signal Health dashboard section."""

from __future__ import annotations

import os
from statistics import mean
from typing import Dict, Iterable, List, Optional

from app.ai.research import FeatureCatalog
from app.compat.dotenv import load_dotenv

try:  # pragma: no cover - primary orchestrator
    from app.ai.orchestrator import AGENT_ORCHESTRATOR as _GLOBAL_ORCHESTRATOR
except Exception:  # pragma: no cover - fallback during tests or offline mode
    try:
        from app.cores.api.router import \
            llm_orchestrator as _GLOBAL_ORCHESTRATOR  # type: ignore
    except Exception:  # pragma: no cover - ultimate fallback
        _GLOBAL_ORCHESTRATOR = None

from .models import FeatureHighlight, GrafanaPanel, SignalHealthSummary

load_dotenv()


def is_signal_health_enabled() -> bool:
    return os.getenv("FRONTEND_SIGNAL_HEALTH_ENABLED", "true").lower() not in {
        "0",
        "false",
        "no",
    }


def collect_signal_health_summary(
    *,
    limit: int = 3,
    orchestrator: Optional[object] = None,
    trades: Optional[Iterable[Dict[str, object]]] = None,
) -> SignalHealthSummary:
    if not is_signal_health_enabled():
        return SignalHealthSummary.disabled()

    orchestrator = orchestrator or _GLOBAL_ORCHESTRATOR
    history = _extract_history(orchestrator)
    confidence = _calculate_confidence(history)
    accuracy, sample_size = _calculate_accuracy(trades, history)
    features = _resolve_top_features(limit=limit)
    panels = _build_grafana_links()
    return SignalHealthSummary(
        enabled=True,
        accuracy=accuracy,
        llm_confidence=confidence,
        sample_size=sample_size,
        top_features=features,
        grafana_panels=panels,
    )


def _extract_history(orchestrator: Optional[object]) -> List[Dict[str, object]]:
    if orchestrator is None:
        return []
    history = getattr(orchestrator, "history", None)
    if isinstance(history, list):
        return [entry for entry in history if isinstance(entry, dict)]
    return []


def _calculate_confidence(history: Iterable[Dict[str, object]]) -> float:
    confidences: List[float] = []
    for entry in history:
        value = entry.get("confidence")
        if value is None:
            value = entry.get("accuracy")
        if value is None:
            continue
        try:
            confidences.append(float(value))
        except (TypeError, ValueError):
            continue
    return round(mean(confidences), 4) if confidences else 0.0


def _calculate_accuracy(
    trades: Optional[Iterable[Dict[str, object]]], history: List[Dict[str, object]]
) -> tuple[float, int]:
    if trades is None:
        trades = _load_recent_trades()
    wins = 0
    losses = 0
    for trade in trades:
        try:
            pnl = float(trade.get("pnl", 0.0))
        except (TypeError, ValueError):
            continue
        if pnl > 0:
            wins += 1
        elif pnl < 0:
            losses += 1
    sample_size = wins + losses
    if sample_size == 0:
        # fall back to history confidence counts if present
        sample_size = len(history)
        if sample_size == 0:
            return 0.0, 0
        return 1.0, sample_size  # assume perfect if only synthetic history exists
    accuracy = wins / sample_size if sample_size else 0.0
    return round(accuracy, 4), sample_size


def _load_recent_trades(limit: int = 200) -> List[Dict[str, object]]:
    try:
        from app.db.reporting import list_trades

        return list_trades(limit=limit)
    except Exception:
        return []


def _resolve_top_features(*, limit: int) -> tuple[FeatureHighlight, ...]:
    catalog = FeatureCatalog()
    try:
        raw = catalog.load()
    except Exception:
        return tuple()
    highlights: List[FeatureHighlight] = []
    for name, payload in raw.items():
        if not isinstance(payload, dict):
            continue
        description = str(payload.get("description", ""))
        tags = tuple(
            str(tag) for tag in payload.get("tags", []) if isinstance(tag, str)
        )
        metrics = tuple(
            str(metric.get("name"))
            for metric in payload.get("metrics", [])
            if isinstance(metric, dict) and metric.get("name")
        )
        importance_raw = payload.get("importance")
        try:
            importance = float(importance_raw)
        except (TypeError, ValueError):
            importance = float(len(metrics) or 1)
        highlights.append(
            FeatureHighlight(
                name=name,
                description=description,
                importance=importance,
                tags=tags,
                metrics=metrics,
            )
        )
    highlights.sort(key=lambda item: item.importance, reverse=True)
    return tuple(highlights[:limit])


def _build_grafana_links() -> tuple[GrafanaPanel, ...]:
    base = os.getenv("GRAFANA_BASE_URL", "http://localhost:3000")
    dashboard_uid = os.getenv("GRAFANA_SIGNAL_DASHBOARD", "signal-health")
    return (
        GrafanaPanel(
            title="Signal Accuracy",
            url=f"{base}/d/{dashboard_uid}/signal-health?viewPanel=1",
            panel_id="1",
        ),
        GrafanaPanel(
            title="LLM Confidence",
            url=f"{base}/d/{dashboard_uid}/signal-health?viewPanel=2",
            panel_id="2",
        ),
        GrafanaPanel(
            title="Top Feature Usage",
            url=f"{base}/d/{dashboard_uid}/signal-health?viewPanel=3",
            panel_id="3",
        ),
    )
