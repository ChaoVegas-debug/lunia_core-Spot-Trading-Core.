from app.logging import compliance
from app.logging.compliance import (collect_audit_snapshot,
                                    generate_access_review_report)


def test_compliance_snapshots_written(tmp_path, monkeypatch):
    monkeypatch.setattr(compliance, "LOG_DIR", tmp_path)
    compliance.COMPLIANCE_DIR = tmp_path / "compliance"
    compliance.COMPLIANCE_DIR.mkdir()
    compliance.AUDIT_LOG = tmp_path / "audit.log"
    compliance.AUDIT_LOG.write_text("test-entry", encoding="utf-8")
    snapshot = collect_audit_snapshot()
    assert snapshot.exists()
    report = generate_access_review_report(["security@lunia.ai"])
    assert report.exists()
    payload = report.read_text(encoding="utf-8")
    assert "security@lunia.ai" in payload


def test_compliance_upload_skipped_without_endpoint(monkeypatch, tmp_path):
    monkeypatch.setattr(compliance, "LOG_DIR", tmp_path)
    compliance.COMPLIANCE_DIR = tmp_path / "compliance"
    compliance.COMPLIANCE_DIR.mkdir()
    compliance.AUDIT_LOG = tmp_path / "audit.log"
    path = collect_audit_snapshot()
    assert path.exists()
