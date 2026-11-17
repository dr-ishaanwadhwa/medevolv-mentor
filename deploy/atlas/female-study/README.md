# Female study model (default female atlas set since 2026-11-17)

The female atlas set is the "female study model v3" from human-atlas-enhanced, chosen by the user on 2026-11-17
(decision and alternatives: `docs/wiki/decisions/ADR-003-female-study-model.md`; background:
`docs/wiki/research/2026-11-16-human-atlas-enhanced.md`). The earlier HRA VH_F v1.5 organs-only build
(`deploy/atlas/female/`) stays in the pipeline as the fallback (`FEMALE_MODEL=hra`).

**What it is.** 2,181 male BodyParts3D 4.0 meshes reshaped to a female form by hand-tuned morph fields, plus 64 female
meshes from the Human Reference Atlas VH_F v1.5 (reproductive tract, breast, pelvis, 2 knee ligaments) fitted into that
body. The upstream authors call it experimental, with the morph, breast and glute adjustments "artistic estimates" and
the review unresolved. Our UI labels it "Female (study model)", says it is for orientation only, and marks every
reshaped part (see "Honesty" below). Model files never go into git (`.gitignore`: `deploy/atlas/female-study/source/`).

## Source (downloaded 2026-11-17 with the user's approval)
| | |
|---|---|
| Repo | https://github.com/PrejudiceNeutrino/human-atlas-enhanced (MIT code; data CC BY 4.0) |
| Commit | `fb3ca0f3950dafce4d262c3a0404959753796791` (main on 2026-11-17, "Integrate final three-subject Exam Cram reviews"); the model files were last changed upstream in `048fce3` (wiiiimm, 2026-09-07) |
| URLs | `https://raw.githubusercontent.com/PrejudiceNeutrino/human-atlas-enhanced/<commit>/public/models/<file>` |
| Files | `atlas-female-reconstructed.json`, `female-base-0..15.bin.gz`, `female-joint-additions-8d95b6b434cd4e04.bin.gz`, `female-fit-report.json` (provenance only, not shipped) |
| Bytes | 37,024,852 in 19 files (manifest 1,612,830; chunks gzip 35,138,637 incl. joint additions 9,333; fit report 273,385) |
| Check | every file's git blob hash equals the upstream tree entry at that commit; SHA-256 below and in `SHA256SUMS.txt` (checked by `install_study.mjs`) |

```
mkdir -p deploy/atlas/female-study/source && cd deploy/atlas/female-study/source
C=fb3ca0f3950dafce4d262c3a0404959753796791
B=https://raw.githubusercontent.com/PrejudiceNeutrino/human-atlas-enhanced/$C/public/models
for f in atlas-female-reconstructed.json female-joint-additions-8d95b6b434cd4e04.bin.gz female-fit-report.json \
         $(seq -f 'female-base-%g.bin.gz' 0 15); do curl -fsSL -O "$B/$f"; done
cd .. && shasum -a 256 -c SHA256SUMS.txt
```

SHA-256 (also `SHA256SUMS.txt`):

| File | Bytes | SHA-256 |
|---|---|---|
| atlas-female-reconstructed.json | 1,612,830 | `60a098028eedcb164249a2f7d0b99fb1b9eab56733cd2b90e90b509d29f1da5f` |
| female-base-0.bin.gz | 2,279,399 | `6f8c4840f554fa9bd1b90f866077be877985a72d6fef39a9926b0dd196974eb4` |
| female-base-1.bin.gz | 2,325,209 | `937fea4230ab38265005ae4a258271b35d7dedc54e340567c9f773b183301424` |
| female-base-2.bin.gz | 2,388,965 | `61c90df32afdb1bcff5da60262278beebfe5283729d6d49d48005e0b4ed49799` |
| female-base-3.bin.gz | 2,152,130 | `47667d765348ea054947b216ae4c7b18669103f1f61bc02b238d9723d8dd90ad` |
| female-base-4.bin.gz | 2,170,207 | `964c63442a589089de35d12e67d1b39afa93f6c1fe1b4c931a4f20af16f6c894` |
| female-base-5.bin.gz | 2,233,971 | `8b6d8848a23f6fff5b60e76d902dece22b37aa8bb75f59e0eb4eeedc7ae632b8` |
| female-base-6.bin.gz | 2,392,219 | `242b580fc48aa54a302ec11c56cabf46f5190907caa7f21def0014d17ce0ec30` |
| female-base-7.bin.gz | 2,391,078 | `12a2c1a764b449ad7d7ad2d7ab3cac0a5286c93fcfaaae45b7870d1f43c1f94d` |
| female-base-8.bin.gz | 2,372,384 | `b09da50abe143ccb582dec3be0b22d9b9d3dd87d1c890a2a71583a49928e1783` |
| female-base-9.bin.gz | 2,296,708 | `ea0a89fe9b0d9dfd1e0fc8a21674e864d2b0938ecc40423cf03965c65c1a6a67` |
| female-base-10.bin.gz | 2,298,571 | `e1e8d3897e1a164c810a14f49bf901d4f39ee9f1f52bb775904e2ee606c512e3` |
| female-base-11.bin.gz | 2,302,440 | `24979f2f2a46266b2e06de588b5164d4a5a066182eb2a13c03c58b16663cdaeb` |
| female-base-12.bin.gz | 2,608,638 | `90a09e2d11cff48bfe1b766fe7e90a8682e2c3e3b10098d607207c89e6ceaaad` |
| female-base-13.bin.gz | 2,387,855 | `3f9ac79f7e260a495b3ef425255b007e5f014790cb6d231d32853858a0d6d516` |
| female-base-14.bin.gz | 2,352,106 | `36e5e66cd2e565d06b19e7dec264da9a1cb21c66b4d8a186109405be1bd9d6c1` |
| female-base-15.bin.gz | 177,424 | `1f29d60df0b4b8d56ae1a9f5cf1f875b607f184dc855c8de84d52bfdf6e98277` |
| female-joint-additions-8d95b6b434cd4e04.bin.gz | 9,333 | `4d4de687fbe5c0ba8a843088e32550380e6695bc4f307cee88afc7cd674888c6` |
| female-fit-report.json | 273,385 | `3bd226a86e96ead166ca87ab45bcab4ff80188e5b179c35d47104d0e55d743e5` |

