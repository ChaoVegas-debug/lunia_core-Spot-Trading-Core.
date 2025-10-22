from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FALCO_RULES = REPO_ROOT / "deploy" / "falco" / "falco-rules.yaml"
FALLBACK_RULES = (
    REPO_ROOT / "deploy" / "falco" / "fallback_branch" / "legacy-rules.yaml"
)


def test_falco_rules_cover_python_and_swap():
    content = FALCO_RULES.read_text(encoding="utf-8")
    assert "Lunia Python Exec" in content
    assert "Lunia Swap Modification" in content


def test_fallback_branch_present():
    assert FALLBACK_RULES.exists(), "Fallback security policy must be preserved"
