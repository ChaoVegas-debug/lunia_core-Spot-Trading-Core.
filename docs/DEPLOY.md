# Lunia Core Deployment Guide

This document outlines staging and production deployment procedures, including reverse proxy, WAF/IDS hardening, and Vault/mTLS enablement.

## 1. Repository Layout

Key deployment assets:

- `docker-compose.staging.yml` – staging profile aggregating API, scheduler, arbitrage, bot, Redis.
- `docker-compose.prod.yml` – production profile with hardened defaults.
- `lunia_core/infra/docker-compose.yml` – base definition reused by both profiles.
- `lunia_core/infra/systemd/*.service` – sample systemd units for process supervision.
- `deploy/waf/` – ModSecurity + CrowdSec bundles.
- `deploy/vault/` – Vault/KMS bootstrap scripts.

## 2. Staging Deployment (Docker Compose)

```bash
cd /opt/lunia_core/lunia_core
cp .env.example .env   # adjust secrets for staging
chmod 600 .env

docker compose -f docker-compose.staging.yml pull --ignore-pull-failures
docker compose -f docker-compose.staging.yml up -d
```

Smoke verification:
```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/api/portfolio/explain/BTCUSDT | jq
```

To stop:
```bash
docker compose -f docker-compose.staging.yml down -v
```

## 3. Production Deployment

```bash
cd /opt/lunia_core/lunia_core
cp .env.example .env    # ensure production secrets + BINANCE_LIVE_TRADING=true
nano .env               # set INFRA_PROD_ENABLED=true
chmod 600 .env

docker compose -f docker-compose.prod.yml pull --ignore-pull-failures
docker compose -f docker-compose.prod.yml up -d
```

Validate SLO endpoints:
```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/metrics | grep -E 'core_pnl|risk_exposure'
```

Roll back:
```bash
docker compose -f docker-compose.prod.yml down -v
INFRA_PROD_ENABLED=false docker compose -f docker-compose.staging.yml up -d
```

## 4. Reverse Proxy & TLS

### Option A: Caddy (ships with repo)

```bash
docker compose --profile tls -f lunia_core/infra/docker-compose.yml up -d caddy
```
Set `LUNIA_DOMAIN` and `LUNIA_TLS_EMAIL` in `.env`. Caddy provisions Let's Encrypt certificates automatically and enforces HTTPS (HSTS enabled by default).

### Option B: Nginx

1. Install Nginx on host: `sudo apt install -y nginx`.
2. Use sample server block:
   ```nginx
   server {
     listen 80;
     server_name example.com;
     return 301 https://$host$request_uri;
   }

   server {
     listen 443 ssl http2;
     server_name example.com;

     ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
     ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
     include /etc/letsencrypt/options-ssl-nginx.conf;
     add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
     add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none';";

     location / {
       proxy_pass http://127.0.0.1:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
       proxy_set_header X-Forwarded-Proto https;
     }
   }
   ```
3. Reload Nginx: `sudo systemctl reload nginx`.

## 5. WAF / IDS Integration

1. Deploy ModSecurity with the Core Rule Set:
   ```bash
   docker compose -f deploy/waf/docker-compose.waf.yml up -d
   ```
   Logs appear under `deploy/waf/logs/`.
2. Enable CrowdSec & Fail2Ban using sample configs in `deploy/waf/`.

## 6. Vault / KMS / mTLS

1. Bootstrap Vault (see `deploy/vault/bootstrap.sh`).
2. Enable `INFRA_PROD_ENABLED=true` in `.env` to activate secure clients.
3. Configure mTLS certificates in `deploy/vault/mtls-config.json` and distribute to services.
4. Export secrets to Vault using per-tenant policies under `deploy/vault/policies/`.

## 7. Monitoring & Logging

- Start observability stack:
  ```bash
  docker compose -f lunia_core/infra/docker-compose.yml --profile monitoring up -d
  docker compose -f lunia_core/infra/logging/docker-compose.logging.yml up -d
  ```
- Grafana dashboards are provisioned from `lunia_core/infra/monitoring/grafana/`.
- Vector forwards logs to Elasticsearch/S3 (configure credentials in `.env`).

## 8. Post-Deployment Checklist

- [ ] `scripts/verify_all.sh`
- [ ] OWASP ZAP scan returns grade A or better
- [ ] `docs/GO_NO_GO_CHECKLIST.md` completed and signed off
- [ ] `docs/RELEASE_REPORT.md` archived with artifacts
- [ ] Vault tokens rotated, secrets sealed
