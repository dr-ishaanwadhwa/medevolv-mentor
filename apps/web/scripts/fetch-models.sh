#!/usr/bin/env bash
# Fetch the BodyParts3D model binaries (~90 MB, CC BY 4.0) into public/models. They are git-ignored.
# Usage: scripts/fetch-models.sh [path-to-human-atlas-clone]
set -euo pipefail
here="$(cd "$(dirname "$0")/.." && pwd)"
dest="$here/public/models"
src="${1:-$HOME/Projects/third_party/human-atlas}"
if [ ! -f "$src/public/models/atlas.json" ]; then
  src="$(mktemp -d)/human-atlas"
  git clone --depth 1 https://github.com/ashemag/human-atlas "$src"
fi
mkdir -p "$dest"
cp "$src"/public/models/atlas.json "$src"/public/models/body-*.bin* "$dest"/
echo "Models ready in $dest ($(du -sh "$dest" | cut -f1))"
