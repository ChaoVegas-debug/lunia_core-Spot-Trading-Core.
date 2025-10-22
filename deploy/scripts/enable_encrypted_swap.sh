#!/usr/bin/env bash
set -Eeuo pipefail

log() {
  printf '[swap] %s\n' "$*"
}

if [[ "${ENABLE_ENCRYPTED_SWAP:-true}" != "true" ]]; then
  log "encrypted swap disabled via ENABLE_ENCRYPTED_SWAP"
  exec "$@"
fi

if [[ $(id -u) -ne 0 ]]; then
  log "not running as root; skipping encrypted swap setup"
  exec "$@"
fi

SWAP_FILE="${ENCRYPTED_SWAP_FILE:-/tmp/encswap.img}"
SWAP_SIZE_MB="${ENCRYPTED_SWAP_SIZE_MB:-512}"
MAPPER_NAME="${ENCRYPTED_SWAP_MAPPER:-encswap0}"

if grep -q "${MAPPER_NAME}" /proc/swaps 2>/dev/null; then
  log "encrypted swap already active"
  exec "$@"
fi

if ! command -v cryptsetup >/dev/null 2>&1; then
  log "cryptsetup not available, cannot enable encrypted swap"
  exec "$@"
fi

log "provisioning encrypted swap at ${SWAP_FILE} (${SWAP_SIZE_MB}MB)"
rm -f "${SWAP_FILE}"
dd if=/dev/urandom of="${SWAP_FILE}" bs=1M count="${SWAP_SIZE_MB}" status=none
chmod 600 "${SWAP_FILE}"

echo "type swap" | cryptsetup open --type plain --key-file - "${SWAP_FILE}" "${MAPPER_NAME}" || {
  log "cryptsetup failed; continuing without encrypted swap"
  exec "$@"
}
mkswap "/dev/mapper/${MAPPER_NAME}" >/dev/null
swapon "/dev/mapper/${MAPPER_NAME}" || log "unable to activate encrypted swap"

exec "$@"
