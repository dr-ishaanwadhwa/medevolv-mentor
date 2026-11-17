#!/usr/bin/env bash
# Runs on YOUR Mac. Copies the built atlas (dist/) to the VM; Caddy serves it as atlas.medevolv.in.
#   deploy/atlas/push_atlas.sh <vm-public-ip> [ssh-key-path]
# One-time prerequisites: DNS A record atlas.medevolv.in -> VM IP, the Caddyfile block from Caddyfile.atlas appended
# to deploy/oci/Caddyfile, and one normal deploy/oci/push.sh run so Caddy gets the ../atlas-site volume.
set -euo pipefail
HOST="$1"; KEY="${2:-$HOME/.ssh/eka_oci}"
HERE="$(cd "$(dirname "$0")" && pwd)"
CLONE="${ATLAS_CLONE:-$HOME/Projects/third_party/human-atlas}"
[ -f "$CLONE/dist/index.html" ] || "$HERE/build_atlas.sh" "$CLONE"
# the pinned patch must be what was built: refuse a dist built without the deep link
grep -rq "medevolv-credit" "$CLONE/dist/assets" || { echo "dist lacks the deep-link patch; run deploy/atlas/build_atlas.sh"; exit 1; }
# the female set must be the one asked for (default: the study model, ADR-003); an older dist may hold the HRA set
if [ "${FEMALE:-1}" != "0" ] && [ "${FEMALE_MODEL:-study}" = "study" ]; then
  head -c 200 "$CLONE/dist/models/female.json" 2>/dev/null | grep -q '"version":"female-study-v3' \
    || { echo "dist/models/female.json is not the female study model; run deploy/atlas/build_atlas.sh"; exit 1; }
fi
SSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
$SSH "ubuntu@$HOST" "mkdir -p atlas-site"
# atlas-site lives beside eka/ (not inside it) so deploy/oci/push.sh's rsync --delete never wipes it
rsync -az --delete -e "$SSH" "$CLONE/dist/" "ubuntu@$HOST:atlas-site/"
echo "Atlas files at ~/atlas-site. Test: https://atlas.medevolv.in/?select=heart"
