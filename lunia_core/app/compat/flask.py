from __future__ import annotations

try:
    from flask import Blueprint, Flask, Response, jsonify, request

    HAVE_FLASK = True
except Exception:  # pragma: no cover - offline shim branch
    HAVE_FLASK = False

    class _FakeReq:
        def __init__(self) -> None:
            self.args: dict = {}
            self.json: dict | None = {}
            self.headers: dict = {}

    request = _FakeReq()

    class _FakeResp:
        def __init__(
            self, data: object = None, status: int = 200, mimetype: str | None = None
        ) -> None:
            self.data = data
            self.status_code = status
            self.mimetype = mimetype or "application/json"

    class _FakeBP:
        def __init__(self, name: str, import_name: str) -> None:
            self.name = name
            self.import_name = import_name

        def route(self, *args, **kwargs):  # type: ignore[override]
            def _wrap(fn):
                return fn

            return _wrap

        def get(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def post(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def put(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def delete(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

    class _FakeApp:
        def __init__(self, *args, **kwargs) -> None:
            self.name = kwargs.get("import_name", "offline-flask-app")

        def route(self, *args, **kwargs):  # type: ignore[override]
            def _wrap(fn):
                return fn

            return _wrap

        def register_blueprint(self, *args, **kwargs) -> None:  # pragma: no cover
            return None

        def run(self, *args, **kwargs) -> None:  # pragma: no cover
            print("⚠️ Flask offline: mock server started")

        def get(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def post(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def put(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

        def delete(self, *args, **kwargs):  # type: ignore[override]
            return self.route(*args, **kwargs)

    def Flask(*args, **kwargs):  # type: ignore[misc]
        return _FakeApp(*args, **kwargs)

    def Blueprint(name: str, import_name: str):  # type: ignore[misc]
        return _FakeBP(name, import_name)

    def jsonify(data):  # type: ignore[misc]
        return data

    def Response(data: object = None, status: int = 200, mimetype: str | None = None):  # type: ignore[misc]
        return _FakeResp(data=data, status=status, mimetype=mimetype)


__all__ = [
    "Blueprint",
    "Flask",
    "HAVE_FLASK",
    "Response",
    "jsonify",
    "request",
]
