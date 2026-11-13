# 3D anatomy atlas (human-atlas) for MedEvolv Mentor

Upstream: https://github.com/ashemag/human-atlas (MIT), data BodyParts3D (CC BY 4.0, see `ATTRIBUTION.md`).
It is built outside this repo (`~/Projects/third_party/human-atlas`, never committed here) and served as static files.

## What we change: `deep-link.patch` (one file, `app/page.tsx`)
- `?select=<name | FMA id | source mesh id | FMA ids joined by commas>`: several ids (`FMA7309,FMA7310`, both lungs) are
  selected together as one isolated structure. Otherwise, on load, ranks the atlas concepts (exact name > id > prefix > shortest
  substring), then selects, isolates and opens details for the best match. No match: the normal atlas opens.
- `?system=<system id>` (e.g. `skeletal`, `arteries`): shows only that layer.
- The credit "BodyParts3D © DBCLS, CC BY 4.0" (licence link) sits inside the atlas's own footer row, between the controls
  hint and "Source & credits", so nothing overlaps at 320-430 px or on desktop. The About sheet keeps the full text.

The mentor links use FMA ids (`?select=FMA19667`, or two for a left/right pair), written into
`data/graph/atlas_crosswalk.jsonl` by `scripts/build_atlas_crosswalk.py`: every atlas name, a left+right record for
structures drawn only as a pair, curated synonyms, and DeepSeek-checked matches for ontology structure labels (cached,
<= $0.20). `rag.atlas.variants` (plural, "the", "X of Y" order, trailing muscle/bone, hyphens, left/right) is applied at
lookup, so ontology labels and Gray's titles resolve without being listed. The atlas has no peripheral nerves other than a
few cranial ones, no meningeal vessels, no plexuses, no uterus or thyroid: those structures get no link by design.

## Build and deploy (the orchestrator runs these, not the build session)
1. `deploy/atlas/build_atlas.sh` (Node >= 22.13): clone, pin commit, apply patch, `npm ci && npm run build`.
2. DNS: A record `atlas.medevolv.in` -> the VM IP.
3. Append `Caddyfile.atlas` to `deploy/oci/Caddyfile`, preserving the other site blocks (sme-cashflow).
4. Set `ATLAS_URL=https://atlas.medevolv.in` in `.env` (push.sh passes it to the server) and rebuild the crosswalk locally
   (`.venv/bin/python scripts/build_atlas_crosswalk.py`).
5. `DOMAIN=mentor.medevolv.in deploy/oci/push.sh 130.210.60.153` (ships the crosswalk and the Caddy `../atlas-site` volume).
6. `deploy/atlas/push_atlas.sh 130.210.60.153` (copies dist/ to `~/atlas-site`, 108 MB, models ~33 MB gzip-served).
7. Check `https://atlas.medevolv.in/?select=heart` and a mentor Explore page (e.g. Aortic dissection).
Without `ATLAS_URL` the mentor hides every 3D control.
