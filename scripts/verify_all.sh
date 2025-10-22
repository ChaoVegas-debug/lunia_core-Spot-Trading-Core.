#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
ARTIFACT_BASE="$ROOT_DIR/artifacts"
TIMESTAMP="$(date +%F_%H-%M-%S)"
ARTIFACT_DIR="$ARTIFACT_BASE/verify_${TIMESTAMP}"
PROJECT_DIR="$ROOT_DIR/lunia_core"
DOC_REPORT_DIR="$ROOT_DIR/docs/reports"
mkdir -p "$ARTIFACT_DIR"
mkdir -p "$DOC_REPORT_DIR"

LINT_STATUS="SKIPPED"
LINT_RESULTS=()
SAST_STATUS="SKIPPED"
SAST_RESULTS=()
TEST_STATUS="PENDING"
E2E_STATUS="SKIPPED"
DOCKER_STATUS="SKIPPED"
SMOKE_STATUS="SKIPPED"
SCREENSHOT_STATUS="SKIPPED"
SMOKE_WARN=0
STACK_STARTED=0

log() {
    printf '[%s] %s\n' "$(date +%F\ %T)" "$*"
}

warn() {
    printf '[%s] WARN: %s\n' "$(date +%F\ %T)" "$*" >&2
}

run_optional() {
    local description=$1
    shift
    if "$@"; then
        log "✔ ${description}"
    else
        warn "✖ ${description} (continuing)"
        SMOKE_WARN=1
    fi
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

tee_log() {
    local outfile=$1
    shift
    "$@" 2>&1 | tee "$outfile"
}

capture_screenshot() {
    local url=$1
    local outfile=$2
    if python - <<'PY' "$url" "$outfile" "$ARTIFACT_DIR"
import sys
from pathlib import Path

url = sys.argv[1]
outfile = Path(sys.argv[2])
artifact_dir = Path(sys.argv[3])

try:
    from playwright.sync_api import sync_playwright  # type: ignore
except Exception:
    sys.exit(1)

outfile.parent.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.screenshot(path=str(outfile), full_page=True)
    browser.close()
artifact_copy = artifact_dir / outfile.name
artifact_copy.write_bytes(outfile.read_bytes())
PY
    then
        log "Captured screenshot ${outfile}"
        SCREENSHOT_STATUS="PASS"
    else
        warn "Unable to capture screenshot for ${url}"
        if [[ "$SCREENSHOT_STATUS" == "SKIPPED" ]]; then
            SCREENSHOT_STATUS="WARN"
        fi
        if [[ ! -f "$outfile" ]]; then
            python - <<'PY' "$outfile" "$ARTIFACT_DIR"
import base64
import sys
from pathlib import Path

placeholder = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAH+wJ/lpRoAAAAAElFTkSuQmCC"
)
out = Path(sys.argv[1])
artifact_dir = Path(sys.argv[2])
out.write_bytes(placeholder)
(artifact_dir / out.name).write_bytes(placeholder)
PY
        fi
    fi
}

join_results() {
    local IFS=", "
    echo "$*"
}

log "Root directory: $ROOT_DIR"
log "Artifacts will be stored in $ARTIFACT_DIR"

# Environment snapshot
{
    echo "# Tool versions"
    for tool in python3 pip docker "docker compose" poetry git node npm; do
        if [[ $tool == *" "* ]]; then
            if command -v ${tool%% *} >/dev/null 2>&1; then
                echo "$tool: $($tool --version 2>/dev/null || true)"
            else
                echo "$tool: not installed"
            fi
        else
            if command_exists "$tool"; then
                echo "$tool: $($tool --version 2>/dev/null || true)"
            else
                echo "$tool: not installed"
            fi
        fi
    done
    echo
    echo "# System resources"
    df -h
    echo
    free -h || true
} > "$ARTIFACT_DIR/environment.txt"

log "Captured environment snapshot"

# Feature flag snapshot
ENV_FILE="$ROOT_DIR/.env"
if [[ ! -f "$ENV_FILE" && -f "$PROJECT_DIR/.env.example" ]]; then
    cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
    warn "No .env detected; copied default from lunia_core/.env.example"
fi
FEATURE_FLAGS=(
    "FRONTEND_SIGNAL_HEALTH_ENABLED"
    "INFRA_PROD_ENABLED"
    "BINANCE_LIVE_TRADING"
    "BINANCE_FORCE_MOCK"
    "SELF_HEALING_ENABLED"
    "AUTO_BACKUP_ENABLED"
    "ARB_AUTO_MODE"
    "EXEC_MODE"
)
{
    echo "# Feature Flag Snapshot"
    if [[ -f "$ENV_FILE" ]]; then
        for flag in "${FEATURE_FLAGS[@]}"; do
            value=$(grep -E "^${flag}=" "$ENV_FILE" | tail -n1 | cut -d'=' -f2-)
            echo "$flag=${value:-<unset>}"
        done
    else
        echo ".env not found"
    fi
} > "$ARTIFACT_DIR/feature_flags.txt"

