# Test & Verification Matrix

The Lunia core stack ships with three layers of automated checks. All tests run in mock/offline mode and avoid real network calls to Binance or Telegram.

## Unit tests

```
make test-unit
```

Focus: pure functions and utilities (e.g., quote detector symbol helpers, capital allocator maths).

## Integration tests

```
make test-integration
```

Focus: Flask API blueprints, Telegram bot bootstrap (`create_app(dry_run=True)`), Redis pub/sub (fakeredis), and mock exchange flows. Each test uses pytest fixtures defined in `tests/conftest.py` to provide fake Redis and temporary SQLite state.

## Full suite

```
make test
```

Runs the entire pytest suite (unit + integration). Flask dependent tests are marked with `@pytest.mark.requires_flask` and auto-skip in offline/proxy environments.

## Offline fallback

```
make test-offline
```

Executes pytest with `--maxfail=1 --disable-warnings -k "not external"` so the run succeeds even without `fakeredis`, `flask`, `pydantic`, `requests` или `prometheus_client`. Шимы `app.compat.*` автоматически подменяют недостающие зависимости, а Redis доступ осуществляется через in-memory реализацию из `tests/conftest.py`.

Quick offline bootstrapping from scratch:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt || true  # optional when PyPI is unavailable
make test-offline
```

## Smoke tests

```
make smoke
```

* `scripts/smoke_api.sh` – checks `/healthz` and `/metrics` of a running API container.
* `scripts/smoke_bot.sh` – initialises the Telegram bot in dry-run mode and confirms handler registration.

## Performance harness

```
pytest tests/perf -q
python tools/load_test.py --users 120 --orders 550 --backtests 12
```

The pytest suite validates that the synthetic load generator works even in offline CI. The CLI command produces a report at
`reports/load_test_summary.json` and emulates the go-live targets (100+ пользователей, 10+ бэктестов, 500+ заявок в минуту).

### Self-healing / backup / dashboard quick checks

* `make enable-self-healing` – runs the health monitor once (outputs JSON in offline mode).
* `make create-emergency-backup` – writes a backup archive and prints metadata.
* `make dashboard-up` – starts the optional FastAPI dashboard (defaults to port 3000).

## Linting and formatting

```
make lint
make fmt
```

`make lint` runs ruff, black (check), isort (check), and mypy. `make fmt` applies black+isort formatting.

## Docker workflow

```
make build
make up
make smoke
make logs   # Ctrl+C to stop
make down
```

Builds container images, starts the stack (api, scheduler, arbitrage, redis), runs smoke checks, tails logs, and tears everything down. Monitoring profile is available via `make up-monitoring`.

## Continuous Integration

GitHub Actions workflow `.github/workflows/ci.yml` performs the following on every push/PR (with `EXCHANGE_MODE=mock`, `QUOTE_PREF=auto`):

1. Install dependencies from `requirements/dev.txt`.
2. Run `make lint`.
3. Run `make test` followed by `make test-offline` to verify both modes.
4. Bring up the docker stack via `make build`/`make up` and execute `make smoke`.
5. Always collect compose logs and shut down via `make down` on completion.
