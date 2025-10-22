from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LOGGING_DIR = REPO_ROOT / "lunia_core" / "infra" / "logging"


def test_vector_pipeline_targets_elastic_and_s3():
    vector_config = (LOGGING_DIR / "vector.toml").read_text(encoding="utf-8")
    assert "sinks.elasticsearch" in vector_config
    assert "sinks.s3_archive" in vector_config
    assert "LOG_ARCHIVE_BUCKET" in vector_config


def test_logging_compose_wires_optional_stack():
    compose = (LOGGING_DIR / "docker-compose.logging.yml").read_text(encoding="utf-8")
    assert "vector" in compose
    assert "INFRA_PROD_ENABLED" in compose
    assert "elasticsearch" in compose
