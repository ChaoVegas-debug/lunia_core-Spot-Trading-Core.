#!/usr/bin/env bash
set -euo pipefail
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "[smoke] Checking API health at $BASE_URL/healthz"
if ! curl -fsS "$BASE_URL/healthz" > /dev/null; then
  echo "API health check failed"
  exit 1
fi

echo "[smoke] Checking API metrics at $BASE_URL/metrics"
if ! curl -fsS "$BASE_URL/metrics" > /dev/null; then
  echo "API metrics endpoint failed"
  exit 1
fi

echo "[smoke] API smoke tests passed"
