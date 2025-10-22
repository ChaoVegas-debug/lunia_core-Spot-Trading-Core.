# Vault & KMS Hardening

This package provisions HashiCorp Vault with mTLS, AWS KMS auto-unseal and strict per-tenant policies. It is optional and controlled via the `INFRA_PROD_ENABLED` flag.

## Files
- `vault.hcl` – Vault server configuration with TLS listener and AWS KMS seal
- `policies/tenant-base.hcl` – template applied per tenant enforcing Chinese wall boundaries
- `policies/operator.hcl` – break-glass policy for auditors
- `mtls-config.json` – runtime manifest consumed by services to establish mTLS sessions
- `scripts/bootstrap.sh` – helper to initialise Vault with policies and secrets

## Quick start

```bash
INFRA_PROD_ENABLED=true VAULT_KMS_KEY_ID="arn:aws:kms:..." ./deploy/vault/scripts/bootstrap.sh
```

The bootstrap script seeds the tenant policies, creates transit keys for encryption-at-rest and writes mTLS bundles for workloads. Keys are stored per-tenant in the `kv/tenants/<id>` path and referenced via the existing allocator.
