#!/usr/bin/env bash
# Runs on YOUR Mac. Builds the v2 web app here (the VM has 1 CPU), ships web + API code to ~/v2 on the VM, starts it,
# and adds the v2 Caddy block to the running Caddy (validated first, reloaded in place: no downtime for other sites).
#   deploy/v2/push.sh <vm-public-ip> [ssh-key-path]
# Needs eka-app already built on the VM (deploy/oci/push.sh): the API image is FROM it, so data/ comes from there.
set -euo pipefail
HOST="$1"; KEY="${2:-$HOME/.ssh/eka_oci}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"; cd "$ROOT"
V2HOST="v2.${HOST//./-}.sslip.io"
OUT="$(mktemp -d)/v2"; mkdir -p "$OUT"
ENV_FILE="${ENV_FILE:-.env}"   # default .env in the repo root; override with ENV_FILE=/path/to/.env
grep -q "^DEEPSEEK_API_KEY=." "$ENV_FILE" || { echo "Add DEEPSEEK_API_KEY=... to .env first"; exit 1; }

# 1. web: standalone build (models are NOT bundled; Caddy serves /models from the atlas mount)
NEXT_PUBLIC_MODELS_BASE=/models pnpm --dir apps/web build
SA=apps/web/.next/standalone
test -f "$SA/apps/web/server.js" || { echo "no standalone server.js (next.config output: 'standalone'?)"; exit 1; }
mkdir -p "$OUT/web"
cp -R "$SA/." "$OUT/web/"
mkdir -p "$OUT/web/apps/web/.next" && cp -R apps/web/.next/static "$OUT/web/apps/web/.next/static"
rsync -a --exclude models apps/web/public/ "$OUT/web/apps/web/public/"

# 2. api code (data/ is inside the eka-app base image)
rsync -a --exclude __pycache__ api rag "$OUT/"
mkdir -p "$OUT/ontology" && : > "$OUT/ontology/__init__.py" && cp ontology/merge.py "$OUT/ontology/"
cp deploy/v2/Dockerfile.api deploy/v2/Dockerfile.web deploy/v2/docker-compose.yml deploy/v2/Caddyfile.v2-block "$OUT/"
{ grep -E '^(DEEPSEEK_API_KEY|ATLAS_URL)=' "$ENV_FILE"; echo "LLM_BACKEND=deepseek"; echo "EMBED_BACKEND=local"; } > "$OUT/.env"
chmod 600 "$OUT/.env"

# API fingerprint: the API container is recreated only when this changes. It covers the API code, the API image
# inputs and the bundled .env (env_file is read when the container is created). Hashing .env via stdin keeps the
# temp path out of the hash, so the same inputs always give the same value.
API_SHA="$({ find api rag ontology/merge.py -type f -name '*.py' | sort | xargs shasum
            shasum deploy/v2/Dockerfile.api deploy/v2/docker-compose.yml
            shasum < "$OUT/.env"; } | shasum | cut -d' ' -f1)"
printf '%s\n' "$API_SHA" > "$OUT/api.sha"

SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
# read the previous fingerprint from the VM BEFORE rsync overwrites it (empty if the VM has none yet)
PREV_SHA="$($SSH "ubuntu@$HOST" 'cat ~/v2/api.sha 2>/dev/null || true')"
if [ "$PREV_SHA" = "$API_SHA" ]; then
  COMPOSE_UP="docker compose up -d --build --no-deps v2-web"; API_RECREATED=0
  echo "API code unchanged: rebuilding web only"
else
  COMPOSE_UP="docker compose up -d --build"; API_RECREATED=1
  echo "API code changed or first deploy: rebuilding and recreating the API"
fi
rsync -az --delete -e "$SSH" "$OUT/" "ubuntu@$HOST:v2/"
rm -rf "$(dirname "$OUT")"

# 3. start containers, then add the Caddy block if missing (validate inside the running Caddy before reloading)
$SSH "ubuntu@$HOST" bash -s <<REMOTE
set -euo pipefail
chmod 600 ~/v2/.env
cd ~/v2 && sudo $COMPOSE_UP
if ! grep -q "$V2HOST" ~/eka/Caddyfile; then
  cat ~/eka/Caddyfile <(echo) ~/v2/Caddyfile.v2-block > /tmp/Caddyfile.new
  sudo docker cp /tmp/Caddyfile.new eka-caddy-1:/tmp/Caddyfile.new
  sudo docker exec eka-caddy-1 caddy validate --adapter caddyfile --config /tmp/Caddyfile.new
  cat /tmp/Caddyfile.new > ~/eka/Caddyfile        # same inode, so the bind mount sees it
fi
sudo docker exec eka-caddy-1 caddy reload --adapter caddyfile --config /etc/caddy/Caddyfile
REMOTE
echo "Deployed: https://$V2HOST  (first HTTPS request can take ~30 s while the certificate is issued)"

# 4. only after a recreate: wait for the API to answer, then one warm-up question so the next real one is fast
if [ "$API_RECREATED" = 1 ]; then
  ready=0
  for _ in $(seq 1 60); do
    if curl -fsS --max-time 10 -o /dev/null "https://$V2HOST/api/health"; then ready=1; break; fi
    sleep 5
  done
  [ "$ready" = 1 ] || { echo "API did not answer https://$V2HOST/api/health"; exit 1; }
  curl -fsS --max-time 180 -o /dev/null -X POST -H 'Content-Type: application/json' \
    -d '{"question":"warm up"}' "https://$V2HOST/api/chat/stream"
  echo "API warmed"
fi
