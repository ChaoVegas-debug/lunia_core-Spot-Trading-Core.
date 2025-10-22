"""Kraken API proxy adapter."""

from __future__ import annotations

from typing import Any, Dict

from .base import HMACProxyAdapter, ProxyResponse


class KrakenProxyAdapter(HMACProxyAdapter):
    """Kraken adapter using proxy semantics."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        api_secret: str,
    ) -> None:
        super().__init__(
            name="kraken",
            base_url=base_url,
            api_key=api_key,
            api_secret=api_secret,
        )

    def place_order(
        self, pair: str, type_: str, volume: float, price: float | None = None
    ) -> ProxyResponse:
        payload: Dict[str, Any] = {
            "pair": pair,
            "type": type_,
            "volume": volume,
        }
        if price is not None:
            payload["price"] = price
        return super().place_order("/0/private/AddOrder", payload)
