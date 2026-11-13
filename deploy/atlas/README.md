# 3D anatomy atlas (human-atlas) for MedEvolv Mentor

Upstream: https://github.com/ashemag/human-atlas (MIT), data BodyParts3D (CC BY 4.0, see `ATTRIBUTION.md`).
It is built outside this repo (`~/Projects/third_party/human-atlas`, never committed here) and served as static files.

## What we change: `deep-link.patch` (one file, `app/page.tsx`)
- `?select=<name | FMA id | source mesh id>`: on load, ranks the atlas concepts (exact name > id > prefix > shortest
  substring), then selects, isolates and opens details for the best match. No match: the normal atlas opens.
- `?system=<system id>` (e.g. `skeletal`, `arteries`): shows only that layer.
- A fixed footer credit "BodyParts3D © DBCLS, CC BY 4.0" linking to the licence. The existing About sheet keeps the full text.

The mentor links use FMA ids (`?select=FMA19667`), written into `data/graph/atlas_crosswalk.jsonl` by
`scripts/build_atlas_crosswalk.py`.

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
