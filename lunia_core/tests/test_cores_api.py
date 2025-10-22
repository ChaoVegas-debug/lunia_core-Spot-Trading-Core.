from __future__ import annotations

import json

from app.services.api.flask_app import app


def test_cores_endpoint_returns_json():
    client = app.test_client()
    response = client.get("/api/v1/cores/")
    assert response.status_code == 200
    payload = json.loads(response.data.decode())
    assert "cores" in payload
