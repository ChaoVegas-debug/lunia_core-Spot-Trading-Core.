#!/usr/bin/env bash
set -e

echo "[verify] Running infra health checks..."
python scripts/health/all_checks.py
echo "[verify] Infrastructure health passed."
