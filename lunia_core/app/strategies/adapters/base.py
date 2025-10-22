"""Common proxy adapter base classes."""

from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional

from app.compat.requests import requests


@dataclass
class ProxyResponse:
    status: str
    payload: Dict[str, Any]


class HMACProxyAdapter:
    """Proxy adapter that signs requests for downstream exchanges."""

    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        api_key: str,
        api_secret: str,
        recv_window: int = 5000,
        session: Optional["requests.Session"] = None,
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.recv_window = recv_window
        self.session = session or (
            requests.Session() if getattr(requests, "Session", None) else None
        )

    def _timestamp(self) -> int:
        return int(time.time() * 1000)

    def _sign(self, payload: Mapping[str, Any]) -> str:
        sorted_items = sorted(payload.items())
        query = "&".join(f"{key}={value}" for key, value in sorted_items)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return signature

    def _prepare(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(payload)
        payload.setdefault("timestamp", self._timestamp())
        payload.setdefault("recvWindow", self.recv_window)
        payload["signature"] = self._sign(payload)
        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json",
        }
        return {
            "url": f"{self.base_url}{path}",
            "headers": headers,
            "json": payload,
        }

    def place_order(self, path: str, payload: Dict[str, Any]) -> ProxyResponse:
        request_payload = self._prepare(path, payload)
        if self.session is None:
            return ProxyResponse(status="SIMULATED", payload=request_payload)
        response = self.session.post(**request_payload, timeout=10)
        if response.status_code >= 400:
            return ProxyResponse(
                status="ERROR",
                payload={"code": response.status_code, "body": response.text},
            )
        return ProxyResponse(status="OK", payload=response.json())

    def get_price(
        self, path: str, params: Dict[str, Any] | None = None
    ) -> ProxyResponse:
        params = params or {}
        request_payload = self._prepare(path, params)
        if self.session is None:
            return ProxyResponse(status="SIMULATED", payload=request_payload)
        response = self.session.get(
            request_payload["url"],
            headers=request_payload["headers"],
            params=params,
            timeout=10,
        )
        if response.status_code >= 400:
            return ProxyResponse(
                status="ERROR",
                payload={"code": response.status_code, "body": response.text},
            )
        return ProxyResponse(status="OK", payload=response.json())
