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
npm run build
cp LICENSE dist/LICENSE-human-atlas.txt          # MIT notice travels with the static files
cp "$HERE/ATTRIBUTION.md" dist/ATTRIBUTION.md    # BodyParts3D CC BY 4.0
echo "built $DIR/dist ($(du -sh dist | cut -f1))"
