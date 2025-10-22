"""Scheduler entrypoint running rebalancer and digest loops."""

from __future__ import annotations

import argparse
import os
import threading

from ...core.metrics import ensure_metrics_server
from ..api.flask_app import agent
from .compliance import start_compliance_loops
from .digest import start_digest_loop
from .rebalancer import start_rebalancer


def run_scheduler() -> None:
    ensure_metrics_server(9101)
    threads = [
        threading.Thread(
            target=start_rebalancer,
            args=(agent,),
            kwargs={"interval_seconds": 900},
            daemon=True,
        ),
        threading.Thread(
            target=start_digest_loop,
            args=(agent,),
            kwargs={"interval_seconds": 3600},
            daemon=True,
        ),
    ]
    if os.getenv("INFRA_PROD_ENABLED", "false").lower() == "true":
        threads.append(
            threading.Thread(
                target=start_compliance_loops,
                kwargs={"interval_hours": 24, "review_interval_days": 90},
                daemon=True,
            )
        )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scheduler worker")
    parser.add_argument(
        "--healthcheck", action="store_true", help="Run healthcheck and exit"
    )
    return parser.parse_args()


def main() -> None:  # pragma: no cover - runtime entry
    args = parse_args()
    if args.healthcheck:
        # Lightweight check to ensure components can be initialised
        ensure_metrics_server(9101)
        print("ok")
        return
    run_scheduler()


if __name__ == "__main__":  # pragma: no cover
    main()
