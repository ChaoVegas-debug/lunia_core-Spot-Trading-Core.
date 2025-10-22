# Tenant policy ensures strict Chinese wall separation between tenants.
path "kv/data/tenants/{{identity.entity.metadata.tenant_id}}/*" {
  capabilities = ["read", "list", "update"]
}

path "kv/metadata/tenants/{{identity.entity.metadata.tenant_id}}/*" {
  capabilities = ["list"]
}

path "transit/encrypt/tenant-{{identity.entity.metadata.tenant_id}}" {
  capabilities = ["update"]
}

path "transit/decrypt/tenant-{{identity.entity.metadata.tenant_id}}" {
  capabilities = ["update"]
}

path "sys/policies/password" {
  capabilities = ["list"]
}
