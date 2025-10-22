"""Extended client for interacting with cores API."""

from __future__ import annotations

import os
from typing import Any, Dict

from app.compat.requests import requests


class EnhancedCoreClient:
    def __init__(self) -> None:
        self.base_url = os.getenv("CORE_API_URL", "http://localhost:8000/api/v1")
        self.token = os.getenv("OPS_API_TOKEN")
        self.host = os.getenv("HOST", "localhost")
        self.dashboard_port = int(os.getenv("DASHBOARD_PORT", "3000"))

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get_backtest_results(self, strategy: str | None = None) -> Dict[str, Any]:
        resp = requests.get(
            f"{self.base_url}/backtest/results", headers=self._headers()
        )
        data = resp.json() if hasattr(resp, "json") else {}
        if strategy:
            return data.get(strategy, data)
        return data

    def get_llm_stats(self) -> Dict[str, Any]:
        resp = requests.get(f"{self.base_url}/llm/stats", headers=self._headers())
        return resp.json() if hasattr(resp, "json") else {}

    def trigger_update(self) -> Dict[str, Any]:
        resp = requests.post(f"{self.base_url}/system/backup", headers=self._headers())
        return resp.json() if hasattr(resp, "json") else {}
