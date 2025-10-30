#!/usr/bin/env bash
set -euo pipefail

say(){ echo -e "$@"; }

# ensure we are inside a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  say "❌ Not a git repo"; exit 1
fi

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

git config --global --add safe.directory "$ROOT" || true

git fetch --all --prune

# discover latest Phase 2A branch
WORK_BRANCH="$(git for-each-ref --format='%(refname:short) %(committerdate:iso8601)' refs/remotes/origin/codex/add-infrastructure-and-health-integration-* \
  | sort -k2,2r | head -n1 | awk '{print $1}' | sed 's#^origin/##')"
if [[ -z "${WORK_BRANCH:-}" ]]; then
  say "⛔ Phase-2A branch not found"; exit 2
fi
say "→ Using green branch: $WORK_BRANCH"

# checkout local tracking branch
if ! git show-ref --verify --quiet "refs/heads/$WORK_BRANCH"; then
  git switch -c "$WORK_BRANCH" --track "origin/$WORK_BRANCH"
else
  git switch "$WORK_BRANCH"
  git pull --rebase origin "$WORK_BRANCH"
fi

# backup branch
BK="backup/${WORK_BRANCH//\//-}-$(date +%Y%m%d-%H%M%S)"
git branch -f "$BK" HEAD || true

say "→ Merge origin/main into $WORK_BRANCH with -X ours"
set +e
git merge -m "merge(origin/main → $WORK_BRANCH): keep Phase-2A baseline as source of truth" -X ours origin/main
merge_rc=$?
set -e

# known files to resolve with ours
read -r -d '' OURS_LAT <<'FILES'
.env.example.3a
.github/workflows/verify.yml
infra/docker-compose.yml
lunia_core/app/api/routes_admin.py
lunia_core/app/core/guard/__init__.py
lunia_core/app/core/scheduler/__init__.py
lunia_core/app/main.py
lunia_core/app/services/api/schemas.py
lunia_core/app/services/telegram/__init__.py
lunia_core/main.py
lunia_core/requirements/all.txt
lunia_core/requirements/base.txt
lunia_core/requirements/base_minimal.txt
lunia_core/requirements/telegram.txt
lunia_core/runtime/__init__.py
lunia_core/runtime/guard.py
lunia_core/runtime/scheduler.py
requirements.txt
scripts/__init__.py
scripts/ensure-no-telegram.sh
scripts/health/__init__.py
scripts/health/all_checks.py
scripts/health/rabbitmq_check.py
scripts/health/redis_check.py
scripts/preflight.py
scripts/recover_main_phase2a.sh
scripts/resolve_phase2a_conflicts.sh
scripts/start_runtime.sh
tests/test_api_schemas.py
tests/test_health_scripts.py
tests/test_runtime_guard.py
tests/test_telegram_optional.py
FILES

if [[ $merge_rc -ne 0 ]]; then
  say "→ Resolving known Phase-2A paths in favor of ours"
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if git ls-files --unmerged -- "$path" >/dev/null 2>&1; then
      git checkout --ours -- "$path" || true
      git add "$path" || true
    fi
  done <<<"$OURS_LAT"
fi

if git ls-files --unmerged | grep -q .; then
  say "⛔ Remaining conflicts:";
  git ls-files --unmerged | cut -f2 | sort -u
  exit 3
fi

if ! git diff --cached --quiet; then
  git commit -m "fix(Phase-2A): resolve conflicts in favor of green branch"
fi

chmod +x scripts/ensure-no-telegram.sh 2>/dev/null || true
chmod +x scripts/recover_main_phase2a.sh 2>/dev/null || true
chmod +x scripts/start_runtime.sh 2>/dev/null || true
chmod +x scripts/resolve_phase2a_conflicts.sh 2>/dev/null || true

say "→ preflight";           python scripts/preflight.py            || true
say "→ guard(no-telegram)"; bash   scripts/ensure-no-telegram.sh    || true
say "→ health OFFLINE_CI=1"; OFFLINE_CI=1 python scripts/health/all_checks.py || true
say "→ pytest smoke";       pytest -q -k "telegram_optional or health_scripts or runtime_guard or api_schemas" || true

say "→ push $WORK_BRANCH"
set +e
git push origin "$WORK_BRANCH"
code=$?
set -e

if [[ $code -eq 0 ]]; then
  say "🎉 PR обновлён."
  exit 0
fi

BUNDLE="phase2a_${WORK_BRANCH//\//-}.bundle"
say "⚠️ Push blocked (code=$code). Creating bundle: $BUNDLE"
git bundle create "$BUNDLE" "$WORK_BRANCH"
say "📦 Bundle ready: $BUNDLE"
say "To push manually:\n  git clone <REPO_URL> repo\n  cd repo && git pull ../$BUNDLE $WORK_BRANCH && git push origin $WORK_BRANCH\n"