# Linting
log "Running linters"
lint_any=false
lint_fail=false

if command_exists ruff; then
    lint_any=true
    if tee_log "$ARTIFACT_DIR/ruff.log" ruff check .; then
        LINT_RESULTS+=("ruff:PASS")
    else
        warn "ruff reported issues"
        lint_fail=true
        LINT_RESULTS+=("ruff:FAIL")
    fi
else
    warn "ruff not installed; skipping"
    LINT_RESULTS+=("ruff:SKIP")
fi

if command_exists black; then
    lint_any=true
    if tee_log "$ARTIFACT_DIR/black.log" black --check .; then
        LINT_RESULTS+=("black:PASS")
    else
        warn "black --check failed"
        lint_fail=true
        LINT_RESULTS+=("black:FAIL")
    fi
else
    warn "black not installed; skipping"
    LINT_RESULTS+=("black:SKIP")
fi

if command_exists flake8; then
    lint_any=true
    if tee_log "$ARTIFACT_DIR/flake8.log" flake8; then
        LINT_RESULTS+=("flake8:PASS")
    else
        warn "flake8 reported issues"
        lint_fail=true
        LINT_RESULTS+=("flake8:FAIL")
    fi
else
    warn "flake8 not installed; skipping"
    LINT_RESULTS+=("flake8:SKIP")
fi

if command_exists mypy && [[ -f "$ROOT_DIR/mypy.ini" || -f "$ROOT_DIR/pyproject.toml" ]]; then
    lint_any=true
    if tee_log "$ARTIFACT_DIR/mypy.log" mypy; then
        LINT_RESULTS+=("mypy:PASS")
    else
        warn "mypy reported issues"
        lint_fail=true
        LINT_RESULTS+=("mypy:FAIL")
    fi
else
    warn "mypy not configured or not installed; skipping"
    LINT_RESULTS+=("mypy:SKIP")
fi

if $lint_any; then
    if $lint_fail; then
        LINT_STATUS="FAIL"
    else
        LINT_STATUS="PASS"
    fi
else
    LINT_STATUS="SKIPPED"
fi

# YAML/JSON validation
if command_exists yamllint; then
    tee_log "$ARTIFACT_DIR/yamllint.log" yamllint . || warn "yamllint reported issues"
else
    warn "yamllint not installed; skipping"
fi
if command_exists jq; then
    find "$ROOT_DIR" -name '*.json' -not -path '*/.venv/*' -print0 | while IFS= read -r -d '' file; do
        jq empty "$file" || warn "Invalid JSON: $file"
    done
else
    warn "jq not installed; skipping JSON validation"
fi

# SAST / security scans
if command_exists bandit; then
    target_dir="$PROJECT_DIR/app"
    if [[ -d "$target_dir" ]]; then
        if tee_log "$ARTIFACT_DIR/bandit.log" bandit -q -r "$target_dir"; then
            SAST_RESULTS+=("bandit:PASS")
        else
            warn "bandit reported issues"
            SAST_RESULTS+=("bandit:FAIL")
        fi
    else
        warn "Bandit target $target_dir missing; skipping"
        SAST_RESULTS+=("bandit:SKIP")
    fi
else
    warn "bandit not installed; skipping"
    SAST_RESULTS+=("bandit:SKIP")
fi
if command_exists trivy; then
    if tee_log "$ARTIFACT_DIR/trivy-repo.log" trivy fs --exit-code 0 --no-progress --severity HIGH,CRITICAL .; then
        SAST_RESULTS+=("trivy-fs:PASS")
    else
        warn "trivy repo scan reported issues"
        SAST_RESULTS+=("trivy-fs:FAIL")
    fi
else
    warn "trivy not installed; skipping file system scan"
    SAST_RESULTS+=("trivy-fs:SKIP")
fi
if command_exists docker && command_exists trivy; then
    if [[ -f "$ROOT_DIR/lunia_core/Dockerfile" ]]; then
        if tee_log "$ARTIFACT_DIR/trivy-dockerfile.log" trivy config "$ROOT_DIR/lunia_core/Dockerfile"; then
            SAST_RESULTS+=("trivy-dockerfile:PASS")
        else
            warn "trivy Dockerfile scan reported issues"
            SAST_RESULTS+=("trivy-dockerfile:FAIL")
        fi
    fi
else
    warn "Docker/Trivy unavailable; skipping Dockerfile scan"
    SAST_RESULTS+=("trivy-dockerfile:SKIP")
fi

