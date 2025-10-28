#!/usr/bin/env python3
import os
import subprocess
import sys

CHECKS = [
    ("redis", [sys.executable, "scripts/health/redis_check.py"]),
    ("rabbitmq", [sys.executable, "scripts/health/rabbitmq_check.py"]),
]


def main() -> None:
    if os.getenv("OFFLINE_CI") == "1" or os.getenv("SKIP_INFRA") == "1":
        print("health: SKIP (offline mode)")
        sys.exit(0)

    status = 0
    for name, cmd in CHECKS:
        try:
            print(f"→ Checking {name}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            output = (result.stdout or result.stderr).strip()
            if output:
                print(output)
            if result.returncode != 0:
                status = 1
        except Exception as exc:  # pragma: no cover - runtime failure path
            print(f"{name}: FAIL ({exc})")
            status = 1
    sys.exit(status)


if __name__ == "__main__":
    main()
