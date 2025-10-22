# Lunia Core — User Guide (Production Release)

Этот документ описывает, как конечные пользователи взаимодействуют с Lunia Core в боевом режиме.

## 1. Быстрый старт

1. Получите доступ к панели управления: `https://<ваш-домен>/ui`.
2. Авторизуйтесь через SSO или API-token (см. security policy).
3. Проверьте дашборд **Overview**, чтобы убедиться в зелёном состоянии всех ядер.
4. Выполните smoke-проверки:
   - `curl -fsS http://localhost:8000/healthz`
   - `python tools/load_test.py --users 10 --orders 50`
5. Включите auto-mode (`/auto_on` в Telegram или `/api/v1/ops/auto_on`).

## 2. Управление стратегиями

- **Spot/HFT/Futures/Options** ядра включаются/выключаются в разделе **Cores**.
- Для ручного сигнала используйте `/signal` в API или кнопку «Сделать» в Telegram.
- Вес стратегии меняется через `/spot/strategies` (API) или карточку в боте.

## 3. Ордеры

- Минимальный объём микро-заявки определяется `BINANCE_MIN_NOTIONAL_USD` (по умолчанию 11 USD).
- Канареечный режим удерживает 5 % капитала, пока SLA не будет выполнен.
- Shadow-trading позволяет протестировать стратегию без реальных сделок.

## 4. Мониторинг

- `/metrics` → Prometheus (основные метрики: PnL, latency, success rate).
- Grafana дашборды:
  - `core_performance`
  - `risk_metrics`
  - `signal_health`
- Telegram уведомления: алерты SLO/SLA, circuit breakers, compliance события.

## 5. Обслуживание

- Еженедельный отчёт `/daily` в Telegram содержит ROI, hit-rate, капы капитала.
- `make smoke` → API/бот/scheduler health.
- `make cores-up` / `make cores-down` управляет ядрами.

## 6. Troubleshooting

| Симптом | Диагностика | Решение |
|---------|-------------|---------|
| Ядро выключено (circuit breaker) | `/api/v1/cores/{name}` | Проверить дневной PnL, выполнить `/ops/start_all` |
| Redis недоступен | Логи `logs/alerts.log` | Система переключится в read-only, восстановить Redis |
| LLM rate-limit | `/api/v1/llm/stats` | Система переключится на rule-based, проверить квоты |

