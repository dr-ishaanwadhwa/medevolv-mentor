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
# Female model (R5): built into public/models before the vite build copies it into dist/. Skipped when the source GLB
# has not been downloaded, or with FEMALE=0. Needs the user's yes for the download (deploy/atlas/female/README.md).
if [ "${FEMALE:-1}" != "0" ] && [ -f "$HERE/female/source/3d-vh-f-united.glb" ]; then
  "$HERE/female/build_female.sh" "$DIR"
fi
# Precompressed manifest so Caddy's `precompressed gzip` serves atlas.json compressed (1.3 MB -> about 0.2 MB).
gzip -9 -kf public/models/atlas.json
npm run build
cp LICENSE dist/LICENSE-human-atlas.txt          # MIT notice travels with the static files
cp "$HERE/ATTRIBUTION.md" dist/ATTRIBUTION.md    # BodyParts3D CC BY 4.0
echo "built $DIR/dist ($(du -sh dist | cut -f1))"
