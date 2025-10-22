# Lunia / Aladdin Core v3

Bootstrap of the Lunia/Aladdin trading core with spot exchange mock/testnet integration, Flask API, Telegram bot skeleton, schedulers, guards, installer, Docker Compose, and CI-friendly tests. The layout is designed for Codex-style iteration and future expansion.

## Repository Layout

```
lunia_core/
  app/
    boot.py
    core/
      bus/
        redis_bus.py
      exchange/
        binance_spot.py
        binance_futures.py
        base.py
      ai/
        supervisor.py
        agent.py
      risk/
        manager.py
      portfolio/
        portfolio.py
      capital/
        allocator.py
    services/
      api/
        flask_app.py
      telegram/
        bot.py
      scheduler/
        rebalancer.py
        digest.py
        worker.py
      guard/
        healthcheck.py
        budget_guard.py
    backtester/
      synthetic.py
      engine.py
    boot.py
  Dockerfile
  infra/
    docker-compose.yml
    monitoring/
      prometheus.yml
      grafana/
        provisioning/
          datasources/
          dashboards/
    install.sh
    systemd/lunia_api.service
    systemd/lunia_bot.service
    systemd/lunia_sched.service
    scripts/upgrade.sh
    ci/github-actions.yml
  logs/
    trades.jsonl (created automatically)
  tests/
    test_health.py
    test_risk.py
    test_spot_mock.py
  web/
  .env.example
  requirements/
    base.txt
    backtester.txt
  requirements.txt
```

Logs are stored under `logs/trades.jsonl`. API keys and secrets are configured via `.env` only.

## Environment Preparation

1. Install Python 3.11 and system build tooling (Ubuntu 24.04 ships with everything required):

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git curl
```

2. Clone the repository and enter the project directory:

```bash
git clone <repo>
cd <repo>/lunia_core
```

3. (Optional) create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements/base.txt  # runtime stack
```

To work with developer tooling run `pip install -r requirements/dev.txt` (fakeredis, pytest, black, ruff, mypy, etc.). The fully pinned dependency snapshot lives in `requirements/lock.txt`.

## Quick Start (mock mode)

```bash
cp .env.example .env
sed -i 's/^EXCHANGE_MODE=.*/EXCHANGE_MODE=mock/' .env
sed -i 's/^MOCK_MODE=.*/MOCK_MODE=1/' .env
make dev-deps        # create .venv + install dev requirements (fakeredis, pytest, linters)
make lint            # black + isort + ruff + mypy
make test            # full pytest suite (requires fakeredis)
make test-offline    # fallback run without fakeredis / external deps
make build           # docker compose build
make up              # start api + workers + redis in mock mode
make smoke           # run smoke_api.sh and smoke_bot.sh against local stack
make logs            # tail docker compose logs (Ctrl+C to exit)
```

To stop containers run `make compose-down`. Additional Compose profiles are available: `make up-monitoring` brings up Prometheus and Grafana; `make down-monitoring` tears them down. The mock quick start keeps everything offline by forcing `EXCHANGE_MODE=mock` and `MOCK_MODE=1`.

## Makefile Commands

| Command | Description |
| --- | --- |
| `make venv` | create local virtual environment |
| `make deps` | install runtime stack from `requirements/base.txt` |
| `make dev-deps` | install development stack from `requirements/dev.txt` |
| `make lint` | run black (check), isort (check), ruff, mypy |
| `make fmt` | format sources with black and isort |
| `make test` | execute entire pytest suite |
| `make test-offline` | run pytest without external dependencies (fakeredis fallback) |
| `make test-unit` | run tests located in `tests/unit` |
| `make test-integration` | run tests located in `tests/integration` |
| `make smoke` | execute `scripts/smoke_api.sh` and `scripts/smoke_bot.sh` |
| `make build` | build docker images (`docker compose build`) |
| `make up` | start core services (api, scheduler, arbitrage, redis) |
| `make down` | stop and remove containers and volumes |
| `make compose-down` | alias for `make down` |
| `make compose-logs` | tail docker compose logs |
| `make logs` | tail docker compose logs |
| `make up-monitoring` | start Prometheus and Grafana profile |
| `make down-monitoring` | stop monitoring profile |
| `make clean` | remove virtual environment |
| `make install` | execute `infra/install.sh` from the current checkout (run with sudo) |

