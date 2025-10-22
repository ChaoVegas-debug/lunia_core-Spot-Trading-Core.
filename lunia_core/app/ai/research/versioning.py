"""Utilities for model version tracking via MLflow and DVC.

The helpers are intentionally defensive: they degrade gracefully when MLflow or
DVC are not installed so that the offline CI pipeline can execute the same
code paths without network access.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

try:  # pragma: no cover - optional dependency
    import mlflow  # type: ignore
except Exception:  # pragma: no cover - offline fallback
    mlflow = None  # type: ignore

try:  # pragma: no cover - optional dependency
    from dvc import api as dvc_api  # type: ignore
except Exception:  # pragma: no cover - offline fallback
    dvc_api = None  # type: ignore

from app.monitoring.alerts import AlertManager


@dataclass
class VersioningConfig:
    experiment_name: str = "lunia-core"
    enable_drift_alerts: bool = True
    drift_threshold: float = 0.15


class VersionTracker:
    """High level helper for logging model versions and monitoring drift."""

    def __init__(self, config: VersioningConfig | None = None) -> None:
        self.config = config or VersioningConfig()
        self.alerts = AlertManager()

    def log_model_version(
        self,
        model_name: str,
        metrics: Dict[str, float],
        artifacts_path: str | None = None,
    ) -> None:
        if mlflow is None:
            return
        experiment = mlflow.get_experiment_by_name(self.config.experiment_name)
        if experiment is None:
            mlflow.create_experiment(self.config.experiment_name)
        with mlflow.start_run(run_name=model_name):
            for key, value in metrics.items():
                mlflow.log_metric(key, value)
            if artifacts_path and Path(artifacts_path).exists():
                mlflow.log_artifacts(artifacts_path)

    def get_dvc_resource(
        self, path: str, repo: Optional[str] = None
    ) -> Optional[bytes]:
        if dvc_api is None:
            return None
        with contextlib.suppress(Exception):
            return dvc_api.read(path=path, repo=repo)
        return None

    def check_drift(
        self,
        metric_name: str,
        baseline: float,
        current: float,
        context: Optional[Dict[str, str]] = None,
    ) -> None:
        if not self.config.enable_drift_alerts:
            return
        if baseline == 0:
            return
        delta = abs(current - baseline) / abs(baseline)
        if delta >= self.config.drift_threshold:
            message = (
                f"Model drift detected for {metric_name}: baseline={baseline:.4f} current={current:.4f} "
                f"delta={delta:.2%}"
            )
            self.alerts.notify_critical(message, context=context or {})


def register_artifact(path: str, description: str) -> None:
    tracker = VersionTracker()
    metadata = {"description": description, "path": path}
    tracker.log_model_version("artifact-registration", metadata)


def is_versioning_enabled() -> bool:
    return (
        os.getenv("MLFLOW_TRACKING_URI") is not None
        or os.getenv("DVC_REPO") is not None
    )
