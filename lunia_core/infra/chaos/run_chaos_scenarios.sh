#!/usr/bin/env bash
set -euo pipefail

SCENARIO=${1:-all}
INFRA_FLAG=${INFRA_PROD_ENABLED:-false}

log() {
  printf '[chaos] %s\n' "$*"
}

if [[ "${INFRA_FLAG}" != "true" ]]; then
  log "INFRA_PROD_ENABLED is not true; running in dry-run mode"
fi

run_exchange_outage() {
  log "Simulating primary exchange outage"
  python - <<'PY'
from app.services.resilience.failover import promote_backup_exchange
promote_backup_exchange(primary="binance", fallback="okx", reason="chaos_exchange_outage")
PY
}

run_redis_failure() {
  log "Simulating Redis failure"
  python - <<'PY'
from app.services.resilience.failover import enter_read_only_mode
enter_read_only_mode("redis outage chaos test")
PY
}

run_llm_rate_limit() {
  log "Simulating LLM rate limit"
  python - <<'PY'
from app.services.resilience.failover import engage_llm_fallback
engage_llm_fallback("chaos_llm_rate_limit")
PY
}

case "$SCENARIO" in
  exchange)
    run_exchange_outage ;;
  redis)
    run_redis_failure ;;
  llm)
    run_llm_rate_limit ;;
  all)
    run_exchange_outage
    run_redis_failure
    run_llm_rate_limit ;;
  *)
    echo "Usage: $0 [exchange|redis|llm|all]" >&2
    exit 1 ;;
esac