## Install / build
`deploy/atlas/build_atlas.sh` runs `node deploy/atlas/female-study/install_study.mjs <clone>/public/models` (default
`FEMALE_MODEL=study`; `FEMALE_MODEL=hra` builds the old HRA organs-only set instead; `FEMALE=0` skips the female model).
The script needs no network or npm packages and takes under a second. It:
1. checks every source file against `SHA256SUMS.txt`;
2. adds `origin` to every part (`hra-female` for the 64 HRA parts, `bp3d-reshaped` for the 2,181 BodyParts3D parts,
   from the upstream `provenance.source`), normalises ids (`FMA:123` -> `FMA123`, all concept ids uppercase), maps the
   upstream `reproductive` and `mammary` systems to our `reproductive_female`, and checks that the compound concept
   `HRA:VH_F_UTERUS` has the same 10 parts as the old HRA build (it does upstream, so old links keep working);
3. checks integrity (unique ids, every concept draws a part, aligned offsets, every index in range, gzip and raw sizes
   equal the manifest, left ovary on +x);
4. writes `female.json` (+ `.gz`), the 17 `.bin.gz` chunks and their gunzipped `.bin` into the models dir (old
   `female*` files there are removed first), and regenerates `rag/female_study_origin.json` (committed; the API's
   concept id -> origin table).

Chunk names are kept (`/models/female-base-N.bin`, `/models/female-joint-additions-....bin`); the manifest name is ours
(`female.json`), so the viewer's loader and the `/models` path scheme are unchanged. `version` is
`female-study-v3@fb3ca0f`, so browser caches (keyed by version and url) never mix it with the HRA set.

## Measured (install of 2026-11-17)
| | |
|---|---|
| Parts | 2,245 (64 `hra-female`, 2,181 `bp3d-reshaped`) |
| Concepts | 4,248 (as upstream; includes `HRA:VH_F_UTERUS`, `HRA:VH_F_OVARY`, `HRA:VH_F_FALLOPIAN_TUBE`) |
| Triangles | 2,437,148 |
| Chunks | 17 (16 base + joint additions) |
| **Download (gzip chunks)** | **35,138,637 bytes (about 35 MB)**; the HRA organs-only set was 17.0 MB, the male set 33.0 MB |
| Raw chunks | 62,108,560 bytes (shipped for browsers without DecompressionStream) |
| Local QA (2026-11-17) | 18 requests, 35,436,397 bytes transferred for the Female view (manifest + 17 gzip chunks) |
| `female.json` / `.json.gz` | 1,669,471 / 286,526 bytes |
| API sidecar | `rag/female_study_origin.json`: 151 ids `hra-female`, 15 `mixed` (e.g. skeletal system, lower limb), 4,132 `bp3d-reshaped` |

## Honesty (medical app)
- Toggle label "Female (study model)", tooltip and the note under it say: male-derived body reshaped to a female form,
  plus female organs from the Human Reference Atlas, for orientation only.
- Selecting a part in the female model shows "Reshaped from the male model (BodyParts3D), not female anatomy data."
  (or "Female anatomy data from the Human Reference Atlas, fitted into this body.", or "Partly reshaped ...") from
  `parts[].origin`.
- `/api/spatial/resolve?sex=female` returns `origin` (`hra-female`, `bp3d-reshaped`, `mixed`) and never reports a
  reshaped structure as `sex: "female"`; female-only structures (uterus, ovary, uterine tube...) resolve to their HRA
  parts through the sidecar. Answer links (`data/graph/atlas_crosswalk.jsonl` female rows) still need a named reviewer
  in `deploy/atlas/female/id_map.csv`, as before.
- No vulva, clitoris, labia, female urethra or female pelvic-floor muscles (53 male or pelvic-floor parts were dropped
  upstream). Acetabular fit is not established upstream.

## Rollback
`FEMALE_MODEL=hra FEMALE_ARGS=--exclude-allen deploy/atlas/build_atlas.sh` (needs the GLB in `deploy/atlas/female/source/`),
then `FEMALE_MODEL=hra deploy/atlas/push_atlas.sh <ip>`. Revert the UI copy commit too, or the labels will describe the
wrong model.
