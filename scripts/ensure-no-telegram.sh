#!/usr/bin/env bash
set -euo pipefail
FILE="lunia_core/requirements/base_minimal.txt"
[ -f "$FILE" ] || { echo "❌ Missing $FILE"; exit 1; }
if grep -Eiq '(aiogram|aiohttp|ai\+?ogram|aio\+?gram)' "$FILE"; then
  echo "❌ Telegram deps found in $FILE"
  exit 1
fi
echo "✅ Guard OK — no Telegram deps in minimal profile."
