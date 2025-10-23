import sys, re, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
BAD = [r"\baioogram\b", r"\baiiogram\b", r"\baoiogram\b"]
FILES = [
    ROOT/"lunia_core"/"requirements"/"requirements.txt",
    ROOT/"lunia_core"/"requirements"/"base.txt",
    ROOT/"lunia_core"/"requirements"/"base_minimal.txt",
    ROOT/"requirements.txt",
]
def main():
    fail = []
    for base in (ROOT/"lunia_core").rglob("*.txt"):
        try:
            t = base.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for p in BAD:
            if re.search(p, t):
                fail.append(str(base))
    for f in FILES:
        if f.exists():
            t = f.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"\baiogram\b", t) or re.search(r"\baiohttp\b", t):
                if f.name in ("base_minimal.txt","requirements.txt"):
                    fail.append(str(f))
    if fail:
        print("❌ Preflight failed — remove aiogram/aiohttp from minimal and fix typos:")
        for x in sorted(set(fail)): print(" -", x)
        sys.exit(1)
    print("✅ Preflight OK")
if __name__ == "__main__":
    main()
