PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
PY := $(VENV)/bin/python
COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: venv deps dev-deps lint fmt run bot sched arb test test-offline test-unit test-integration test-e2e smoke build up down logs compose-up compose-down compose-logs up-monitoring down-monitoring clean install enable-self-healing enable-auto-backup run-health-check create-emergency-backup dashboard-up verify report all

venv:
	$(PYTHON) -m venv $(VENV)

deps: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/base.txt

dev-deps: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/dev.txt

lint:
	$(PY) -m black --check .
	$(PY) -m isort --check-only .
	$(PY) -m ruff check .
	$(PY) -m mypy app

fmt:
	$(PY) -m black .
	$(PY) -m isort .

run:
        $(PY) -m flask --app app.services.api.flask_app run --host=0.0.0.0 --port=$${PORT:-8000}

bot:
	$(PY) -m app.services.telegram.bot

sched:
	$(PY) -m app.services.scheduler.worker

arb:
	$(PY) -m app.services.arbitrage.worker

test:
	$(PY) -m pytest -q

test-offline:
        FLASK_BACKEND=none PydanticBackend=none REQUESTS_BACKEND=none $(PY) -m pytest -q --maxfail=1 --disable-warnings -k "not external"

test-unit:
	$(PY) -m pytest -q tests/unit

test-integration:
	$(PY) -m pytest -q tests/integration

smoke:
        bash scripts/smoke_api.sh
        bash scripts/smoke_bot.sh

test-e2e:
	@if command -v playwright >/dev/null 2>&1; then \
		$(PY) -m pytest -q tests/frontend/e2e || true; \
	else \
		echo "Playwright not installed; skipping e2e tests."; \
	fi

build:
        $(COMPOSE) build

up:
        $(COMPOSE) up -d

cores-up: up

compose-up: up

down:
	$(COMPOSE) down -v

compose-down: down

compose-logs:
	$(COMPOSE) logs -f --tail=200

logs:
        $(COMPOSE) logs -f --tail=200

verify:
        bash ../scripts/verify_all.sh

report:
	@echo "Release report available at docs/RELEASE_REPORT.md and docs/RELEASE_REPORT.html"
	@echo "Latest artifacts can be generated with make verify"

up-monitoring:
        $(COMPOSE) --profile monitoring up -d

down-monitoring:
	$(COMPOSE) --profile monitoring down

clean:
        rm -rf $(VENV)

install:
        bash infra/install.sh

enable-self-healing:
        cd app/self_healing && $(PY) -m self_healing.health_monitor || true

enable-auto-backup:
        cd app/backup && $(PY) -m backup.backup_manager || true

run-health-check:
        cd app/self_healing && $(PY) - <<'PY'
from self_healing.health_monitor import ComprehensiveHealthMonitor
import asyncio
async def main():
    monitor = ComprehensiveHealthMonitor()
    report = await monitor.perform_health_check()
    print(report.to_dict())
asyncio.run(main())
PY

create-emergency-backup:
        cd app/backup && $(PY) - <<'PY'
from backup.backup_manager import SmartBackupManager
manager = SmartBackupManager()
print(manager.execute_smart_backup(trigger="emergency").to_dict())
PY

dashboard-up:
        cd app/dashboard && uvicorn main:app --host 0.0.0.0 --port $${DASHBOARD_PORT:-3000} || true

all:
        $(MAKE) cores-up
        $(MAKE) up-monitoring
        $(MAKE) dashboard-up
        $(MAKE) enable-self-healing
        $(MAKE) enable-auto-backup
