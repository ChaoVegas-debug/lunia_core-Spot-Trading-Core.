"""Compliance evidence helpers."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from app.compat.requests import requests

LOGGER = logging.getLogger(__name__)
LOG_DIR = Path(__file__).resolve().parents[3] / "logs"
AUDIT_LOG = LOG_DIR / "audit.log"
COMPLIANCE_DIR = LOG_DIR / "compliance"
COMPLIANCE_DIR.mkdir(parents=True, exist_ok=True)


def collect_audit_snapshot() -> Path:
    """Collect weekly audit snapshots for compliance evidence."""

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    destination = COMPLIANCE_DIR / f"audit-{timestamp}.json"
    payload: Dict[str, object] = {
        "created_at": timestamp,
        "entries": [],
    }
    if AUDIT_LOG.exists():
        payload["entries"] = AUDIT_LOG.read_text(encoding="utf-8").splitlines()[-1000:]
    destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    LOGGER.info("Weekly audit snapshot saved to %s", destination)
    if os.getenv("S3_AUDIT_BUCKET"):
        _upload_to_s3(destination, os.getenv("S3_AUDIT_BUCKET"))
    return destination


def generate_access_review_report(recipients: List[str] | None = None) -> Path:
    """Produce a quarterly access review report summarising active accounts."""

    timestamp = datetime.utcnow().strftime("%Y%m%d")
    destination = COMPLIANCE_DIR / f"access-review-{timestamp}.json"
    report = {
        "generated_at": timestamp,
        "recipients": recipients or [],
        "active_roles": os.getenv(
            "ACTIVE_RBAC_ROLES", "owner,admin,viewer,auditor"
        ).split(","),
    }
    destination.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOGGER.info("Quarterly access review report generated: %s", destination)
    return destination


def _upload_to_s3(path: Path, bucket: str) -> None:
    """Upload a file to S3 using signed requests when available."""

    endpoint = os.getenv("S3_AUDIT_ENDPOINT")
    if not endpoint:
        LOGGER.debug("No S3 endpoint configured, skipping upload")
        return
    files = {"file": (path.name, path.read_bytes())}
    response = requests.post(
        endpoint, params={"bucket": bucket}, files=files, timeout=5
    )
    if response.status_code >= 400:
        LOGGER.warning("S3 upload failed for %s: %s", path, response.text)
    else:
        LOGGER.info("S3 upload completed for %s", path)
