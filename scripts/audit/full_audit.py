import pathlib
import re
import sys
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
ERRORS: list[str] = []


def _read(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""


def _err(message: str) -> None:
    ERRORS.append(message)


def _must_exist(paths: Iterable[str]) -> None:
    for rel in paths:
        if not (ROOT / rel).exists():
            _err(f"[missing] {rel}")


def check_requirements() -> None:
    req_top = ROOT / "requirements.txt"
    if not req_top.exists():
        _err("[req] missing requirements.txt")
    else:
        text = _read(req_top)
        if "base_minimal" not in text:
            _err("[req] requirements.txt must point to lunia_core/requirements/base_minimal.txt")

    minimal = ROOT / "lunia_core/requirements/base_minimal.txt"
    if not minimal.exists():
        _err("[req] missing lunia_core/requirements/base_minimal.txt")
    else:
        text = _read(minimal)
        if re.search(r"\b(aiogram|aiohttp)\b", text, re.IGNORECASE):
            _err("[req] aiogram/aiohttp must NOT be in base_minimal.txt")

    base_txt = ROOT / "lunia_core/requirements/base.txt"
    if base_txt.exists():
        text = _read(base_txt)
        if "-r base_minimal.txt" not in text:
            _err("[req] lunia_core/requirements/base.txt must include '-r base_minimal.txt'")


def check_typos_and_imports() -> None:
    typo_hits: set[str] = set()
    aiogram_hits: set[str] = set()
    allowed_prefixes = (
        "lunia_core/app/services/telegram",
        "app/services/telegram",
    )
    import_pattern = re.compile(r"^\s*(?:from|import)\s+aiogram", re.MULTILINE)

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".py", ".txt", ".yml", ".yaml"}:
            continue
        text = _read(path)
        if re.search(r"\baioogram\b|\baiiogram\b|\baoiogram\b", text):
            typo_hits.add(str(path.relative_to(ROOT)))
        if suffix == ".py" and import_pattern.search(text):
            rel = str(path.relative_to(ROOT))
            if not rel.startswith(allowed_prefixes):
                aiogram_hits.add(rel)

    if typo_hits:
        _err("[typo] Found typos around aiogram in: " + ", ".join(sorted(typo_hits)))
    if aiogram_hits:
        _err(
            "[imports] Direct aiogram imports outside telegram facade: "
            + ", ".join(sorted(aiogram_hits))
        )


def check_pydantic_v2() -> None:
    decorator_pattern = re.compile(r"^\s*@root_validator\b", re.MULTILINE)
    offenders = [
        str(path.relative_to(ROOT))
        for path in ROOT.rglob("*.py")
        if decorator_pattern.search(_read(path))
    ]
    if offenders:
        _err("[pydantic] @root_validator found (Pydantic v2 incompatible): " + ", ".join(sorted(offenders)))


def check_structure() -> None:
    _must_exist(
        [
            "lunia_core/app/main.py",
            "lunia_core/app/core/scheduler/__init__.py",
            "lunia_core/app/core/guard/__init__.py",
            "lunia_core/app/services/telegram/__init__.py",
            "infra/docker-compose.yml",
            ".github/workflows/verify.yml",
            "scripts/preflight.py",
            "scripts/ensure-no-telegram.sh",
            "scripts/health/all_checks.py",
            ".env.example.3a",
        ]
    )


def check_admin_routes() -> None:
    candidates = (
        ROOT / "lunia_core/app/api/routes_admin.py",
        ROOT / "app/api/routes_admin.py",
    )
    if not any(path.exists() for path in candidates):
        _err("[admin] routes_admin.py not found (admin endpoints)")


def main() -> None:
    check_requirements()
    check_typos_and_imports()
    check_pydantic_v2()
    check_structure()
    check_admin_routes()

    if ERRORS:
        print("❌ Full System Audit FAILED")
        for message in ERRORS:
            print(" -", message)
        sys.exit(1)
    print("✅ Full System Audit PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
