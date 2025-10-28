#!/usr/bin/env python3
import sys, socket
try:
    s = socket.create_connection(("localhost", 5672), timeout=1.5)
    s.close()
    print("✅ RabbitMQ alive")
    sys.exit(0)
except Exception as e:
    print(f"⚠️ RabbitMQ unreachable: {e}")
    sys.exit(1)
