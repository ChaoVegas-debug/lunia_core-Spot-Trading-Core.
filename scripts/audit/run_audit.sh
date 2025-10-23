#!/usr/bin/env bash
set -euo pipefail
echo "[audit] running Full System Audit (offline-safe)…"
python scripts/audit/full_audit.py
echo "[audit] done."
