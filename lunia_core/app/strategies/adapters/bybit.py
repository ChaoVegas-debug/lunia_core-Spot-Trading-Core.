"""Bybit API proxy adapter."""

from __future__ import annotations

from typing import Any, Dict

from .base import HMACProxyAdapter, ProxyResponse


class BybitProxyAdapter(HMACProxyAdapter):
    """Minimal Bybit proxy adapter leveraging HMAC signatures."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        super().__init__(
            name="bybit",
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
        )

    def place_order(
        self, symbol: str, side: str, qty: float, price: float | None = None
    ) -> ProxyResponse:
        payload: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
        }
        if price is not None:
            payload["price"] = price
        return super().place_order("/order", payload)
