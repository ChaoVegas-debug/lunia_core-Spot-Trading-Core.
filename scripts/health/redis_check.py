#!/usr/bin/env python3
import sys
try:
    import redis
    r = redis.Redis(host="localhost", port=6379, socket_connect_timeout=1)
    r.ping()
    print("✅ Redis alive")
    sys.exit(0)
except Exception as e:
    print(f"⚠️ Redis unreachable: {e}")
    sys.exit(1)
