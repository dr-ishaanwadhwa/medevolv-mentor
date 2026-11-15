# Female atlas model: build runbook

Turns the HRA "3D Reference Organ Set for United, Female" v1.5 GLB into the atlas manifest and chunk files the 3D viewer
reads (`female.json`, `female-N.bin`, `female-N.bin.gz`). Offline only: nothing here deploys. The model files stay out of
git (`.gitignore`: `deploy/atlas/female/source/` and `work/`; the outputs live in the human-atlas clone).
Spec: `docs/prd/2026-11-15-next-release-prd.md` section 4.5. Credit text and change list: `deploy/atlas/ATTRIBUTION.md`.

## Source (needs the user's yes to download; given 2026-11-15)
| | |
|---|---|
| URL | https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb |
| Size | 211,624,968 bytes (matches the HEAD request; last-modified 2026-06-10) |
| SHA-256 | `472567a56896b9b7890508da6501fbf858e56aaa30745365f7a71ade782b529c` |
| Licence | CC BY 4.0 (creators Kristen Browne, Heidi Schlehlein; publisher HuBMAP) |
| Destination | `deploy/atlas/female/source/3d-vh-f-united.glb` (git-ignored), checksum beside it as `.sha256` |

```
mkdir -p deploy/atlas/female/source && cd deploy/atlas/female/source
curl -fL -O https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb
shasum -a 256 3d-vh-f-united.glb      # must equal the value above
```

## Build
```
deploy/atlas/female/build_female.sh [human-atlas-clone]      # default ~/Projects/third_party/human-atlas
FEMALE_ARGS="--exclude-allen" deploy/atlas/female/build_female.sh   # without the 282 Allen brain meshes
```
Needs Node >= 22.13 and `npm ci` already run in the clone (`deploy/atlas/build_atlas.sh` does it; the optimizer needs
`meshoptimizer`). `build_atlas.sh` also calls this script when the GLB is present (skip with `FEMALE=0`). Takes about 10 s.

Steps, each a script in this folder:
1. `convert_glb.mjs` (no dependencies; a GLB is JSON plus one binary chunk). Bounds check first, then bake node transforms,
   place on the stage, clean names, map ids and systems, write `female.json` and `female-src-N.bin` into the clone's
   `public/models/`, and `id_map.csv` here.
2. `scripts/optimize-anatomy.mjs female.json` in the clone (upstream script; picks the `female` prefix from the file
   name): welds coincident vertices and averages normals, simplifies each mesh at a 0.2% error bound, writes
   `female-N.bin`, deletes the `female-src` files.
3. `compress_female.mjs`: `female-N.bin.gz`, `gzip`/`gzipBytes` fields in `female.json`, plus `female.json.gz` and
   `atlas.json.gz` (upstream `compress-models.mjs` only handles `atlas.json`).
4. `validate_female.mjs`: integrity (every index in range, sizes, gzip round-trip, unique ids, ids uppercase without
   spaces or commas), scale and placement, 20 anatomical spot checks (left is +x, cervix below the uterine body, bladder
   anterior to the uterus, and so on), and mapping coverage from `id_map.csv`. Exit 1 on any failure.
   (Upstream `validate-atlas.mjs` hard-codes the male counts 2234/3432, so it cannot be reused.)

Output paths: `~/Projects/third_party/human-atlas/public/models/female.json` (manifest), `female-0.bin` ... `female-9.bin`
and the `.gz` of each, `female.json.gz`. The vite build copies them into `dist/models/`, and `push_atlas.sh` (rsync
`--delete`) ships `dist/`, so a manual upload of the female files would be wiped by the next atlas push. Deploy needs
the user's yes and a free-disk check on the VM first (`df -h` there); this runbook does not do it.

## Measured result (build of 2026-11-15, brain included)
| | Brain included | `--exclude-allen` |
|---|---|---|
| Meshes (parts) | 888 | 606 |
| Concepts | 1,162 | 832 |
| Triangles (source / after weld + simplify) | 5,557,599 / 1,810,421 | n/a / 1,333,274 |
| Chunk files | 10 | 7 |
| Raw chunk bytes | 38.36 MB | 28.33 MB |
| **gzip chunk bytes (download)** | **23.63 MB** | **17.01 MB** |
| `female.json` / `.json.gz` | 550,461 / 119,722 bytes | |

Budget (PRD 4.5): at most 35 MB gzip with the brain included. Met with margin, so no separate brain chunk group is needed.
For comparison the male set is 15 chunks with about 33 MB gzip. `atlas.json` is 1,335,285 bytes and `atlas.json.gz`
215,452 bytes.

