import os
import sys


def main() -> None:
    if os.getenv("OFFLINE_CI") == "1" or os.getenv("SKIP_INFRA") == "1":
        print("redis: SKIP (offline mode)")
        sys.exit(0)
    try:
        import redis  # lazy import
    except Exception:
        print("redis: SKIP (redis package not installed)")
        sys.exit(0)

    url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        client = redis.Redis.from_url(url)
        client.ping()
        print("redis: OK")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        print(f"redis: FAIL — {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
