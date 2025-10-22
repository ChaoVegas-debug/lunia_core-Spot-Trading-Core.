# Lunia Core — Production Runbook

## 1. Контакты

| Роль | Имя | Канал |
|------|-----|-------|
| Incident Commander | @lunia_ic | PagerDuty |
| SRE On-call | @lunia_sre | Telegram / Slack |
| Quant Lead | @lunia_quant | Email |

## 2. Ежедневный чеклист

1. Проверить `/api/v1/system/health`.
2. Просмотреть отчёт `/daily` в Telegram (ROI, hit-rate, CAP).
3. Убедиться в отсутствии открытых circuit breakers (`/api/v1/cores/`).
4. Проверить Grafana панели (latency, success rate).
5. Просмотреть журнал `logs/compliance.log` на предмет критичных событий.

## 3. Инциденты

### 3.1 Exchange outage
- Сценарий «Outage» из `infra/chaos/run_chaos_scenarios.sh` выполняет авто-переключение.
- Проверить `/api/v1/system/health` → поле `failover_status` должно быть `active`.
- После восстановления снять failover через `/api/v1/system/recover`.

### 3.2 Redis недоступен
- Система перейдёт в read-only (см. логи resilience).
- Восстановить Redis, выполнить `make cores-reload`.

### 3.3 LLM rate limit
- Мониторинг переключит ядро LLM в rule-based режим.
- Проверьте квоты у провайдеров, затем `/api/v1/llm/stats`.

## 4. Деплой

1. `git pull`
2. `make cores-migrate`
3. `make cores-up`
4. Smoke: `make smoke`, `python tools/load_test.py --users 20 --orders 120`
5. Подтвердить `/api/v1/metrics` и `/ui/signal-health`

## 5. Откат

- Запустить `make cores-down`
- Выполнить `.deploy/auto_install.sh --rollback`
- Установить `BINANCE_FORCE_MOCK=true`, `AUTO_MODE=false`
- Подтвердить, что `/api/v1/cores/` показывает отключенные ядра

## 6. Compliance

- Weekly: `make compliance-report`
- Quarterly: `make access-review`
- Audit evidence сохраняется в S3 (см. `docs/release/security_policy.md`)

