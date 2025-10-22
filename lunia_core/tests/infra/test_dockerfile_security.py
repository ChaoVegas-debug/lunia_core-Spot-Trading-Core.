from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = REPO_ROOT / "deploy" / "Dockerfile"


def test_dockerfile_contains_apparmor_reference():
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "apparmor" in content, "Dockerfile must install AppArmor utilities"
    assert (
        "enable_encrypted_swap.sh" in content
    ), "Dockerfile must ship encrypted swap helper"


def test_dockerfile_entrypoint_runs_swap_helper():
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "ENTRYPOINT" in content and "enable_encrypted_swap.sh" in content
    assert "CMD" in content and "python" in content