## Bounds check (PRD 4.5 step 2: units and axes were UNKNOWN)
The file is **metres, Y-up, left = +x, anterior = +z**, the same frame as the male model. Measured after baking node
transforms (there are none: all 1,073 nodes have identity transforms): skin extent 0.9674 x 1.6663 x 0.3293 m against the
HRA metadata 967.44 x 1666.35 x 329.29 mm, a maximum error of 0.1%; the millimetre and Z-up readings are off by 99% and 400%
and fail. The HRA placement metadata (-90 degree X rotation, millimetre translation 489.56, 794.76, 222.62) maps the file
into the HRA global frame; its translation puts the skin's minimum corner at the origin (its y value 794.76 mm is exactly our feet shift; we also centre x and z, as the male model does). The two conflicting statements in the
research notes are both right: the file is metres/Y-up, the placement is in millimetres. The converter fails if neither
reading matches within 5%. The whole-model z extent is 0.455 m, not 0.329, because the 8 placenta and umbilical items lie
in front of the skin (a reference placement); the check therefore compares the skin, which is what the metadata box
describes.

Placement: skin lowest point to y = 0, skin box centred on x and z (the male skin does the same, 0 to 1.73 m).

## Id mapping (`id_map.csv`, committed; columns `mesh_name, concept_id, concept_name, source, reviewed_by`)
The GLB is richer than the research notes said: 678 of the 888 mesh nodes carry a non-empty `ontologyid` (676 are well-formed FMA or UBERON ids) and a
`label` in their node `extras`, so pass 1 reads those instead of guessing names.

| Source | Meshes | Rule |
|---|---|---|
| `hra-extras:FMA` | 239 | `FMA:12345` becomes `FMA12345` (our concept id form; matches the crosswalk) |
| `hra-extras:UBERON` | 175 | kept as `UBERON:0000996` |
| `synthetic:shared-id-split` | 262 | several meshes (usually Left and Right) share one class id. Each mesh gets its own `HRA:VH_F_<NAME>` concept so a click selects one side, and the shared class becomes a parent concept holding all of them |
| `synthetic:no-ontology-id` | 210 | `-` in the file (180 are Allen brain regions): `HRA:VH_F_<NAME>`, uppercase, no spaces or commas |
| `synthetic:malformed-id` | 2 | `FMA64019` without a colon on both menisci: treated as unusable, synthetic |
| group rows | 182 | compound concepts over descendants, for example `HRA:VH_F_UTERUS` (10 parts), `HRA:VH_F_OVARY`, `HRA:VH_F_FALLOPIAN_TUBE`, and `HRA:VH_F_ALLEN_BRAIN` (282) |

Coverage: **676 of 888 meshes (76.1%) are backed by an FMA or UBERON class** from the source file; 212 (23.9%) have only a
synthetic id. All 888 meshes have a concept and a system. **Nothing is hand-reviewed yet**: `reviewed_by` is empty for
every row, and the PRD ships the automatic mapping flagged off (`female_atlas` false) until a named anatomy reviewer signs
off the clinically important set (about 100 names: uterus parts, ovary, tube, vagina, cervix, breast, ligaments).
Corrections go in `id_overrides.csv` (header `mesh_name,concept_id,concept_name,reviewed_by`; the converter applies it, source
becomes `override`); the file does not exist yet. No FMA id has been invented: the group concepts for uterus, ovary,
tube and cervix use synthetic ids because the source gives no class id for them.

## Systems
`VH_F_*_system` parents map to the existing 15 systems plus two new ones (added to `anatomy.ts`): `reproductive_female`
("Reproductive (female)": 54 meshes, including the breast) and `pregnancy` ("Pregnancy reference": the 8 placenta and
umbilical items, hidden by default). Eyes are `sensory`, heart `cardiac`, vessels `arterial`/`venous` by name, brain and
spinal cord `nervous`, tonsil `lymphatic`. The male model's `reproductive` system is unused in the female model. Counts:
nervous 316, skeletal 91, urinary 87, respiratory 70, digestive 59, venous 57, reproductive_female 54, arterial 53,
sensory 46, muscular 16, lymphatic 16, cardiac 14, pregnancy 8, integumentary 1.

## Names
Node name minus `VH_F_`/`Allen_`, underscores to spaces, trailing `_L`/`_R` to a leading Left/Right, first letter
capitalised. Corrected source typos (listed in the converter output): jejenum, eigth, opthalmic, fibria (fimbria), schlemms.
Concept names use the file's `label` (the official FMA/UBERON wording) when present.

## Known gaps and decisions for the lead
- **Allen brain licence unverified** (PRD): the DOI page read on 2026-11-15 does not say. Ship with the brain only after
  checking, or rebuild with `--exclude-allen` (17.0 MB).
- The 8 pregnancy items lie in front of the body, so a camera framed on "all non-skin parts" (`AtlasScene` `wanted`) gets
  a deeper z box even with the layer off. Effect: slightly farther default distance for the female model. Fix when the
  female switch is built (frame only visible layers).
- No vulva, clitoris or labia; skeleton and muscles partial (UI note in PRD 4.5).
- The model is not verified to be a single subject (the pages read do not say); no UI copy should claim "one body".
- Crosswalk rows (`sex: "female"`), `/api/spatial/resolve` `sex`, `atlasHref` and the toggle UI are not built yet (later P3 work).
