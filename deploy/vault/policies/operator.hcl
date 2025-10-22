# Operator policy for break-glass recovery. Restricted to auditing actions.
path "sys/health" {
  capabilities = ["read"]
}

path "sys/audit" {
  capabilities = ["list", "read"]
}

path "sys/policies/acl" {
  capabilities = ["list"]
}

path "kv/*" {
  capabilities = ["list"]
}
