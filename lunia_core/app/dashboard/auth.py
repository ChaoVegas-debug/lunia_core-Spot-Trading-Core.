"""Simple token based auth for the dashboard."""

from __future__ import annotations

import os


class DashboardAuth:
    def __init__(self) -> None:
        admins = os.getenv("DASHBOARD_ADMINS", "")
        self.allowed = {item.strip() for item in admins.split(",") if item.strip()}

    def is_allowed(self, user_id: str | None) -> bool:
        if not self.allowed:
            return True
        return bool(user_id and user_id in self.allowed)
