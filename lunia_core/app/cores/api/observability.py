"""Observability endpoints for the cores runtime."""

from __future__ import annotations

import time
from typing import Any

from app.compat.flask import Blueprint, jsonify

from ..runtime.supervisor import SUPERVISOR

router = Blueprint("cores_observability", __name__)
_start_ts = time.time()


@router.route("/cores/health", methods=["GET"])
def health() -> Any:
    snapshot = SUPERVISOR.snapshot()
    return jsonify(
        {"status": "ok", "uptime": time.time() - _start_ts, "cores": snapshot}
    )


__all__ = ["router"]
