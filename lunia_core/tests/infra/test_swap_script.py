from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SWAP_SCRIPT = REPO_ROOT / "deploy" / "scripts" / "enable_encrypted_swap.sh"


def test_swap_script_mentions_cryptsetup_and_env():
    content = SWAP_SCRIPT.read_text(encoding="utf-8")
    assert "ENABLE_ENCRYPTED_SWAP" in content
    assert "cryptsetup" in content
    assert "swapon" in content
