"""Typed containers used by the self-healing subsystem."""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(slots=True)
class HealthIssue:
    """Represents a single anomaly detected during a health check."""

    component: str
    severity: str
    description: str
    details: Dict[str, Any] = field(default_factory=dict)

    def is_critical(self) -> bool:
        return self.severity.lower() == "critical"


@dataclass(slots=True)
class HealthReport:
    """Aggregated result of a health check."""

    timestamp: _dt.datetime
    issues: List[HealthIssue] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def has_critical_issues(self) -> bool:
        return any(issue.is_critical() for issue in self.issues)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "issues": [issue.__dict__ for issue in self.issues],
            "metrics": self.metrics,
        }


@dataclass(slots=True)
class RecoveryPlan:
    """A proposed recovery plan for a specific issue."""

    issue_type: str
    actions: List[str]
    requires_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RecoveryResult:
    """Outcome of a recovery attempt."""

    issue_type: str
    success: bool
    message: str
    steps: List[str] = field(default_factory=list)
    follow_up: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_type": self.issue_type,
            "success": self.success,
            "message": self.message,
            "steps": self.steps,
            "follow_up": self.follow_up,
        }


@dataclass(slots=True)
class ValidationResult:
    """Validation information returned before executing recovery."""

    valid: bool
    reasons: List[str] = field(default_factory=list)
    advisory: Optional[str] = None

    def raise_if_invalid(self) -> None:
        if not self.valid:
            raise RuntimeError(
                ", ".join(self.reasons) or "Recovery action rejected by validator"
            )
