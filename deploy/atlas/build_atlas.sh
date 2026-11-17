#!/usr/bin/env bash
# Clone human-atlas OUTSIDE this repo, apply our deep-link patch, build dist/. Needs Node >= 22.13.
#   deploy/atlas/build_atlas.sh [clone-dir]      default clone dir: ~/Projects/third_party/human-atlas
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:-$HOME/Projects/third_party/human-atlas}"
PIN=1c38bf35c254a891200d3cedecfd57abebe83d8d      # upstream commit the patch was made against
[ -d "$DIR/.git" ] || git clone https://github.com/ashemag/human-atlas "$DIR"
cd "$DIR"
git fetch -q origin "$PIN" 2>/dev/null || true
git checkout -q -f "$PIN"
git apply "$HERE/deep-link.patch"
npm ci
# Female model (R5): installed into public/models (female.json + chunks) before the vite build copies it into dist/.
#   FEMALE_MODEL=study (default since 2026-11-17, ADR-003): human-atlas-enhanced female study model v3, from the files in
#     deploy/atlas/female-study/source/ (deploy/atlas/female-study/README.md); fails if they are missing.
#   FEMALE_MODEL=hra: the earlier HRA VH_F v1.5 organs-only build from the GLB (fallback; FEMALE_ARGS="--exclude-allen").
#   FEMALE=0 skips the female model.
if [ "${FEMALE:-1}" != "0" ]; then
  case "${FEMALE_MODEL:-study}" in
    study) node "$HERE/female-study/install_study.mjs" "$DIR/public/models" ;;
    hra) if [ -f "$HERE/female/source/3d-vh-f-united.glb" ]; then "$HERE/female/build_female.sh" "$DIR"; fi ;;
    *) echo "FEMALE_MODEL must be study or hra"; exit 1 ;;
  esac
fi
# Precompressed manifest so Caddy's `precompressed gzip` serves atlas.json compressed (1.3 MB -> about 0.2 MB).
gzip -9 -kf public/models/atlas.json
npm run build
cp LICENSE dist/LICENSE-human-atlas.txt          # MIT notice travels with the static files
cp "$HERE/ATTRIBUTION.md" dist/ATTRIBUTION.md    # BodyParts3D CC BY 4.0
echo "built $DIR/dist ($(du -sh dist | cut -f1))"
