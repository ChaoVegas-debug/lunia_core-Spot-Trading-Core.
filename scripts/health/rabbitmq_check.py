#!/usr/bin/env python3
import os, sys, socket
OFFLINE = os.environ.get("OFFLINE_CI") == "1"
try:
    s = socket.create_connection((os.environ.get("RABBITMQ_HOST","localhost"), 5672), timeout=1.5)
    s.close()
    print("✅ RabbitMQ alive")
    sys.exit(0)
except Exception as e:
    if OFFLINE:
        print(f"⏭️  RabbitMQ check skipped (OFFLINE_CI=1, {e})")
        sys.exit(0)
    print(f"⚠️  RabbitMQ unreachable: {e}")
    sys.exit(1)
