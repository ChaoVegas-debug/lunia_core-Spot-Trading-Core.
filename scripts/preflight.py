#!/usr/bin/env python3
import sys, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
minimal = ROOT / "lunia_core/requirements/base_minimal.txt"
patterns = [r"aiogram", r"aiohttp", r"aio+gram", r"ai+ogram"]

if not minimal.exists():
    print("❌ Missing:", minimal)
    sys.exit(1)

bad = []
for i, line in enumerate(minimal.read_text().splitlines(), start=1):
    for pat in patterns:
        if re.search(pat, line, re.IGNORECASE):
            bad.append((i, line.strip()))

if bad:
    print("❌ Forbidden deps/typos in base_minimal.txt:")
    for ln, text in bad:
        print(f"   line {ln}: {text}")
    sys.exit(1)

print("✅ Preflight OK — minimal profile is Telegram-free.")
