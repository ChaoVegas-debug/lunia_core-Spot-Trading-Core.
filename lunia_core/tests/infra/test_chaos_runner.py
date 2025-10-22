from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "lunia_core" / "infra" / "chaos" / "run_chaos_scenarios.sh"


def test_chaos_script_contains_all_scenarios():
    content = SCRIPT.read_text(encoding="utf-8")
    assert "exchange outage" in content.lower()
    assert "redis failure" in content.lower()
    assert "llm rate limit" in content.lower()
    assert "INFRA_PROD_ENABLED" in content
