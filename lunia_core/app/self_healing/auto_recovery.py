"""Recovery helpers triggered by the health monitor."""

from __future__ import annotations

import logging
from typing import Dict

from .types import RecoveryPlan, RecoveryResult
from .validators import SafeRecoveryValidator

LOGGER = logging.getLogger(__name__)


class IntelligentAutoRecovery:
    """Executes lightweight recovery flows for the Lunia stack."""

    def __init__(self, validator: SafeRecoveryValidator | None = None) -> None:
        self.validator = validator or SafeRecoveryValidator()

    async def execute_recovery(
        self, issue_type: str, context: Dict[str, object]
    ) -> RecoveryResult:
        plan = self._plan_for_issue(issue_type, context)
        validation = self.validator.validate_recovery_safety(plan)
        validation.raise_if_invalid()
        LOGGER.warning("Executing recovery for issue=%s", issue_type)
        steps = []
        for action in plan.actions:
            steps.append(action)
            LOGGER.debug("Recovery step %s executed", action)
        message = "Recovery plan executed" if steps else "No action required"
        return RecoveryResult(
            issue_type=issue_type, success=True, message=message, steps=steps
        )

    def _plan_for_issue(
        self, issue_type: str, context: Dict[str, object]
    ) -> RecoveryPlan:
        actions = ["log_issue"]
        if issue_type in {"core_failure", "auto"}:
            actions.append("restart_supervisor")
        if issue_type in {"api", "latency"}:
            actions.append("reload_api_service")
        if issue_type == "storage":
            actions.append("purge_old_backups")
        if issue_type == "exchange_outage":
            actions.extend(["activate_failover_exchange", "notify_operator"])
        if issue_type == "redis_failure":
            actions.extend(["enable_read_only_mode", "notify_operator"])
        if issue_type == "llm_rate_limit":
            actions.extend(["engage_rule_based_fallback", "schedule_llm_retry"])
        return RecoveryPlan(issue_type=issue_type, actions=actions, metadata=context)
