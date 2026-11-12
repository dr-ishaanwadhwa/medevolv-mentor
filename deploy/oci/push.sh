#!/usr/bin/env bash
# Runs on YOUR Mac. Builds the bundle, copies it to the VM, starts it there.
#   [DOMAIN=study.medevolv.in] deploy/oci/push.sh <vm-public-ip> [ssh-key-path]
set -euo pipefail
HOST="$1"; KEY="${2:-$HOME/.ssh/eka_oci}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
OUT="$(mktemp -d)/eka"

# Secrets: only the three variables the server needs, taken from .env without printing them
grep -q "^DEEPSEEK_API_KEY=." .env || { echo "Add DEEPSEEK_API_KEY=... to .env first"; exit 1; }
grep -q "^APP_PASSWORD=." .env || echo "Note: no APP_PASSWORD in .env, so the site will be public (no login)."

.venv/bin/python -m deploy.build_hf_bundle "$OUT"
cp deploy/oci/docker-compose.yml deploy/oci/Caddyfile deploy/oci/setup.sh "$OUT/"
{ grep -E '^(DEEPSEEK_API_KEY|APP_PASSWORD)=' .env; echo "LLM_BACKEND=deepseek"; echo "EMBED_BACKEND=local"; } > "$OUT/.env"
chmod 600 "$OUT/.env"

SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
rsync -az --delete -e "$SSH" "$OUT/" "ubuntu@$HOST:eka/"
rm -rf "$(dirname "$OUT")"
$SSH "ubuntu@$HOST" "chmod 600 eka/.env && DOMAIN='${DOMAIN:-}' bash eka/setup.sh"
