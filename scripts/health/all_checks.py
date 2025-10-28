#!/usr/bin/env python3
import os, subprocess, sys
py = os.environ.get("PYTHON", sys.executable or "python3")
checks = [
    [py, "scripts/health/redis_check.py"],
    [py, "scripts/health/rabbitmq_check.py"],
]
ok = True
for cmd in checks:
    code = subprocess.call(cmd)
    ok = ok and (code == 0)
print("✅ All infra checks passed." if ok else "⚠️ Some services unavailable.")
sys.exit(0 if ok else 1)
