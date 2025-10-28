#!/usr/bin/env python3
import os, sys
OFFLINE = os.environ.get("OFFLINE_CI") == "1"
try:
    import redis  # type: ignore
except Exception as e:
    if OFFLINE:
        print(f"⏭️  Redis check skipped (OFFLINE_CI=1, import error: {e})")
        sys.exit(0)
    print(f"⚠️  Redis import failed: {e}")
    sys.exit(1)

try:
    r = redis.Redis(host=os.environ.get("REDIS_HOST","localhost"), port=6379, socket_connect_timeout=1)
    r.ping()
    print("✅ Redis alive")
    sys.exit(0)
except Exception as e:
    if OFFLINE:
        print(f"⏭️  Redis ping skipped (OFFLINE_CI=1, {e})")
        sys.exit(0)
    print(f"⚠️  Redis unreachable: {e}")
    sys.exit(1)
