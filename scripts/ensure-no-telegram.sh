#!/usr/bin/env bash
set -euo pipefail

echo "[guard] verifying minimal requirements have NO aiogram/aiohttp..."
if grep -Eiq '(aiogram|aiohttp)' requirements.txt lunia_core/requirements/base_minimal.txt; then
  echo "❌ guard: aiogram/aiohttp detected in minimal requirements"
  exit 1
fi
echo "✅ guard: ok"
