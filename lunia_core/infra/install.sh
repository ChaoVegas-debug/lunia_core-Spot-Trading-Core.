#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="/opt/lunia_core"
LOG_FILE="/var/log/lunia_install.log"
APT_UPDATED=0
MODE="OFFLINE"
DEFAULT_REDIS_URL="redis://redis:6379/0"
: "${REDIS_URL:=${DEFAULT_REDIS_URL}}"

mkdir -p "$(dirname "${LOG_FILE}")"
: > "${LOG_FILE}"
chmod 644 "${LOG_FILE}"

log() {
  echo "$(date -Iseconds) $*" | tee -a "${LOG_FILE}"
}

trap 'log "Installation failed on line ${LINENO}"' ERR

if [[ $(id -u) -ne 0 ]]; then
  log "Please run infra/install.sh with root privileges"
  exit 1
fi

check_connectivity() {
  if ping -c1 -W1 1.1.1.1 >/dev/null 2>&1; then
    if DEBIAN_FRONTEND=noninteractive apt-get update >/dev/null 2>&1; then
      MODE="ONLINE"
      APT_UPDATED=1
    else
      log "apt-get update failed – switching to OFFLINE mode"
    fi
  else
    log "No network connectivity detected – OFFLINE mode"
  fi
}

ensure_packages() {
  if [[ "${MODE}" != "ONLINE" ]]; then
    log "Skipping apt packages installation in OFFLINE mode"
    return
  fi

  local packages=(
    git curl ca-certificates make gcc python3 python3-venv python3-pip \
    docker.io docker-compose-plugin jq
  )

  log "Installing system packages: ${packages[*]}"
  if [[ ${APT_UPDATED} -eq 0 ]]; then
    DEBIAN_FRONTEND=noninteractive apt-get update | tee -a "${LOG_FILE}"
  fi
  DEBIAN_FRONTEND=noninteractive apt-get install -y "${packages[@]}" | tee -a "${LOG_FILE}"
}

copy_repo() {
  log "Syncing repository to ${TARGET_DIR}"
  mkdir -p "${TARGET_DIR}"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude ".git" "${REPO_DIR}/" "${TARGET_DIR}/"
  else
    find "${TARGET_DIR}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    cp -a "${REPO_DIR}/"* "${TARGET_DIR}/"
  fi
}

stage_systemd_units() {
  log "Staging systemd unit files"
  install -m 644 "${TARGET_DIR}/infra/systemd/lunia_api.service" /etc/systemd/system/lunia_api.service
  install -m 644 "${TARGET_DIR}/infra/systemd/lunia_bot.service" /etc/systemd/system/lunia_bot.service
  install -m 644 "${TARGET_DIR}/infra/systemd/lunia_sched.service" /etc/systemd/system/lunia_sched.service
  install -m 644 "${TARGET_DIR}/infra/systemd/lunia_arb.service" /etc/systemd/system/lunia_arb.service
  if command -v systemctl >/dev/null 2>&1; then
    systemctl daemon-reload
  fi
}

create_venv() {
  log "Creating virtual environment at ${TARGET_DIR}/.venv"
  python3 -m venv "${TARGET_DIR}/.venv"
}

