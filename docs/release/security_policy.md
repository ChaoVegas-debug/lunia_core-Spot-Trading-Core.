# Lunia Core — Security Policy (Production)

## 1. Authentication & Authorization

- SSO (OIDC) обязателен для операторов; JWT сохраняется в течение 15 минут.
- RBAC роли: owner > admin > viewer > auditor. Минимальные права для доступа к дашборду — viewer.
- Tenant isolation (Chinese Wall) включена: API требует `X-Lunia-Tenant` для всех write-операций.

## 2. Secrets & Keys

- API ключи Binance/Bybit/OKX/Kraken хранятся в HashiCorp Vault.
- Каждому tenant назначается собственный namespace и KMS key.
- Авто-ротация каждые 90 дней, emergency revoke — `vault write auth/disable tenant=<id>`.

## 3. Network Security

- Все сервисы используют mTLS (`deploy/vault/mtls-config.json`).
- WAF (modsecurity) и IDS/IPS (CrowdSec + Fail2Ban) включаются флагом `INFRA_PROD_ENABLED`.
- Falco/eBPF мониторит runtime аномалии (см. `deploy/falco`).

## 4. Logging & Monitoring

- Centralized logging через Vector → Elasticsearch/S3, логи хранятся 365 дней.
- Compliance evidence: weekly audit dump + quarterly access review (`docs/release/runbook.md`).
- `/metrics` публикует SLO/SLA метрики; auto-remediation выполняет self-healing.

## 5. Incident Response

- Любое нарушение мандатов рынка → немедленный `global_stop` и уведомление security@lunia.
- Security incidents документируются в Jira (label `SEC-INCIDENT`).
- Playbooks см. в runbook (раздел 3).

## 6. Third-party Pentest & SOC 2

- Pentest результаты сохраняются в `reports/pentest/` (шифрование AES-256, доступ по запросу).
- SOC 2 контрольные листы в `reports/compliance/`.
- Все критичные CVE отслеживаются через `make vuln-scan` (Syft + Grype) и закрываются ≤72 часов.

