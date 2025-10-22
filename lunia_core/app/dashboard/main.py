"""FastAPI dashboard for Lunia."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    from fastapi import Depends, FastAPI, HTTPException, Request
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
except Exception:  # pragma: no cover
    FastAPI = None  # type: ignore
    Request = object  # type: ignore
    HTMLResponse = object  # type: ignore
    StaticFiles = object  # type: ignore
    Jinja2Templates = object  # type: ignore

from app.cores.runtime.registry import REGISTRY
from app.frontend.components.SignalHealth import (
    collect_signal_health_summary, is_signal_health_enabled)

from .auth import DashboardAuth

LOGGER = logging.getLogger(__name__)


def create_app() -> Any:
    if FastAPI is None:
        LOGGER.warning("FastAPI not installed; dashboard is disabled")
        return None
    app = FastAPI(title="Lunia Dashboard")
    base_path = Path(__file__).resolve().parent
    templates = Jinja2Templates(directory=str(base_path / "templates"))
    auth = DashboardAuth()

    app.mount(
        "/static", StaticFiles(directory=str(base_path / "static")), name="static"
    )
    signal_health_enabled = is_signal_health_enabled()
    templates.env.globals["signal_health_enabled"] = signal_health_enabled

    def _require_auth(request: Request) -> None:
        user = request.headers.get("X-User")
        if not auth.is_allowed(user):
            raise HTTPException(status_code=403, detail="forbidden")

    @app.get("/", response_class=HTMLResponse)
    async def overview(request: Request, _: None = Depends(_require_auth)) -> Any:
        return templates.TemplateResponse(
            "overview.html",
            {
                "request": request,
                "cores": REGISTRY.snapshot(),
            },
        )

    @app.get("/cores", response_class=HTMLResponse)
    async def cores(request: Request, _: None = Depends(_require_auth)) -> Any:
        return templates.TemplateResponse(
            "cores.html",
            {"request": request, "cores": REGISTRY.snapshot()},
        )

    @app.get("/backtest", response_class=HTMLResponse)
    async def backtest(request: Request, _: None = Depends(_require_auth)) -> Any:
        return templates.TemplateResponse(
            "backtest.html",
            {"request": request, "reports": []},
        )

    if signal_health_enabled:

        @app.get("/signal-health", response_class=HTMLResponse)
        async def signal_health(
            request: Request, _: None = Depends(_require_auth)
        ) -> Any:
            summary = collect_signal_health_summary()
            return templates.TemplateResponse(
                "signal_health.html",
                {
                    "request": request,
                    "summary": summary,
                },
            )

    return app


app = create_app()
