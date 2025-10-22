from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WAF_DIR = REPO_ROOT / "deploy" / "waf"
VAULT_DIR = REPO_ROOT / "deploy" / "vault"


def test_modsecurity_configuration_present():
    config = (WAF_DIR / "modsecurity.conf").read_text(encoding="utf-8")
    assert "SecRuleEngine On" in config
    assert "INFRA_PROD_ENABLED" in config
    compose = (WAF_DIR / "docker-compose.waf.yml").read_text(encoding="utf-8")
    assert "modsecurity" in compose.lower()
    assert "crowdsec" in compose.lower()
    assert "fail2ban" in compose.lower()


def test_vault_configuration_contains_mtls_and_tenant_policies():
    vault_hcl = (VAULT_DIR / "vault.hcl").read_text(encoding="utf-8")
    assert "tls_disable   = 0" in vault_hcl
    assert "kms_key_id" in vault_hcl
    tenant_policy = (VAULT_DIR / "policies" / "tenant-base.hcl").read_text(
        encoding="utf-8"
    )
    assert "tenant_id" in tenant_policy
    mtls_manifest = (VAULT_DIR / "mtls-config.json").read_text(encoding="utf-8")
    assert '"mutual_tls": true' in mtls_manifest
