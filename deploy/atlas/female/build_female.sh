#!/usr/bin/env bash
# Build the female atlas model files inside the human-atlas clone (outside this repo). No network, no deploy.
#   deploy/atlas/female/build_female.sh [human-atlas-clone-dir]     default: ~/Projects/third_party/human-atlas
# Needs: Node >= 22.13, the GLB in deploy/atlas/female/source/ (see README.md), `npm ci` already run in the clone
# (build_atlas.sh does that; the optimizer needs its `meshoptimizer` dependency).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DIR="${1:-$HOME/Projects/third_party/human-atlas}"
GLB="$HERE/source/3d-vh-f-united.glb"
EXPECT_SHA="472567a56896b9b7890508da6501fbf858e56aaa30745365f7a71ade782b529c"
[ -f "$GLB" ] || { echo "missing $GLB; see deploy/atlas/female/README.md (download needs the user's yes)"; exit 1; }
[ -d "$DIR/node_modules/meshoptimizer" ] || { echo "run 'npm ci' in $DIR first (deploy/atlas/build_atlas.sh does)"; exit 1; }
SHA="$(shasum -a 256 "$GLB" | cut -d' ' -f1)"
[ "$SHA" = "$EXPECT_SHA" ] || { echo "GLB sha256 $SHA does not match the recorded $EXPECT_SHA"; exit 1; }
MODELS="$DIR/public/models"
rm -f "$MODELS"/female.json "$MODELS"/female-*.bin "$MODELS"/female-*.bin.gz "$MODELS"/female.json.gz
# FEMALE_ARGS="--exclude-allen" builds without the 282 Allen brain meshes (see README: licence check)
node "$HERE/convert_glb.mjs" --glb "$GLB" --out "$MODELS" ${FEMALE_ARGS:-}
( cd "$DIR" && node scripts/optimize-anatomy.mjs female.json )      # weld + simplify (0.2% error) + female-N.bin, removes female-src-N.bin
node "$HERE/compress_female.mjs" "$MODELS"
node "$HERE/validate_female.mjs" "$MODELS"
echo "female model built in $MODELS (female.json, female-N.bin, female-N.bin.gz, female.json.gz)"
