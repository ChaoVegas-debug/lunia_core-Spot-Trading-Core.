"""Binance Spot exchange client supporting mock, testnet and live modes."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Dict, Optional

import app.compat.requests as requests
from app.compat.requests import HAVE_REQUESTS

from ..utils.quote_detector import (get_current_quote, register_quote_balances,
                                    split_symbol)
from .base import IExchange

logger = logging.getLogger(__name__)

MOCK_PRICES: Dict[str, float] = {
    "BTCUSDT": 30000.0,
    "ETHUSDT": 2000.0,
    "BNBUSDT": 300.0,
    "BTCUSDC": 30000.0,
    "ETHUSDC": 2000.0,
    "BNBUSDC": 300.0,
    "BTCEUR": 28000.0,
    "ETHEUR": 1900.0,
    "BTCPLN": 120000.0,
}


class BinanceSpotError(RuntimeError):
    """Raised for Binance Spot related failures."""


@dataclass
class BinanceSpot(IExchange):
    """Binance Spot client with mock, testnet and live trading support."""

    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    use_testnet: bool = False
    mock: Optional[bool] = None
    session: requests.Session = field(default_factory=requests.Session)

    def __post_init__(self) -> None:
        live_base_url = "https://api.binance.com"
        testnet_base_url = "https://testnet.binance.vision"
        self.base_url = testnet_base_url if self.use_testnet else live_base_url
        self.timeout = 10
        self.retries = 3

        force_mock = os.getenv("BINANCE_FORCE_MOCK", "false").lower() == "true"
        live_trading_enabled = (
            os.getenv("BINANCE_LIVE_TRADING", "true").lower() == "true"
        )
        min_notional_default = "11" if not self.use_testnet else "5"
        self.min_notional_usd = float(
            os.getenv("BINANCE_MIN_NOTIONAL_USD", min_notional_default)
        )

        if self.mock is None:
            self.mock = (
                force_mock
                or not live_trading_enabled
                or not HAVE_REQUESTS
                or not self.api_key
                or not self.api_secret
            )
        elif force_mock:
            self.mock = True

        if self.mock:
            mode = "testnet" if self.use_testnet else "live"
            logger.info("BinanceSpot running in %s mock mode", mode)
        else:
            logger.info(
                "BinanceSpot initialized for %s trading (min notional ≈ %.2f USD)",
                "testnet" if self.use_testnet else "live",
                self.min_notional_usd,
            )

    # Utilities
    def _build_headers(self) -> Dict[str, str]:

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-MBX-APIKEY"] = self.api_key
        return headers

    def _mock_price(self, symbol: str) -> float:
        symbol_upper = symbol.upper()
        price = MOCK_PRICES.get(symbol_upper)
        if price is None:
            base, _quote = split_symbol(symbol_upper)
            fallback_symbol = f"{base}USDT" if base else symbol_upper
            price = MOCK_PRICES.get(fallback_symbol, 1.0)
        logger.info("Returning mock price %.2f for %s", price, symbol)
        return price

    def _mock_response(self, data: Dict[str, object]) -> Dict[str, object]:
        logger.debug("Mock response generated: %s", data)
        return data

    def _handle_response(self, response: requests.Response) -> Dict[str, object]:
        try:
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - error path
            logger.error("Binance API request failed: %s", exc)
            raise BinanceSpotError(str(exc)) from exc
        try:
            payload = response.json()
        except json.JSONDecodeError as exc:  # pragma: no cover - error path
            logger.error("Invalid JSON received from Binance: %s", exc)
            raise BinanceSpotError("invalid-json") from exc
        logger.debug("Binance API response: %s", payload)
        return payload

    def _signed_params(self, params: Dict[str, object]) -> Optional[Dict[str, object]]:
        if not self.api_secret:
            logger.warning("Missing API secret; cannot sign request. Using mock mode")
            return None
        query = "&".join(f"{key}={value}" for key, value in params.items())
        signature = hmac.new(
            self.api_secret.encode(), query.encode(), hashlib.sha256
        ).hexdigest()
        signed = dict(params)
        signed["signature"] = signature
        return signed

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, object]] = None,
        signed: bool = False,
    ) -> Dict[str, object]:
        if self.mock:
            raise BinanceSpotError("mock-mode")
        if signed and (not self.api_key or not self.api_secret):
            raise BinanceSpotError("credentials-missing")

        params = params or {}
        request_params = params
        if signed:
            params_with_timestamp = dict(params)
            params_with_timestamp.setdefault("timestamp", int(time.time() * 1000))
            signed_params = self._signed_params(params_with_timestamp)
            if signed_params is None:
                raise BinanceSpotError("signing-failed")
            request_params = signed_params

        url = f"{self.base_url}{path}"
        headers = self._build_headers()
        last_exc: Optional[Exception] = None
        for attempt in range(1, self.retries + 1):
            try:
                if method.upper() == "GET":
                    resp = self.session.get(
                        url,
                        params=request_params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                elif method.upper() == "POST":
                    resp = self.session.post(
                        url,
                        params=request_params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                elif method.upper() == "DELETE":
                    resp = self.session.delete(
                        url,
                        params=request_params,
                        headers=headers,
                        timeout=self.timeout,
                    )
                else:
                    raise ValueError(f"Unsupported method {method}")
                return self._handle_response(resp)
            except (requests.RequestException, BinanceSpotError) as exc:
                last_exc = exc
                logger.warning(
                    "Binance request %s %s failed on attempt %s/%s: %s",
                    method,
                    path,
                    attempt,
                    self.retries,
                    exc,
                )
                time.sleep(0.5)
        raise BinanceSpotError(str(last_exc))

    def _validate_side(self, side: str) -> str:
        side_upper = side.upper()
        if side_upper not in {"BUY", "SELL"}:
            logger.warning("Invalid order side received: %s", side)
            raise BinanceSpotError("invalid-side")
        return side_upper

    # Public API
    def get_price(self, symbol: str) -> float:
        logger.info("Fetching price for symbol %s", symbol)
        if self.mock:
            return self._mock_price(symbol)

        try:
            payload = self._request(
                "GET", "/api/v3/ticker/price", {"symbol": symbol.upper()}
            )
            price = float(payload["price"])
            logger.debug("Received price %.2f for %s", price, symbol)
            return price
        except (
            BinanceSpotError,
            ValueError,
        ) as exc:  # pragma: no cover - network issues
            logger.warning("Price request failed (%s); falling back to mock", exc)
            self.mock = True
            return self._mock_price(symbol)

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        type: str = "MARKET",
    ) -> Dict[str, object]:
        side_upper = self._validate_side(side)
        logger.info(
            "Placing %s order for %s qty=%.8f type=%s", side_upper, symbol, qty, type
        )
        if self.mock:
            order_id = f"mock-{int(time.time() * 1000)}"
            price = self._mock_price(symbol)
            return self._mock_response(
                {
                    "symbol": symbol.upper(),
                    "orderId": order_id,
                    "side": side_upper,
                    "type": type,
                    "origQty": qty,
                    "status": "FILLED",
                    "price": price,
                    "executedQty": qty,
                    "cummulativeQuoteQty": price * qty,
                    "transactTime": int(time.time() * 1000),
                }
            )

        if not self.api_key or not self.api_secret:
            logger.warning("API credentials missing; using mock order response")
            self.mock = True
            return self.place_order(symbol, side, qty, type)

        qty_to_submit = qty
        if not self.mock and self.min_notional_usd > 0:
            market_price = self.get_price(symbol)
            min_qty = self.min_notional_usd / max(market_price, 1e-9)
            if qty_to_submit < min_qty:
                logger.info(
                    "Adjusting quantity from %.8f to %.8f to satisfy min notional %.2f USD",
                    qty_to_submit,
                    min_qty,
                    self.min_notional_usd,
                )
                qty_to_submit = round(min_qty, 8)

        try:
            payload = self._request(
                "POST",
                "/api/v3/order",
                {
                    "symbol": symbol.upper(),
                    "side": side_upper,
                    "type": type,
                    "quantity": qty_to_submit,
                },
                signed=True,
            )
            return payload
        except BinanceSpotError as exc:  # pragma: no cover - network issues
            logger.warning("Order placement failed (%s); using mock", exc)
            self.mock = True
            return self.place_order(symbol, side, qty, type)

    def cancel_order(self, order_id: str) -> Dict[str, object]:
        logger.info("Cancelling order %s", order_id)
        if self.mock:
            return self._mock_response(
                {
                    "orderId": order_id,
                    "status": "CANCELED",
                }
            )

        if not self.api_key or not self.api_secret:
            logger.warning("Missing credentials; returning mock cancel response")
            self.mock = True
            return self.cancel_order(order_id)

        try:
            return self._request(
                "DELETE",
                "/api/v3/order",
                {"orderId": order_id},
                signed=True,
            )
        except BinanceSpotError as exc:  # pragma: no cover - network issues
            logger.warning("Order cancellation failed (%s); using mock", exc)
            self.mock = True
            return self.cancel_order(order_id)

    def get_position(self, symbol: str) -> Optional[Dict[str, object]]:
        logger.info("Fetching position for symbol %s", symbol)
        if self.mock:
            balance = 1.0 if symbol.upper() in MOCK_PRICES else 0.0
            return self._mock_response(
                {
                    "symbol": symbol.upper(),
                    "free": balance,
                    "locked": 0.0,
                }
            )

        if not self.api_key or not self.api_secret:
            logger.warning("Missing credentials; returning mock position")
            self.mock = True
            return self.get_position(symbol)

        try:
            balances = self.get_balances()
        except BinanceSpotError as exc:  # pragma: no cover - network issues
            logger.warning("Balance request failed (%s); using mock", exc)
            self.mock = True
            return self.get_position(symbol)

        symbol_upper = symbol.upper()
        base_asset, _ = split_symbol(symbol_upper)
        asset = balances.get(base_asset)
        if asset is None:
            return None
        return {
            "symbol": symbol_upper,
            "free": asset.get("free", 0.0),
            "locked": asset.get("locked", 0.0),
        }

    def get_balances(self) -> Dict[str, Dict[str, float]]:
        if self.mock:
            quote = get_current_quote()
            balances = {"USDT": {"free": 1000.0, "locked": 0.0}}
            balances.setdefault(quote, {"free": 1000.0, "locked": 0.0})
            register_quote_balances(balances)
            return balances
        account = self._request("GET", "/api/v3/account", signed=True)
        balances: Dict[str, Dict[str, float]] = {}
        for balance in account.get("balances", []):
            balances[balance["asset"]] = {
                "free": float(balance.get("free", 0.0)),
                "locked": float(balance.get("locked", 0.0)),
            }
        register_quote_balances(balances)
        return balances

    def get_order(self, symbol: str, order_id: str) -> Dict[str, object]:
        if self.mock:
            return {
                "symbol": symbol.upper(),
                "orderId": order_id,
                "status": "FILLED",
            }
        return self._request(
            "GET",
            "/api/v3/order",
            {"symbol": symbol.upper(), "orderId": order_id},
            signed=True,
        )
