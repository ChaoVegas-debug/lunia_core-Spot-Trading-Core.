"""Integration test for API idempotency handling."""

from __future__ import annotations

import pytest

pytest.importorskip("flask", reason="Flask not available in offline mode")

pytestmark = [pytest.mark.integration, pytest.mark.requires_flask]


def test_spot_trade_idempotency(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.risk import get_idempotency_store
    from app.services.api.flask_app import app

    store = get_idempotency_store()
    store.clear()

    with app.test_client() as client:
        payload = {"symbol": "BTCUSDT", "side": "BUY", "qty": 0.01}
        headers = {"Idempotency-Key": "api-test-1"}

        first = client.post("/trade/spot/demo", json=payload, headers=headers)
        assert first.status_code == 200
        assert first.json.get("ok") is True

        second = client.post("/trade/spot/demo", json=payload, headers=headers)
        assert second.status_code == 400
        assert second.json.get("reason") == "duplicate_order"
