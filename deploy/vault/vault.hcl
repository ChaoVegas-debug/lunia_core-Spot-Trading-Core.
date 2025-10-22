storage "file" {
  path = "/vault/data"
}

listener "tcp" {
  address       = "0.0.0.0:8200"
  tls_disable   = 0
  tls_cert_file = "/vault/tls/server.crt"
  tls_key_file  = "/vault/tls/server.key"
  tls_client_ca_file = "/vault/tls/ca.crt"
}

seal "awskms" {
  region     = "eu-central-1"
  kms_key_id = "${VAULT_KMS_KEY_ID}"
}

disable_mlock = true
ui = true
max_lease_ttl = "24h"
default_lease_ttl = "1h"

api_addr = "https://vault.service.consul:8200"
cluster_addr = "https://vault.service.consul:8201"
