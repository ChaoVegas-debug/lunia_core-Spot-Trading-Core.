#!/usr/bin/env bash
set -euo pipefail

export TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-dummy}"
export ADMIN_CHAT_ID="${ADMIN_CHAT_ID:-0}"
export EXCHANGE_MODE="${EXCHANGE_MODE:-mock}"
export PYTHONPATH="${PYTHONPATH:-$(pwd)}"

PYTHON_BIN="${PYTHON_BIN:-python}"
if [ -x ".venv/bin/python" ]; then
  PYTHON_BIN=".venv/bin/python"
fi

"${PYTHON_BIN}" - <<'PY'
from app.services.telegram.bot import create_app

bot, dp = create_app(dry_run=True)
print("[smoke] Telegram bot initialised with handlers", len(dp.handlers["message"]))
PY

echo "[smoke] Telegram bot smoke test passed"