## Requirements

* Ubuntu 24.04 or compatible Linux distribution
* Python 3.11+
* Docker / Docker Compose v2 (for containerised workflows)
* Base Python packages from `requirements/base.txt`; optional pandas/numpy extras live in `requirements/backtester.txt`

## Installation (Ubuntu 24.04+)

### One-liner install (run as root)

```bash
git clone <repo_url> lunia_core
cd lunia_core
sudo bash infra/install.sh
```

The installer copies the repository to `/opt/lunia_core`, detects connectivity, and operates in two modes:

* **ONLINE** – installs system packages (git, curl, docker, python3-venv, etc.), creates `.venv`, upgrades `pip`, and installs `requirements/dev.txt`.
* **OFFLINE** – skips network package installation but keeps the project runnable thanks to `app.compat.*` shims. Smoke tests and health checks run without external HTTP calls.

Key behaviours:

* Idempotent reruns; progress streamed to `/var/log/lunia_install.log`.
* Auto-creates `.env` from `.env.example` and applies overrides from environment variables (`TELEGRAM_BOT_TOKEN`, `REDIS_URL`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`, optional `QUOTE_OVERRIDE`).
* Copies systemd unit files to `/etc/systemd/system` (not enabled automatically).
* When Docker is available in ONLINE mode, builds the stack via `docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up -d --build`, then prints `docker compose ps` and recent logs.
* When Docker is unavailable/offline, falls back to `make lint` (ONLINE only), `make test-offline`, and `make smoke`.
* Runs health probes: waits for `http://127.0.0.1:8000/healthz`, and executes `python -m app.services.telegram.bot --healthcheck --dry-run`, `python -m app.services.scheduler.worker --healthcheck --dry-run`, and `python -m app.services.arbitrage.worker --healthcheck --dry-run`.

Quick verification:

```bash
make smoke
curl -fsS http://127.0.0.1:8000/healthz
```

Systemd units are staged in `/etc/systemd/system/`; enable and start them when ready:

```bash
sudo systemctl enable --now lunia_api
sudo systemctl enable --now lunia_sched
sudo systemctl enable --now lunia_arb
# optional when Telegram token is configured
sudo systemctl enable --now lunia_bot
```

### Offline notes

Offline mode keeps the control plane operational using compatibility shims for Flask, requests, pydantic, Prometheus client, and Redis. Real exchange connectivity, Telegram API calls, and Docker image builds that require PyPI access are skipped. To override quote currency manually set `QUOTE_OVERRIDE` before launching the installer (it will also be published to Redis when available).

Manual offline verification:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt || true
make test-offline
make smoke
```

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements/base.txt
# Optional: pip install -r requirements/backtester.txt  # pandas/numpy for backtesting utilities
cp .env.example .env  # configure credentials
flask --app app.services.api.flask_app run
```

### Docker Compose

```bash
docker compose -f infra/docker-compose.yml up -d --build
# add monitoring stack (Prometheus + Grafana)
docker compose -f infra/docker-compose.yml --profile monitoring up -d
```

Services defined in Compose:

* `api` – Flask API (exposes :8000)
* `scheduler` – background worker (metrics on :9101)
* `arbitrage` – CEX–CEX arbitrage worker (metrics on :9102)
* `redis` – Redis pub/sub broker
* `bot` – Telegram bot (optional profile `bot`)
* `prometheus`, `grafana` – monitoring profile
* `caddy` – TLS reverse proxy (profile `tls`) для публикации API за HTTPS

Create a personalised override by copying `infra/docker-compose.override.yml.example` to `infra/docker-compose.override.yml`; Compose automatically loads the override when present.

## Configuration

Edit `.env` to set environment variables:

```
FLASK_ENV=production
HOST=0.0.0.0
PORT=8000
TZ=Europe/Warsaw
EXCHANGE_MODE=mock            # mock|real – controls exchange backends
QUOTE_PREF=auto               # auto or forced quote currency (USDT/USDC/EUR/PLN)
QUOTE_OVERRIDE=
TELEGRAM_BOT_TOKEN=<token>
ADMIN_CHAT_ID=<chat_id>
BINANCE_API_KEY=<key>
BINANCE_API_SECRET=<secret>
BINANCE_USE_TESTNET=false     # production trading enabled by default
BINANCE_LIVE_TRADING=true     # disable to force mock without switching testnet
BINANCE_FORCE_MOCK=false      # emergency kill switch for spot trading
BINANCE_MIN_NOTIONAL_USD=11   # микрозаявки: автокоррекция до минимума Binance
BINANCE_FUTURES_API_KEY=<key>
BINANCE_FUTURES_API_SECRET=<secret>
BINANCE_FUTURES_TESTNET=true
REDIS_URL=redis://redis:6379/0
ENABLE_REDIS=true
SUP_RSI_BUY=30
SUP_RSI_SELL=70
SUP_DEBOUNCE_SECONDS=60
ARB_SCAN_INTERVAL=60
ARB_FEE_PCT=0.06
ARB_SLIPPAGE_PCT=0.02
ARB_QTY_MIN_USD=50
ARB_QTY_MAX_USD=250
ARB_TOP_K=5
ARB_MIN_NET_ROI_PCT=1.0
ARB_MAX_NET_ROI_PCT=100.0
ARB_MIN_NET_USD=5.0
ARB_SORT_KEY=net_roi_pct
ARB_SORT_DIR=desc
ARB_AUTO_MODE=false
EXEC_MODE=dry
ADMIN_PIN_HASH=<sha256_pin>
PORTFOLIO_RESERVE_PCT=0.15
ARB_RESERVE_PCT=0.25
CAPITAL_CAP_PCT=0.25
CAPITAL_CAP_HARD_MAX_PCT=1.0
LUNIA_DOMAIN=example.com
LUNIA_TLS_EMAIL=admin@example.com
DB_URL=sqlite:///./app/db/lunia.db
```

Live mode активен по умолчанию: `BINANCE_USE_TESTNET=false` + `BINANCE_LIVE_TRADING=true` включают реальные REST-вызовы Binance (с автоматической корректировкой микрозаявок до `BINANCE_MIN_NOTIONAL_USD`). Чтобы вернуться в безопасный режим, установите `BINANCE_FORCE_MOCK=true` или `BINANCE_LIVE_TRADING=false`. Для полноценного тестнета выставьте `BINANCE_USE_TESTNET=true` и укажите API-ключи. Аналогично для Binance Futures: `BINANCE_FUTURES_TESTNET=true` + ключи включает REST, отсутствующие ключи переводят клиента в mock.

### AI Supervisor and Spot Agent

Lunia AI анализирует индикаторы RSI/EMA и генерирует спотовые торговые сигналы. Торговый агент валидирует каждую заявку через `RiskManager` и исполняет её в mock или Binance Spot Testnet режимах.

Логи:

* `logs/supervisor.log` — сохранённые значения RSI/EMA и выбранное действие (BUY/SELL/HOLD)
* `logs/trades.jsonl` — журнал исполненных или отклонённых сделок
* `logs/risk.log` — результаты валидации рисков
* `logs/rebalancer.log` — распределение весов по ядрам
* `logs/digest.log` — часовой дайджест
* `logs/telegram.log` — ответы Telegram-бота

### Spot Strategies Pack

* **Micro trend scalper** — реагирует на микро-импульсы, использует адаптивные TP/SL.
* **Scalping breakout** — отслеживает локальные хай/лоу и подстраивает цель по волатильности.
* **Bollinger reversion / VWAP reversion** — возвращение к средним с контролем отклонения.
* **MACD crossover / EMA+RSI trend** — следование тренду с фильтрами по импульсу.
* **Liquidity snipe** — две версии (safe/aggressive) исходя из глубины стакана.
* **Volatility breakout** — ловит мощные свечи при резком расширении диапазона.
* **Grid light** — лёгкая сетка без усреднения в убыток.
* **Stat pairs** — парная торговля внутри USDT-универса.

Все стратегии регистрируются автоматически. Вес каждой можно менять в рантайме через API `/spot/strategies` или команды оператора, а журнал сигналов фиксируется в `logs/supervisor.log`.

### Capital Allocator & Sizing

* `CapitalAllocator` считает доступный `tradable_equity = equity * cap_pct * (1 - (portfolio_reserve + arbitrage_reserve))` и распределяет бюджеты по стратегиям по весам.
* `risk_size()` ограничивает размер сделки двумя критериями: `% капитала на сделку` и `RISK_PER_TRADE_PCT / stop_pct`.
* Ограничения по инструменту (`min_notional`, `lot`, `tick`, `MAX_SYMBOL_EXPOSURE_PCT`) и лимит позиций (`MAX_CONCURRENT_POS`) проверяются перед отправкой заявки.
* Метрики Prometheus: `lunia_ops_capital_cap_pct`, `lunia_tradable_equity_usd`, `lunia_spot_alloc_strategy_usd{strategy}` помогают контролировать бюджет.

### Capital CAP & Reserves

* `CAPITAL_CAP_PCT` — глобальный лимит на использование капитала, `CAPITAL_CAP_HARD_MAX_PCT` — жёсткая «крышка».
* Резервы (`PORTFOLIO_RESERVE_PCT`, `ARB_RESERVE_PCT`) удерживают часть equity под долгосрочные позиции и арбитраж.
* API `/ops/capital` и `/ops/equity` показывают рассчитанный tradable equity и бюджеты по стратегиям; POST `/ops/capital` обновляет CAP.
* Telegram: карточка «Ops/Capital» и команды `/capital`, `/capital +5`, `/capital -5`, `/capital set <pct>` управляют значением онлайном.

## Operations

* Start/stop services: `systemctl start|stop lunia_api lunia_sched lunia_bot`
* Upgrade deployment: `bash infra/scripts/upgrade.sh`

## Example API Request

```bash
curl -X POST http://localhost:8000/trade/spot/demo \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","qty":0.01}'

curl -X POST http://localhost:8000/trade/futures/demo \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSDT","side":"BUY","qty":0.001,"leverage":1}'

curl -X POST http://localhost:8000/ai/run
curl -X POST http://localhost:8000/signal \
  -H "Content-Type: application/json" \
  -d '{"symbol":"ETHUSDT","side":"SELL","qty":0.05}'

curl http://localhost:8000/portfolio
curl http://localhost:8000/balances
curl http://localhost:8000/metrics
curl http://localhost:8000/arbitrage/status
curl http://localhost:8000/arbitrage/opps?limit=5
```

The mock mode responds with a filled order and appends the event to `logs/trades.jsonl`.

## Telegram Bot Setup

1. Установите `TELEGRAM_BOT_TOKEN` и `ADMIN_CHAT_ID` в `.env`.
2. Запустите сервис: `systemctl enable --now lunia_bot` (или `make bot` локально).
3. Команды оператора: `/status`, `/help`, `/auto_on`, `/auto_off`, `/stop_all`, `/start_all`, `/trading_on`, `/trading_off`, `/arb_on`, `/arb_off`, `/sched_on`, `/sched_off`, `/scalp`, `/scalp_set <tp|sl|qty> <value>`, `/arb_interval <sec>`, `/arb_threshold <pct>`, `/arb_qty <usd>`, `/arb_filter`, `/arb_filters`, `/arb_sort`, `/arb_sortdir`, `/daily`, `/export`, `/alerts`, `/pnl [period]`, `/trades`.
4. Все ответы, ошибки и экспорт отчётов протоколируются в `logs/telegram.log`.

## Global Modes & Runtime Controls

* `AUTO_MODE` — включает автоматический режим: Supervisor генерирует сигналы, агент исполняет, арбитражный воркер активен.
* `GLOBAL_STOP` — мягкий стоп: сервисы продолжают работать, но ордера/сканы не исполняются.
* Состояние хранится в `logs/state.json`; API `/ops/state` (GET/POST) и шорткаты `/ops/auto_on`, `/ops/auto_off`, `/ops/stop_all`, `/ops/start_all` позволяют переключать флаги. Для защиты можно задать `OPS_API_TOKEN` и передавать `X-Admin-Token` в запросах.
* Телеграм-команды отражают эти же переключатели в реальном времени.

## Telegram Ops & Reports

* `/status` — подробная сводка по режимам, позициям, количеству буферизованных сигналов, активным фильтрам арбитража.
* `/auto_on`, `/auto_off`, `/stop_all`, `/start_all`, `/arb_on`, `/arb_off`, `/trading_on`, `/trading_off` — мгновенные переключатели глобальных режимов.
* `/scalp`, `/scalp_set` — просмотр и изменение параметров скальпинга (TP/SL/объём), записываются в state.json.
* `/arb_filter minroi|maxroi|minusd|top <value>`, `/arb_sort roi|usd`, `/arb_sortdir asc|desc` — интерактивная настройка фильтров и сортировки арбитража.
* `/arb_interval`, `/arb_threshold`, `/arb_qty` — настройка частоты и параметров CEX–CEX арбитража на лету.
* `/arb_stats` и кнопка «Сканировать» — последние top-N возможностей + кнопки [Сделать], [Сделать+Перевести], [Dry-Run], [Авто:Вкл/Выкл].
* `/daily`, `/alerts` — суточная сводка PnL/ROI/успешности с эмодзи-индикаторами и проверкой алертов; `/export` — немедленная выгрузка данных в S3/MinIO или локальный fallback.

### Telegram Operator Guide (Spot)

* `/spot_on`, `/spot_off` — вкл/выкл спотового блока.
* `/capital`, `/capital +5`, `/capital -5`, `/capital set <pct>` — управление CAP (в процентах от equity).
* `/spot_strategies` — текущие веса стратегий, `/spot_set weight <name> <value>` — точечное изменение веса.
* `/risk set <param> <value>` — обновление лимитов `max_positions`, `max_trade_pct`, `risk_per_trade_pct`, `max_symbol_exposure_pct`.
* `/spot_backtest <strategy> <symbol> <days>` — быстрый бэктест и текстовый отчёт в чате.
* `/alloc show`, `/alloc set portfolio <pct>`, `/alloc set arbitrage <pct>` — контроль резервов.
* `/pnl [day|week|month|year|all]` — сводка прибыли/убытка (данные берутся из SQLite `app/db/lunia.db`).
* `/trades` — последние сделки из журнала (SQLite + `logs/trades.jsonl`), `/export_csv`, `/export_json` — выгрузка отчётов.

## AI Research On-Demand

* `/ai/research/analyze_now` (API) и Telegram кнопка «🔍 Анализ сейчас» вызывают `run_research_now()`.
* Штатно используется список пар из `AI_RESEARCH_PAIRS`. Каждый запуск записывается в `logs/ai_research.log`, публикуется в Redis канал `ai.research.signal`, обновляет метрики `lunia_ai_research_runs_total`, `lunia_ai_research_confidence_avg`, `lunia_ai_research_signal_total{strategy,bias}`.
* Функция возвращает bias (LONG/SHORT/FLAT), confidence и предложенную стратегию (`scalping_breakout`, `micro_trend_scalper`, `liquidity_snipe`).

## Live Arbitrage Digest

* Арбитражный воркер читает настройки из state.json (`arb.interval`, `arb.threshold_pct`, `arb.qty_usd`).
* `/arbitrage/opps` возвращает последние возможности (top-N по spread). Telegram-бот может транслировать дайджест в канал/чат.
* Метрики Prometheus фиксируют число возможностей, исполнений, средний спред и латентность сканов.
* Быстрые кнопки Telegram: ROI 0.5/1/2/3%, сортировки ROI/$, «↻ Обновить», «Экспорт»; заголовок карточек показывает фильтры и диапазон адаптивного объёма.

## Scheduler & Digest

`lunia_sched` запускает два фоновых задания:

* Rebalancer (`logs/rebalancer.log`) — каждые 15 минут пересчитывает целевые веса активных ядер.
* Digest (`logs/digest.log`) — каждый час формирует сводку (Equity, PnL, количество сигналов) и может быть отправлен через Telegram.

Локально запустить можно командой `make sched`.

## Redis Event Bus

Redis используется как событийная шина (канал `signals`). При отсутствии Redis шина работает в in-memory режиме без сбоев. В `.env` включите `ENABLE_REDIS=true` и укажите `REDIS_URL`, чтобы задействовать pub/sub между компонентами (API → Agent, Scheduler → Agent). Docker Compose уже содержит сервис `redis`.

## CEX–CEX Arbitrage

* Конфигурация хранится в `app/core/arbitrage/config.yaml` (список пар, базовый спред, режим исполнения, шаг сканирования).
* Движок опрашивает Binance/OKX/Bybit (mock/testnet) и публикует возможности в Redis канал `arbitrage`. Runtime-фильтры задаются через state.json или REST/бота: `ARB_MIN_NET_ROI_PCT`, `ARB_MAX_NET_ROI_PCT`, `ARB_MIN_NET_USD`, `ARB_SORT_KEY`, `ARB_SORT_DIR`, `ARB_TOP_K`.
* Безопасный исполнитель (`SafeArbitrageExecutor`) работает в режимах `dry`, `simulation`, `real` (по умолчанию `EXEC_MODE=dry`), проверяет риск (`validate_arbitrage` + `validate_order`), поддерживает двойное подтверждение и PIN (`ADMIN_PIN_HASH`), ведёт лог `logs/arbitrage_exec.log` и таблицу `arbitrage_execs`.
* REST API: `POST /arbitrage/scan`, `GET /arbitrage/top`, `POST /arbitrage/exec`, `POST /arbitrage/auto_on|auto_off`, `GET/POST /arbitrage/filters`, `GET /arbitrage/status`, `GET /arbitrage/status/<exec_id>`, `POST /arbitrage/auto/tick` (все защищаются `X-OPS-TOKEN`, если задан `OPS_API_TOKEN`).
* Телеграм-карточки (см. `/arb_filters`, кнопки «Сделать», «Сделать+Перевести», «Dry-Run», «Авто:Вкл/Выкл») формируются в `app/services/arbitrage/ui.py` и используют `logs/state.json` для live-настроек.
* Adaptive Qty (`ARB_QTY_MIN_USD` / `ARB_QTY_MAX_USD`), rate limits (`ARB_RATE_LIMIT_*`), AI-weighted приоритеты, экспорт в S3/MinIO (`/export`) и алерты (`ALERTS_*`) включаются через `.env` и отражаются в метриках (`lunia_arb_qty_suggested_usd`, `lunia_arb_rate_limited_total`, `lunia_s3_exports_total`, `lunia_alerts_sent_total`).
* Метрики Prometheus: `lunia_arbitrage_opportunities_total`, `lunia_arbitrage_executed_total`, `lunia_arb_scans_total`, `lunia_arb_proposals_total`, `lunia_arb_proposals_after_filter_total`, `lunia_arb_filtered_out_total`, `lunia_arb_net_roi_pct`, `lunia_arb_net_profit_usd`, `lunia_arb_execs_total`, `lunia_arb_success_total`, `lunia_arb_fail_total`, `lunia_arb_net_profit_total_usd`, `lunia_arb_auto_execs_total`, `lunia_arbitrage_scan_latency_ms`.

### Arbitrage API Examples

```bash
curl -X POST http://localhost:8000/arbitrage/scan
curl -X POST http://localhost:8000/arbitrage/filters \
  -H "Content-Type: application/json" \
  -d '{"min_net_roi_pct":1.2,"sort_dir":"asc"}'
curl -X POST http://localhost:8000/arbitrage/exec \
  -H "Content-Type: application/json" \
  -d '{"arb_id":"<from /arbitrage/top>","mode":"dry"}'
curl http://localhost:8000/arbitrage/top?limit=5
curl http://localhost:8000/arbitrage/status
```

## Monitoring

* `/metrics` в Flask API отдаёт метрики Prometheus (`lunia_signals_total`, `lunia_orders_total`, `lunia_orders_rejected_total`, `lunia_api_latency_ms`, `lunia_pnl_total`, `lunia_arbitrage_*`).
* Scheduler экспонирует метрики на порту `9101` (через `prometheus_client.start_http_server`).
* Новые счётчики: `lunia_arb_qty_suggested_usd`, `lunia_arb_daily_pnl_usd`, `lunia_arb_success_rate`, `lunia_s3_exports_total`, `lunia_alerts_sent_total`, `lunia_ai_priority_signal_total`.
* Профиль `monitoring` Docker Compose поднимает Prometheus (`infra/monitoring/prometheus.yml`) и Grafana с дашбордом `Lunia Overview` (логин по умолчанию admin/admin), дополненным графиками Daily PnL, success ratio и гистограммой алертов/экспорта.

## Self-Healing & Backups

* `/api/v1/system/health`, `/api/v1/system/backup`, `/api/v1/system/recover`, `/api/v1/system/backups` — эндпойнты для мониторинга и восстановления (требуется `OPS_API_TOKEN`).
* `make enable-self-healing` — запускает монитор состояния (offline режим выведет отчёт в stdout).
* `make create-emergency-backup` — создаёт аварийный бэкап в `BACKUP_STORAGE_PATH` и сохраняет метаданные.

## Dashboard

* `make dashboard-up` — поднимает FastAPI/Jinja2 дашборд (порт `DASHBOARD_PORT`, по умолчанию 3000).
* `/` — обзор ядрового состояния, `/cores` — управление весами, `/backtest` — просмотр последних отчётов бэктеста.
* `/signal-health` — раздел по здоровью сигналов (точность, уверенность LLM, топ-фичи, ссылка на панели Grafana). Управляется
  флагом `FRONTEND_SIGNAL_HEALTH_ENABLED`.

## TLS Proxy (Caddy)

Для публикации API под HTTPS используйте профиль `tls`:

```bash
docker compose -f infra/docker-compose.yml --profile tls up -d
```

Caddy читает домен и email из `.env` (`LUNIA_DOMAIN`, `LUNIA_TLS_EMAIL`), автоматически получает сертификаты Let's Encrypt и проксирует запросы на сервис `api:8000`. Логи Caddy доступны через `docker compose logs caddy`.

## Offline / Proxy CI Mode

В окружениях без доступа к PyPI (офлайн или за строгим прокси) проект автоматически включает шимы для `prometheus_client`, `python-dotenv`, `requests`, `flask` и `pydantic`. Они предоставляют минимальные заглушки, чтобы тесты проходили без установки внешних пакетов. Используйте команды:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt || true
make test-offline          # прогоняет тесты без сетевых зависимостей
```

При наличии доступа к PyPI рекомендуется выполнить

```bash
pip install -r requirements/base.txt
make test                  # полный набор тестов, включая Flask API
```

Шимы для `prometheus_client`, `python-dotenv`, `requests`, `flask`, `pydantic` активируются автоматически; экспортер и алерты в офлайне сохраняют файлы в `logs/exports` и `logs/alerts.log`.

В production и на стендах устанавливайте реальные зависимости, чтобы получить полноценные метрики, загрузку `.env` и сетевые вызовы.

## Security Notes

* Секреты хранятся только в `.env` (инсталлер выставляет права `600` и подключает файл через `EnvironmentFile` в systemd).
* Systemd-юниты запускаются с `ProtectSystem=full`, `ProtectHome=yes`, `PrivateTmp=yes`, `NoNewPrivileges=yes`.
* Логи в `/opt/lunia_core/logs` ротируются через `/etc/logrotate.d/lunia` (ежедневно, хранится 14 архивов).
* Рекомендуется создать отдельного пользователя (например `lunia`) и запустить сервисы не от root, ограничив SSH по ключам и настроив брандмауэр (`ufw allow 22 80 443`, запрет остального).
* Никогда не коммитьте реальные ключи Binance/Telegram; используйте менеджер секретов или GitHub Actions Secrets для CI.

## Testing

```bash
pytest -q
```

CI (`.github/workflows/ci.yml`) запускает `ruff check .` и `pytest -q` на базовых зависимостях. Дополнительные тесты покрывают supervisor debounce, агент с учётом дневного лимита риска, Redis bus fallback, REST API (`/signal`, `/portfolio`, `/balances`), и mock Binance клиент.

## Troubleshooting

* Прокси: установите `HTTP_PROXY`/`HTTPS_PROXY` перед `make setup` или `bash install.sh`; инсталлер автоматически пробросит переменные в `pip`.
* Redis не доступен: проверьте `redis-cli -u $REDIS_URL ping` (инсталлер выведет предупреждение). При выключенном Redis система продолжает работать в offline-режиме.
* Отладка бота/планировщика в Docker: используйте `docker compose -f infra/docker-compose.yml logs -f bot` или `... scheduler`.

### Production Hardening Addendum

* **Perimeter security** – `deploy/waf/` provides ModSecurity, CrowdSec and Fail2Ban bundles guarded by the `INFRA_PROD_ENABLED` flag.
* **Secrets management** – `deploy/vault/` configures Vault with AWS KMS auto-unseal, mTLS and strict tenant policies.
* **Central logging** – `lunia_core/infra/logging/` ships a Vector + Elasticsearch/S3 stack for SOC pipelines.
* **Chaos & resilience** – `lunia_core/infra/chaos/run_chaos_scenarios.sh` exercises exchange failover, Redis read-only mode and LLM rule-based fallbacks.
* **Compliance** – automated evidence collection and access review helpers live in `app/logging/compliance.py`.
