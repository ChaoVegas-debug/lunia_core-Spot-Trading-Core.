from app.services.resilience.failover import (engage_llm_fallback,
                                              enter_read_only_mode,
                                              promote_backup_exchange)


def test_promote_backup_exchange_writes_state(tmp_path, monkeypatch):
    marker = tmp_path / "failover.json"
    monkeypatch.setattr("app.services.resilience.failover.FAILOVER_STATE", marker)
    result = promote_backup_exchange("binance", "okx", "test")
    assert marker.exists()
    payload = marker.read_text(encoding="utf-8")
    assert "binance" in payload and "okx" in payload
    assert result["active"] == "okx"


def test_enter_read_only_mode_marks_state(tmp_path, monkeypatch):
    marker = tmp_path / "read.flag"
    monkeypatch.setattr("app.services.resilience.failover.READ_ONLY_MARKER", marker)
    enter_read_only_mode("chaos")
    assert marker.exists()


def test_engage_llm_fallback_marks_state(tmp_path, monkeypatch):
    marker = tmp_path / "llm.flag"
    monkeypatch.setattr("app.services.resilience.failover.LLM_FALLBACK_MARKER", marker)
    engage_llm_fallback("limit")
    assert marker.exists()
