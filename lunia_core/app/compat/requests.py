"""Compatibility shim for the :mod:`requests` library."""

from __future__ import annotations

from typing import Any, Dict, Optional

try:  # pragma: no cover - executed in production environments
    import requests as _requests  # type: ignore
except Exception:  # pragma: no cover - offline fallback
    HAVE_REQUESTS = False

    class _Resp:
        """Lightweight response object for offline mode."""

        def __init__(
            self,
            url: str = "",
            status_code: int = 200,
            text: str = "",
            json_data: Optional[Dict[str, Any]] = None,
        ) -> None:
            self.url = url
            self.status_code = status_code
            self.text = text or "offline-ok"
            self._json = json_data or {}

        def json(self) -> Dict[str, Any]:  # noqa: D401 - mimic requests.Response
            return self._json

        def raise_for_status(self) -> None:  # noqa: D401
            if self.status_code >= 400:
                raise RuntimeError(f"status {self.status_code}")

    class _Session:
        """Minimal session stub providing request helpers."""

        def get(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return _Resp(url=url)

        def post(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return _Resp(url=url)

        def put(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return _Resp(url=url)

        def delete(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return _Resp(url=url)

    def get(url: str, *args: Any, **kwargs: Any) -> _Resp:
        return _Resp(url=url)

    def post(url: str, *args: Any, **kwargs: Any) -> _Resp:
        return _Resp(url=url)

    def put(url: str, *args: Any, **kwargs: Any) -> _Resp:
        return _Resp(url=url)

    def delete(url: str, *args: Any, **kwargs: Any) -> _Resp:
        return _Resp(url=url)

    def Session() -> _Session:  # noqa: N802 - keep parity with requests API
        return _Session()

    class _CompatModule:
        """Expose a requests-like API for offline tests."""

        def __init__(self) -> None:
            self.RequestException = RuntimeError
            self.Session = _Session
            self.Response = _Resp

        def get(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return get(url, *args, **kwargs)

        def post(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return post(url, *args, **kwargs)

        def put(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return put(url, *args, **kwargs)

        def delete(self, url: str, *args: Any, **kwargs: Any) -> _Resp:
            return delete(url, *args, **kwargs)

    requests = _CompatModule()
else:
    HAVE_REQUESTS = True

    def get(url: str, *args: Any, **kwargs: Any):  # type: ignore[override]
        return _requests.get(url, *args, **kwargs)

    def post(url: str, *args: Any, **kwargs: Any):  # type: ignore[override]
        return _requests.post(url, *args, **kwargs)

    def put(url: str, *args: Any, **kwargs: Any):  # type: ignore[override]
        return _requests.put(url, *args, **kwargs)

    def delete(url: str, *args: Any, **kwargs: Any):  # type: ignore[override]
        return _requests.delete(url, *args, **kwargs)

    def Session() -> "_requests.Session":  # type: ignore[name-defined]
        return _requests.Session()

    requests = _requests

__all__ = [
    "HAVE_REQUESTS",
    "Session",
    "delete",
    "get",
    "post",
    "put",
    "requests",
]
