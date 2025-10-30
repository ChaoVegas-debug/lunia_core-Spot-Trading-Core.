#!/usr/bin/env bash
set -euo pipefail

# If PYTHON env provided use it, else default to python3
PYBIN="${PYTHON:-python3}"
if ! command -v "$PYBIN" >/dev/null 2>&1; then
  echo "❌ Interpreter not found: $PYBIN"
  exit 1
fi

VERSION_STR="$($PYBIN -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
MAJOR="$($PYBIN -c 'import sys; print(sys.version_info[0])')"
MINOR="$($PYBIN -c 'import sys; print(sys.version_info[1])')"

echo "[guard] Using $PYBIN -> $VERSION_STR"
if [ "$MAJOR" -ne 3 ] || [ "$MINOR" -ne 11 ]; then
  echo "❌ Python 3.11 is required (detected $VERSION_STR)"
  exit 1
fi

echo "✅ Python version guard passed"