install_python_deps() {
  if [[ "${MODE}" != "ONLINE" ]]; then
    log "OFFLINE mode: skipping pip installation"
    return
  fi

  log "Installing Python dependencies"
  (cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/pip" install --upgrade pip | tee -a "${LOG_FILE}")
  (cd "${TARGET_DIR}" && "${TARGET_DIR}/.venv/bin/pip" install -r requirements/dev.txt | tee -a "${LOG_FILE}")
}

ensure_env_file() {
  cd "${TARGET_DIR}"
  if [[ ! -f .env ]]; then
    cp .env.example .env
    log "Created .env from template"
  fi
  chmod 600 .env || true
}

update_env_var() {
  local key="$1"
  local value="$2"
  python3 - "$key" "$value" <<'PY'
import sys
from pathlib import Path

key, value = sys.argv[1], sys.argv[2]
env_path = Path('.env')
lines = []
found = False
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if line.startswith(f"{key}="):
            lines.append(f"{key}={value}")
            found = True
        else:
            lines.append(line)
if not found:
    lines.append(f"{key}={value}")
text = "\n".join(lines).rstrip() + "\n"
env_path.write_text(text)
PY
}

apply_env_overrides() {
  cd "${TARGET_DIR}"
  local vars=(TELEGRAM_BOT_TOKEN REDIS_URL BINANCE_API_KEY BINANCE_API_SECRET)
  for var in "${vars[@]}"; do
    if [[ -n "${!var:-}" ]]; then
      update_env_var "${var}" "${!var}"
      log "Applied ${var} from environment"
    fi
  done

  if [[ -n "${QUOTE_OVERRIDE:-}" ]]; then
    update_env_var "QUOTE_OVERRIDE" "${QUOTE_OVERRIDE}"
    log "Registered QUOTE_OVERRIDE=${QUOTE_OVERRIDE} in .env"
    publish_quote_override || log "QUOTE_OVERRIDE publish skipped (Redis unavailable)"
  fi
}

publish_quote_override() {
  local python_bin="${TARGET_DIR}/.venv/bin/python"
  if [[ ! -x "${python_bin}" ]]; then
    python_bin="$(command -v python3)"
  fi
  PYTHONPATH="${TARGET_DIR}" REDIS_URL="${REDIS_URL:-redis://redis:6379/0}" \
    "${python_bin}" - <<'PY'
import os

quote = os.getenv("QUOTE_OVERRIDE")
if not quote:
    raise SystemExit(0)

try:
    from app.core.bus.redis_bus import publish
    publish("system.events", {"type": "quote_override", "value": quote})
    print(f"Published quote override {quote}")
except Exception as exc:  # pragma: no cover
    raise SystemExit(f"Failed to publish quote override: {exc}")
PY
}

wait_for_api() {
  local retries=12
  local url="http://127.0.0.1:8000/healthz"
  if ! command -v curl >/dev/null 2>&1; then
    log "curl not available – skipping API health probe"
    return 0
  fi
  log "Waiting for API health at ${url}"
  until curl -fsS "${url}" >/dev/null 2>&1; do
    ((retries--)) || {
      log "API health check failed"
      return 1
    }
    sleep 5
  done
  log "API health check OK"
}

run_python_healthcheck() {
  local module="$1"
  local python_bin="${TARGET_DIR}/.venv/bin/python"
  if [[ ! -x "${python_bin}" ]]; then
    python_bin="$(command -v python3)"
  fi
  log "Running ${module} --healthcheck --dry-run"
  PYTHONPATH="${TARGET_DIR}" "${python_bin}" -m "${module}" --healthcheck --dry-run | tee -a "${LOG_FILE}"
}

bring_up_docker() {
  if [[ "${MODE}" != "ONLINE" ]]; then
    log "Skipping Docker deployment in OFFLINE mode"
    return 1
  fi
  if ! command -v docker >/dev/null 2>&1; then
    log "Docker not available; falling back to local make commands"
    return 1
  fi

  log "Building and starting Docker stack"
  (cd "${TARGET_DIR}" && docker compose -f infra/docker-compose.yml -f infra/docker-compose.override.yml up -d --build)
  (cd "${TARGET_DIR}" && docker compose ps)
  (cd "${TARGET_DIR}" && docker compose logs --tail=100 api bot scheduler arbitrage || true)
  return 0
}

run_make_checks() {
  cd "${TARGET_DIR}"
  if ! command -v make >/dev/null 2>&1; then
    log "make not available; skipping local make checks"
    return
  fi
  if [[ "${MODE}" == "ONLINE" ]]; then
    log "Running make lint"
    if [[ -x .venv/bin/black ]]; then
      make lint | tee -a "${LOG_FILE}"
    else
      log "Lint dependencies missing; skipping make lint"
    fi
  fi

  log "Running make test-offline"
  if [[ -x .venv/bin/pytest ]]; then
    FLASK_BACKEND=none PydanticBackend=none REQUESTS_BACKEND=none make test-offline | tee -a "${LOG_FILE}"
  else
    log "pytest not available; skipping test-offline"
  fi

  if command -v curl >/dev/null 2>&1; then
    log "Running make smoke"
    make smoke | tee -a "${LOG_FILE}"
  else
    log "curl not available; skipping make smoke"
  fi
}

main() {
  log "Starting Lunia Core installation"
  check_connectivity
  log "Mode detected: ${MODE}"
  ensure_packages
  copy_repo
  stage_systemd_units
  create_venv
  install_python_deps
  ensure_env_file
  apply_env_overrides

  if bring_up_docker; then
    wait_for_api
  else
    run_make_checks
    wait_for_api || log "API health check skipped (service not running)"
  fi

  run_python_healthcheck "app.services.telegram.bot"
  run_python_healthcheck "app.services.scheduler.worker"
  run_python_healthcheck "app.services.arbitrage.worker"

  log "Installation complete. Review ${LOG_FILE} for details."
}

main "$@"
