# Perimeter Protection Stack

This bundle deploys a ModSecurity WAF backed by the OWASP CRS, CrowdSec for collaborative IP reputation and Fail2Ban for local jail enforcement. All services are optional and governed by the `INFRA_PROD_ENABLED` flag so development environments remain lightweight.

## Usage

```bash
INFRA_PROD_ENABLED=true docker compose -f deploy/waf/docker-compose.waf.yml up -d
```

The ModSecurity container proxies traffic to the existing `api` service on port `8080`. CrowdSec ingests ModSecurity audit logs and publishes decisions that Fail2Ban applies locally.

## Files

- `modsecurity.conf` – hardened ModSecurity configuration referencing CRS
- `crs-setup.conf` – CRS tuning baseline
- `crowdsec-config.yaml` / `crowdsec-acquis.yaml` – CrowdSec runtime
- `fail2ban.local` – Fail2Ban jail overrides
- `rules.d/local.rules` – custom local ModSecurity rules

## Feature Flags

Set `INFRA_PROD_ENABLED=false` to disable the WAF rules in staging while still permitting configuration validation.
