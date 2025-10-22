"""Compliance automation loops triggered by the scheduler."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from ...logging.compliance import (collect_audit_snapshot,
                                   generate_access_review_report)

LOGGER = logging.getLogger(__name__)


def start_compliance_loops(
    interval_hours: int = 24, review_interval_days: int = 90
) -> None:
    """Start background loops for weekly audit dumps and quarterly access reviews."""

    LOGGER.info(
        "Starting compliance loops: audit every %sh, review every %sd",
        interval_hours,
        review_interval_days,
    )
    audit_thread = threading.Thread(
        target=_audit_loop, args=(interval_hours,), daemon=True
    )
    review_thread = threading.Thread(
        target=_review_loop, args=(review_interval_days,), daemon=True
    )
    audit_thread.start()
    review_thread.start()


def _audit_loop(interval_hours: int) -> None:
    while True:
        try:
            collect_audit_snapshot()
        except Exception as exc:  # pragma: no cover - best effort logging
            LOGGER.warning("Failed to collect audit snapshot: %s", exc)
        time.sleep(max(interval_hours, 1) * 3600)


def _review_loop(interval_days: int) -> None:
    while True:
        try:
            today = datetime.utcnow()
            if today.day == 1:
                generate_access_review_report()
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Access review generation failed: %s", exc)
        time.sleep(max(interval_days, 1) * 86400)
