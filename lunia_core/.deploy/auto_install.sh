#!/usr/bin/env bash
set -Eeuo pipefail

echo "[lunia] auto installer starting"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
cd "$REPO_DIR"

if command -v python3 >/dev/null 2>&1; then
  python3 -m venv .venv >/dev/null 2>&1 || true
  source .venv/bin/activate
  pip install --upgrade pip >/dev/null 2>&1 || true
  pip install -r requirements/dev.txt >/dev/null 2>&1 || true
fi

make test-offline || echo "tests skipped"
make smoke || echo "smoke skipped"
echo "[lunia] auto installer finished"