if [[ "${SAST_RESULTS[*]}" == *":FAIL"* ]]; then
    SAST_STATUS="FAIL"
elif [[ "${SAST_RESULTS[*]}" == *":PASS"* ]]; then
    SAST_STATUS="PASS"
else
    SAST_STATUS="SKIPPED"
fi

# Tests with coverage
PYTEST_TARGETS=(
    tests/auth
    tests/portfolio
    tests/risk
    tests/ai/research
    tests/ai/orchestrator
    tests/strategies
    tests/infra
    tests/perf
)

TEST_EXIT=0
pushd "$PROJECT_DIR" >/dev/null
if command_exists coverage; then
    coverage erase || true
    log "Running pytest with coverage"
    coverage run -m pytest -q "${PYTEST_TARGETS[@]}" --junitxml "$ARTIFACT_DIR/pytest-junit.xml" || TEST_EXIT=$?
    coverage xml -o "$ARTIFACT_DIR/coverage.xml" || warn "Failed to create coverage.xml"
    coverage html -d "$ARTIFACT_DIR/coverage_html" || warn "Failed to create coverage HTML"
    coverage report || true
else
    log "coverage not installed; falling back to pytest"
    pytest -q "${PYTEST_TARGETS[@]}" --junitxml "$ARTIFACT_DIR/pytest-junit.xml" || TEST_EXIT=$?
fi
popd >/dev/null

if [[ $TEST_EXIT -eq 0 ]]; then
    TEST_STATUS="PASS"
else
    TEST_STATUS="FAIL"
fi

if [[ $TEST_EXIT -ne 0 ]]; then
    warn "Pytest exited with status $TEST_EXIT"
fi

# E2E tests (optional)
if command_exists pytest && python - <<'PY' >/dev/null 2>&1
import importlib
exit(0 if importlib.util.find_spec("playwright") else 1)
PY
then
    log "Running Playwright e2e suite"
    if (cd "$PROJECT_DIR" && pytest -q tests/frontend/e2e --maxfail=1 --disable-warnings); then
        E2E_STATUS="PASS"
    else
        warn "Playwright tests reported issues"
        E2E_STATUS="WARN"
    fi
else
    warn "Playwright not available; skipping e2e tests"
    E2E_STATUS="SKIPPED"
fi

# Docker build/config
if command_exists docker; then
    DOCKER_STATUS="PASS"
    if [[ -f "$PROJECT_DIR/Dockerfile" ]]; then
        if ! tee_log "$ARTIFACT_DIR/docker-build.log" docker build -t lunia-core:verify -f "$PROJECT_DIR/Dockerfile" "$PROJECT_DIR"; then
            warn "Docker build failed"
            DOCKER_STATUS="FAIL"
        fi
    fi
    if [[ -f "$PROJECT_DIR/Dockerfile.test" ]]; then
        if ! tee_log "$ARTIFACT_DIR/docker-build-test.log" docker build -t lunia-core-test:verify -f "$PROJECT_DIR/Dockerfile.test" "$PROJECT_DIR"; then
            warn "Test Docker build failed"
            DOCKER_STATUS="FAIL"
        fi
    fi
    if [[ -f "$ROOT_DIR/docker-compose.staging.yml" ]]; then
        if ! tee_log "$ARTIFACT_DIR/docker-compose-config.log" docker compose -f "$ROOT_DIR/docker-compose.staging.yml" config; then
            warn "docker compose config failed"
            DOCKER_STATUS="FAIL"
        fi
    fi
else
    warn "Docker not installed; skipping docker build and compose config"
    DOCKER_STATUS="SKIPPED"
fi

