"""Extra Telegram commands for phase 2 additions."""

from __future__ import annotations

import logging

from .core_client_ext import EnhancedCoreClient

LOGGER = logging.getLogger(__name__)


class EnhancedTelegramCommands:
    def __init__(self, client: EnhancedCoreClient | None = None) -> None:
        self.client = client or EnhancedCoreClient()

    async def dashboard(self, message) -> None:  # pragma: no cover - runtime only
        url = f"http://{self.client.host}:{self.client.dashboard_port}"
        await message.reply(f"📊 Dashboard: {url}")

    async def trigger_update(self, message) -> None:
        LOGGER.info("Manual update requested from Telegram")
        await message.reply("🔄 Обновление запущено (mock)")

    async def run_backtest(self, message, strategy: str) -> None:
        report = self.client.get_backtest_results(strategy)
        await message.reply(f"📈 Бэктест {strategy}: {report}")

    async def llm_stats(self, message) -> None:
        stats = self.client.get_llm_stats()
        await message.reply(f"🤖 LLM stats: {stats}")
