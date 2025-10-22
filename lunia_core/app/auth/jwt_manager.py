"""Minimal JWT helper preserving compatibility with legacy OPS tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional


class JWTValidationError(Exception):
    """Raised when a JWT token cannot be validated."""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("utf-8")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)


@dataclass
class TokenPayload:
    """Container describing a validated token."""

    claims: Dict[str, Any]
    token_type: str


class JWTManager:
    """Simple HMAC based JWT encoder/decoder with legacy token fallback."""

    def __init__(
        self,
        secret: Optional[str] = None,
        algorithm: str = "HS256",
        legacy_token: Optional[str] = None,
        default_tenant: str | None = None,
    ) -> None:
        self.algorithm = algorithm
        self.secret = (
            secret
            or os.getenv("JWT_SECRET")
            or os.getenv("OPS_API_TOKEN")
            or "change-me"
        ).encode("utf-8")
        self.legacy_token = legacy_token or os.getenv("OPS_API_TOKEN")
        self.default_tenant = default_tenant or os.getenv("DEFAULT_TENANT", "public")

    # ------------------------------------------------------------------
    def encode(self, payload: Dict[str, Any], expires_in: int = 3600) -> str:
        header = {"alg": self.algorithm, "typ": "JWT"}
        body = dict(payload)
        body.setdefault("exp", int(time.time()) + int(expires_in))
        segments = [
            _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8")),
            _b64url_encode(json.dumps(body, separators=(",", ":")).encode("utf-8")),
        ]
        signing_input = ".".join(segments).encode("utf-8")
        signature = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        segments.append(_b64url_encode(signature))
        return ".".join(segments)

    # ------------------------------------------------------------------
    def decode(self, token: str, verify_exp: bool = True) -> Dict[str, Any]:
        if not token:
            raise JWTValidationError("missing token")
        if self.legacy_token and token == self.legacy_token:
            return {
                "sub": "legacy-ops",
                "roles": ["owner"],
                "tenant": self.default_tenant,
                "scopes": ["*"],
                "legacy": True,
            }
        parts = token.split(".")
        if len(parts) != 3:
            raise JWTValidationError("invalid token structure")
        header_raw, payload_raw, signature_raw = parts
        signing_input = f"{header_raw}.{payload_raw}".encode("utf-8")
        expected = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        actual = _b64url_decode(signature_raw)
        if not hmac.compare_digest(expected, actual):
            raise JWTValidationError("signature mismatch")
        payload_bytes = _b64url_decode(payload_raw)
        payload = json.loads(payload_bytes.decode("utf-8"))
        if verify_exp and "exp" in payload and int(payload["exp"]) < int(time.time()):
            raise JWTValidationError("token expired")
        return payload

    # ------------------------------------------------------------------
    def validate(self, token: str) -> TokenPayload:
        payload = self.decode(token)
        token_type = "legacy" if payload.get("legacy") else "jwt"
        return TokenPayload(claims=payload, token_type=token_type)

    # ------------------------------------------------------------------
    def build_context(self, token: Optional[str]) -> TokenPayload:
        if not token:
            raise JWTValidationError("missing token")
        try:
            return self.validate(token)
        except JWTValidationError as exc:
            raise exc


__all__ = ["JWTManager", "JWTValidationError", "TokenPayload"]
