from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CI_PIPELINE = REPO_ROOT / "deploy" / "ci.yml"


def test_ci_includes_syft_and_cosign():
    content = CI_PIPELINE.read_text(encoding="utf-8")
    assert "syft" in content, "SBOM generation using syft must be configured"
    assert "cosign" in content, "Image signing with cosign must be configured"
    assert "pytest tests/infra" in content, "Infra tests must run inside CI"
