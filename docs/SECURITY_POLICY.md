# Security Policy

This policy summarizes the operational and technical controls required to operate Lunia Core in a regulated environment.

## 1. Roles & RBAC

| Role | Description | Permissions |
|------|-------------|-------------|
| `owner`  | Platform owner | Full access to all endpoints, core toggles, infrastructure settings |
| `admin`  | Operations & SRE | Manage deployments, runbooks, view sensitive metrics, execute recovery |
| `viewer` | Read-only UI/API | Read metrics, dashboards, historical data |
| `auditor`| Compliance       | Read audit logs, export evidence |

Policies:
- Enforce SSO (OIDC) with MFA for `owner` and `admin` roles.
- Default role for API tokens should be `viewer`.
- Tenant isolation (Chinese Wall) is enforced by `TENANT_WALL_ENFORCED=true`.

## 2. Secrets Management

- Secrets stored in Vault/KMS. Use per-tenant policies under `deploy/vault/policies/`.
- `.env` files must be protected (`chmod 600`) and never committed.
- Rotate API keys quarterly or upon incident.
- Use mTLS for internal service-to-service communication when `MTLS_ENABLED=true`.

## 3. Authentication Modes

- Hybrid auth: JWT + OIDC SSO. Legacy JWT tokens remain valid until expiration.
- All API endpoints must include auth middleware (`app/api/middleware/auth.py`).
- Refresh tokens stored encrypted; session lifetime ≤ 12 hours.

## 4. Logging & Audit

- Centralized logging pipeline (Vector → Elasticsearch/S3) configured via `infra/logging/`.
- Audit events captured through `app/logging/audit.py`.
- Weekly evidence export: `python -m app.logging.compliance export-weekly`.
- Quarterly access review: `python -m app.logging.compliance export-quarterly`.

## 5. Network Security

- WAF (ModSecurity CRS) + CrowdSec/Fail2Ban per `deploy/waf/`.
- Reverse proxy enforces HTTPS, HSTS, and CSP.
- Restrict access to admin endpoints via VPN or private network.
- Enable Falco runtime detection (`deploy/falco/`).

## 6. Infrastructure Hardening

- AppArmor profile applied to Python runtime (`deploy/security/apparmor-python.profile`).
- Encrypted swap via `deploy/scripts/enable_encrypted_swap.sh`.
- Containers run as non-root where possible (`lunia_core/Dockerfile`).
- `INFRA_PROD_ENABLED=true` gate toggles production-only safeguards.

## 7. Vulnerability Management

- `scripts/verify_all.sh` executes Bandit/Trivy; integrate results into CI (`.github/workflows/verify.yml`).
- Apply security patches monthly.
- Maintain SBOM via Syft + cosign (see `deploy/ci.yml`).
- Block releases if critical CVEs unresolved.

## 8. Incident Response

1. Detect via alerts (Prometheus, Falco, WAF).
2. Triage severity and isolate impacted components.
3. Collect evidence (logs under `artifacts/verify_*`, audit exports).
4. Notify stakeholders and follow `docs/OPERATIONS_RUNBOOK.md`.
5. Conduct post-incident review and update safeguards.

## 9. Data Protection

- Encrypt backups (`ENCRYPT_BACKUPS=true`) and store in restricted S3 bucket.
- Apply data retention policy (30 days default) and scrub PII from logs.
- Access to datasets requires `auditor` role approval.

## 10. Compliance Alignment

- SOC 2 Type II controls tracked via `docs/GO_NO_GO_CHECKLIST.md`.
- Pentest results archived in `docs/release/`.
- Keep release artifacts (reports, SBOM, logs) for ≥ 1 year.
