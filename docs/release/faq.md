# Lunia Core — FAQ

## Общие вопросы

**Q:** Как включить реальные торги?
**A:** Убедитесь, что заданы `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `BINANCE_USE_TESTNET=false`, `BINANCE_LIVE_TRADING=true` и `BINANCE_FORCE_MOCK=false`. Перезапустите `lunia_api`.

**Q:** Можно ли вернуться в sandbox без остановки сервиса?
**A:** Да. Установите `BINANCE_FORCE_MOCK=true` и выполните `make cores-reload` либо `/ops/stop_all`.

**Q:** Что делать при ошибке LLM?
**A:** Проверить `/api/v1/llm/stats`. Система автоматически переключится на rule-based fallback, пока квоты не восстановятся.

## Торговля

**Q:** Какая минимальная заявка?
**A:** Значение `BINANCE_MIN_NOTIONAL_USD` (по умолчанию 11 USD). Клиент автоматически масштабирует объём.

**Q:** Где смотреть TCA?
**A:** Файл `logs/orders.jsonl` и дашборд `core_performance` содержат latency, slippage и комиссии.

## Поддержка

**Q:** Куда писать об инцидентах?
**A:** Используйте `/alert escalate` в Telegram или создайте тикет в системе поддержки. В runbook приведены контакты on-call.

**Q:** Как выполнить аварийный откат?
**A:** Запустить `make cores-down` и `bash infra/install.sh --rollback`. До отката отключите auto-mode.

