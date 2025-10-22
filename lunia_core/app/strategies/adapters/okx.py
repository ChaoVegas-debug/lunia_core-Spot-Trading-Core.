"""OKX API proxy adapter."""

from __future__ import annotations

from typing import Any, Dict

from .base import HMACProxyAdapter, ProxyResponse


class OKXProxyAdapter(HMACProxyAdapter):
    """OKX adapter using the generic HMAC proxy layer."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        super().__init__(
            name="okx",
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
        )

    def place_order(
        self, inst_id: str, side: str, sz: float, px: float | None = None
    ) -> ProxyResponse:
        payload: Dict[str, Any] = {
            "instId": inst_id,
            "side": side,
            "sz": sz,
        }
        if px is not None:
            payload["px"] = px
        return super().place_order("/trade/order", payload)
