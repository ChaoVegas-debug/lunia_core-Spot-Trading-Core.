#!/usr/bin/env bash
set -euo pipefail

if [[ "${INFRA_PROD_ENABLED:-false}" != "true" ]]; then
  echo "INFRA_PROD_ENABLED is not true; skipping Vault bootstrap"
  exit 0
fi

if [[ -z "${VAULT_KMS_KEY_ID:-}" ]]; then
  echo "VAULT_KMS_KEY_ID must be set" >&2
  exit 1
fi

echo "Initialising Vault policies for Lunia Core"
vault policy write tenant-base "$(dirname "$0")/../policies/tenant-base.hcl"
vault policy write operator "$(dirname "$0")/../policies/operator.hcl"

echo "Creating transit key per tenant placeholder"
for tenant in default institutional premium; do
  vault secrets enable -path="kv/tenants/${tenant}" -version=2 kv >/dev/null 2>&1 || true
  vault write -f "transit/keys/tenant-${tenant}" >/dev/null 2>&1 || true

done
echo "Vault bootstrap completed"
