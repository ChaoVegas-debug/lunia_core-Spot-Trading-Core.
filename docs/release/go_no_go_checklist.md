# Go / No-Go Checklist

| Метрика | Цель | Факт | Источник |
|---------|------|------|----------|
| Sharpe (3м) | > 1.3 | _to be filled после 72ч прогонов_ | reports/perf/ | 
| Hit-rate | > 55 % | _pending_ | Grafana `signal_health` |
| Explainability | > 8/10 | _pending_ | `/api/portfolio/explain` агрегаты |
| Critical CVE | 0 | 0 | `make vuln-scan` |
| 72h Uptime | ≥ 99.95 % | _требует мониторинга_ | Prometheus `uptime` |
| Load (users/orders/backtests) | 100 / 500+/10+ | см. `tools/load_test.py` отчёт | reports/load_test_summary.json |

**Процедуры:**
- Завершить 72-часовой мониторинг до переключения в 100 % объём.
- Подтвердить отчёты pentest и SOC 2 в `reports/compliance/`.
- При отклонении любой метрики вернуть систему в testnet (`BINANCE_USE_TESTNET=true`).