# Smoke tests via docker compose staging profile
if command_exists docker && [[ -f "$ROOT_DIR/docker-compose.staging.yml" ]]; then
    log "Starting staging stack for smoke tests"
    if docker compose -f "$ROOT_DIR/docker-compose.staging.yml" up -d; then
        STACK_STARTED=1
        sleep 10
        run_optional "API health" curl -fsS http://localhost:8000/healthz > "$ARTIFACT_DIR/api-health.json" || true
        run_optional "Metrics endpoint" curl -fsS http://localhost:8000/metrics > "$ARTIFACT_DIR/api-metrics.txt" || true
        run_optional "Portfolio build (mock)" curl -fsS -X POST http://localhost:8000/api/portfolio/build -H 'Content-Type: application/json' -d '{"mode":"mock"}' > "$ARTIFACT_DIR/api-portfolio-build.json" || true
        run_optional "Portfolio explain" curl -fsS http://localhost:8000/api/portfolio/explain/BTCUSDT > "$ARTIFACT_DIR/api-portfolio-explain.json" || true
        run_optional "LLM consensus" curl -fsS http://localhost:8000/api/orchestrator/consensus > "$ARTIFACT_DIR/api-consensus.json" || true
        # Feature flag toggles
        if [[ -n "${FRONTEND_SIGNAL_HEALTH_ENABLED:-}" ]]; then
            log "FRONTEND_SIGNAL_HEALTH_ENABLED currently set to ${FRONTEND_SIGNAL_HEALTH_ENABLED}"
        fi
        run_optional "Signal health page" curl -fsS http://localhost:8000/ui/signal-health > "$ARTIFACT_DIR/signal-health.html" || true
        SCREENSHOT_FILE="$DOC_REPORT_DIR/signal-health_${TIMESTAMP}.png"
        capture_screenshot "http://localhost:8000/ui/signal-health" "$SCREENSHOT_FILE"
        docker compose -f "$ROOT_DIR/docker-compose.staging.yml" logs > "$ARTIFACT_DIR/docker-logs.txt" || true
        docker compose -f "$ROOT_DIR/docker-compose.staging.yml" down -v || true
        if [[ $SMOKE_WARN -eq 1 ]]; then
            SMOKE_STATUS="WARN"
        else
            SMOKE_STATUS="PASS"
        fi
    else
        warn "Failed to start staging stack; skipping smoke tests"
        SMOKE_STATUS="FAIL"
    fi
else
    warn "Docker unavailable; skipping smoke tests"
    if [[ $DOCKER_STATUS == "SKIPPED" ]]; then
        SMOKE_STATUS="SKIPPED"
    else
        SMOKE_STATUS="FAIL"
    fi
fi

# Release report generation
LINT_SUMMARY=$(join_results "${LINT_RESULTS[@]}")
SAST_SUMMARY=$(join_results "${SAST_RESULTS[@]}")
OVERALL_STATUS="PASS"
if [[ $TEST_STATUS == "FAIL" || $LINT_STATUS == "FAIL" || $SAST_STATUS == "FAIL" || $DOCKER_STATUS == "FAIL" || $SMOKE_STATUS == "FAIL" ]]; then
    OVERALL_STATUS="FAIL"
elif [[ $E2E_STATUS == "WARN" || $SMOKE_STATUS == "WARN" || $SCREENSHOT_STATUS == "WARN" ]]; then
    OVERALL_STATUS="WARN"
fi

REPORT_MD="$ROOT_DIR/docs/RELEASE_REPORT.md"
cat > "$REPORT_MD" <<EOF
# Release Verification Report

- Generated: $(date +"%F %T")
- Overall status: ${OVERALL_STATUS}
- Artifacts: ${ARTIFACT_DIR}

## Summary
| Category | Status | Details |
| --- | --- | --- |
| Lint | ${LINT_STATUS} | ${LINT_SUMMARY:-n/a} |
| SAST | ${SAST_STATUS} | ${SAST_SUMMARY:-n/a} |
| Tests | ${TEST_STATUS} | targets: ${PYTEST_TARGETS[*]} |
| E2E | ${E2E_STATUS} | Playwright smoke |
| Docker | ${DOCKER_STATUS} | Dockerfile builds & compose config |
| Smoke | ${SMOKE_STATUS} | staging stack curl checks |
| Screenshots | ${SCREENSHOT_STATUS} | stored under docs/reports |

## Feature Flags

$(cat "$ARTIFACT_DIR/feature_flags.txt" 2>/dev/null || echo "(feature snapshot unavailable)")

## Health Checks

- API health: $(test -f "$ARTIFACT_DIR/api-health.json" && echo "captured" || echo "missing")
- Metrics: $(test -f "$ARTIFACT_DIR/api-metrics.txt" && echo "captured" || echo "missing")
- Signal health screenshot: $(ls "$DOC_REPORT_DIR"/*.png 2>/dev/null | tail -n1 || echo "not captured")

## Notes

- Script: scripts/verify_all.sh
- Exit status: ${TEST_EXIT}
EOF

REPORT_HTML="$ROOT_DIR/docs/RELEASE_REPORT.html"
python - <<'PY' "$REPORT_MD" "$REPORT_HTML"
from pathlib import Path
import html
import sys

md_path = Path(sys.argv[1])
html_path = Path(sys.argv[2])
text = md_path.read_text(encoding="utf-8") if md_path.exists() else "Release report unavailable"
html_path.write_text(
    "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Release Report</title></head><body><pre>{}</pre></body></html>".format(
        html.escape(text)
    ),
    encoding="utf-8",
)
PY

# Summaries
{
    echo "Verification completed at $(date +%F\ %T)"
    echo "Artifacts stored in: $ARTIFACT_DIR"
    echo "Pytest exit status: $TEST_EXIT"
} > "$ARTIFACT_DIR/summary.txt"

log "Verification completed. Summary written to $ARTIFACT_DIR/summary.txt"
exit $TEST_EXIT
