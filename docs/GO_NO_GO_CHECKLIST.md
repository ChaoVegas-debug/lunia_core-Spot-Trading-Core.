# Go / No-Go Checklist

Use this checklist before promoting a build to production.

## Release Metadata
- [ ] Version tag:
- [ ] Commit SHA:
- [ ] Release date:

## Platform Health
- [ ] `/healthz` returns 200
- [ ] `/metrics` exposes core_pnl, risk_exposure, request_duration metrics
- [ ] `scripts/verify_all.sh` executed and artifacts archived
- [ ] `docs/RELEASE_REPORT.md` reviewed and signed

## Test Coverage
- [ ] Unit tests (pytest core suites) ✅
- [ ] Integration tests ✅
- [ ] Performance tests (`pytest tests/perf`) ✅ P99 < 200 ms
- [ ] Playwright e2e ✅ (or documented skip if environment lacks Chromium)
- [ ] Load test (`python tools/load_test.py --users 100 --orders 500`) ✅
- [ ] Coverage ≥ 70 % (warn if lower, investigate modules)

## Trading KPIs
- [ ] Sharpe ratio > 1.3 (rolling 3 months)
- [ ] Hit rate > 55 %
- [ ] Explainability score ≥ 8/10
- [ ] No unexplained drawdowns > 5 %

## Security & Compliance
- [ ] OWASP ZAP / AppSec scan A or better
- [ ] Trivy/Bandit results reviewed (no critical CVEs)
- [ ] WAF/IDS enabled (ModSecurity + CrowdSec)
- [ ] Vault/KMS configured (INFRA_PROD_ENABLED=true in staging)
- [ ] Audit evidence exported (weekly + quarterly)
- [ ] Third-party pentest report signed off

## Infrastructure
- [ ] Docker images signed (cosign) & SBOM published (Syft)
- [ ] Falco runtime protection enabled
- [ ] Encrypted swap active on hosts
- [ ] Systemd services enabled: lunia_core, lunia_api, lunia_sched, lunia_arb, lunia_bot
- [ ] Backups verified (restore test completed)

## Feature Flags & Config
- [ ] `BINANCE_LIVE_TRADING=true`
- [ ] `BINANCE_FORCE_MOCK=false`
- [ ] `INFRA_PROD_ENABLED=true`
- [ ] `FRONTEND_SIGNAL_HEALTH_ENABLED=true`
- [ ] Redis/DB/LLM endpoints reachable

## Documentation & Support
- [ ] `docs/INSTALL.md` validated on fresh Ubuntu 24.04 instance
- [ ] `docs/DEPLOY.md` staging + production flows executed
- [ ] `docs/OPERATIONS_RUNBOOK.md` reviewed by on-call SRE
- [ ] User guide / FAQ shared with stakeholders
- [ ] Rollback plan rehearsed (testnet switch)

## Final Decision
- [ ] Go
- [ ] No-Go (attach blocking issues and mitigation plan)

Sign-off:
- Release Manager:
- Security Lead:
- Product Owner:
