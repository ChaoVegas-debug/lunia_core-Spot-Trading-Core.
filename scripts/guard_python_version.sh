#!/usr/bin/env bash
set -euo pipefail

# Target major/minor can be supplied as the first argument (default 3.11)
REQUIRED_VERSION="${1:-3.11}"
if [[ ! "$REQUIRED_VERSION" =~ ^([0-9]+)\.([0-9]+)$ ]]; then
  echo "❌ Invalid version constraint: '$REQUIRED_VERSION' (expected <major>.<minor>)"
  exit 1
fi
REQ_MAJOR="${BASH_REMATCH[1]}"
REQ_MINOR="${BASH_REMATCH[2]}"

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
if [ "$MAJOR" -ne "$REQ_MAJOR" ] || [ "$MINOR" -ne "$REQ_MINOR" ]; then
  echo "❌ Python $REQUIRED_VERSION is required (detected $VERSION_STR)"
  exit 1
fi

echo "✅ Python version guard passed"
