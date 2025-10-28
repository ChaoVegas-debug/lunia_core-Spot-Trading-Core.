#!/usr/bin/env python3
import os
import sys

def main() -> None:
    if os.getenv("OFFLINE_CI") == "1" or os.getenv("SKIP_INFRA") == "1":
        print("rabbitmq: SKIP (offline mode)")
        sys.exit(0)
    try:
        import pika  # type: ignore  # lazy import
    except Exception:
        print("rabbitmq: SKIP (pika not installed)")
        sys.exit(0)

    url = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    try:
        params = pika.URLParameters(url)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()
        channel.queue_declare(queue="healthcheck_test", passive=False)
        channel.close()
        connection.close()
        print("rabbitmq: OK")
        sys.exit(0)
    except Exception as exc:  # pragma: no cover - runtime failure path
        print(f"rabbitmq: FAIL — {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
