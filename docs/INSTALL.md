# Lunia Core Installation Guide (Ubuntu 24.04 LTS)

This guide describes how to deploy Lunia Core on a clean Ubuntu 24.04 LTS VPS. The procedure covers host preparation, dependency installation, environment configuration, and service bootstrap using systemd.

## 1. Prepare the Host

1. Update the OS and install base packages:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install -y build-essential curl git gnupg lsb-release tzdata ufw fail2ban
   sudo timedatectl set-timezone Europe/Warsaw
   ```
2. Harden SSH (optional but recommended):
   - Disable password logins and root SSH in `/etc/ssh/sshd_config`.
   - Restart SSH: `sudo systemctl restart ssh`.
3. Enable automatic security updates:
   ```bash
   sudo apt install -y unattended-upgrades
   sudo dpkg-reconfigure --priority=low unattended-upgrades
   ```
4. Configure Fail2Ban with the default jail and enable the service:
   ```bash
   sudo systemctl enable --now fail2ban
   ```

## 2. Install Docker and Compose

```bash
sudo apt install -y ca-certificates apt-transport-https software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER
```
Log out and back in so the new group membership applies.

## 3. Install Python Tooling

```bash
sudo apt install -y python3 python3-venv python3-pip
python3 --version
pip3 install --upgrade pip
```

## 4. Clone Lunia Core

```bash
sudo mkdir -p /opt/lunia_core
sudo chown $USER:$USER /opt/lunia_core
cd /opt/lunia_core
git clone <REPO_URL> lunia_core
cd lunia_core
```

## 5. Configure the Environment

1. Copy the example configuration and adjust secrets:
   ```bash
   cp lunia_core/.env.example .env
   nano .env
   ```
2. Ensure sensitive values (API keys, tokens) are set and restrict permissions:
   ```bash
   chmod 600 .env
   ```

## 6. Bootstrap the Virtual Environment (optional for local operations)

```bash
make -C lunia_core dev-deps
```

## 7. Systemd Service

The repository ships a sample unit file: `lunia_core/infra/systemd/lunia_core.service`.

1. Copy and enable the service:
   ```bash
   sudo cp lunia_core/infra/systemd/lunia_core.service /etc/systemd/system/lunia_core.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now lunia_core.service
   ```
2. Check status and logs:
   ```bash
   sudo systemctl status lunia_core.service
   sudo journalctl -u lunia_core.service -f
   ```

## 8. Verification

Run the unified verification script (produces artifacts under `artifacts/verify_*`):
```bash
bash scripts/verify_all.sh
```

For a condensed run via Make:
```bash
make -C lunia_core verify
```

## 9. Smoke Test

Once services are up, validate:
```bash
curl -fsS http://localhost:8000/healthz
curl -fsS http://localhost:8000/metrics | head
```

## 10. Next Steps

* Review `docs/DEPLOY.md` for staging/production Compose profiles.
* Follow `docs/SECURITY_POLICY.md` to enforce RBAC, secrets storage, and audit requirements.
* Consult `docs/OPERATIONS_RUNBOOK.md` for recovery procedures.
