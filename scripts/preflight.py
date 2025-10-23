import sys
import re
import pathlib
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Directories to scan for typographical leaks related to aiogram imports.
SCAN_DIRS: Iterable[str] = ("app", "lunia_core", "scripts", "infra", "tests", ".")
# Minimal requirement manifests that must remain free from optional telegram deps.
MINIMAL_FILES = (
    ROOT / "requirements.txt",
    ROOT / "lunia_core" / "requirements" / "base_minimal.txt",
)

BAD_TYPO = (r"\baioogram\b", r"\baiiogram\b", r"\baoiogram\b")


def scan_typos() -> list[str]:
    offenders: list[str] = []
    for directory in SCAN_DIRS:
        path = ROOT / directory
        if not path.exists():
            continue
        for file in path.rglob("*"):
            if not file.is_file():
                continue
            if file.suffix.lower() not in {".py", ".txt", ".yml", ".yaml"}:
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for pattern in BAD_TYPO:
                if re.search(pattern, text):
                    offenders.append(str(file.relative_to(ROOT)))
                    break
    return offenders


def scan_minimal_for_telegram() -> list[str]:
    offenders: list[str] = []
    for manifest in MINIMAL_FILES:
        if not manifest.exists():
            continue
        text = manifest.read_text(encoding="utf-8", errors="ignore")
        if re.search(r"\baiogram\b", text) or re.search(r"\baiohttp\b", text):
            offenders.append(str(manifest.relative_to(ROOT)))
    return offenders


def main() -> None:
    bad = scan_typos()
    if bad:
        print("❌ Preflight failed: found typos around aiogram in:")
        for entry in bad:
            print(" -", entry)
        sys.exit(1)

    leak = scan_minimal_for_telegram()
    if leak:
        print("❌ Preflight failed: aiogram/aiohttp found in minimal requirements:")
        for entry in leak:
            print(" -", entry)
        sys.exit(1)

    print("✅ Preflight OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
