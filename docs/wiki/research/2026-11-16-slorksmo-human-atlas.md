# slorksmo/Human-Atlas: can MedEvolv switch its male and female 3D models to it?

As checked 2026-11-16 (GitHub API plus raw README, LICENSE, ATTRIBUTION.md and the `atlas-female.json` manifest; nothing cloned, no model files downloaded; the male `atlas.json` was only range-read, first 400 KB). Repo: https://github.com/slorksmo/Human-Atlas, live site https://atlas.taim.best.

## Verdict

Keep the current male set: the repo's male model is the same BodyParts3D 4.0 data we already serve. Do not switch the female set wholesale. It is about double our size, is keyed by `HRA:` slugs with no FMA or UBERON ids (our deep links and crosswalk are FMA-keyed), and about 15% of its parts are male bones placed on a female body. If the user still wants it, do a female-only, opt-in switch (plan in section 5).

## 1. What the repo is

| Item | Finding (as checked 2026-11-16) |
|---|---|
| Relationship | Not a GitHub fork (API `fork: false`, no parent). It is a derivative of https://github.com/ashemag/human-atlas: same file layout (`app/anatomy.ts`, `scripts/optimize-anatomy.mjs`, `public/models/atlas.json`, `body-N.bin(.gz)`), and the LICENSE still reads "Copyright (c) 2026 ashemag". Created 2026-09-06, a day after ashemag's 2026-09-05 work. |
| Activity | 7 commits, all 2026-09-06 (last 2026-09-06T20:52Z, "fixed commit"). Last metadata update 2026-11-14. 18 stars, 12 forks. Effectively a one-day build and not maintained since. |
| Delta vs upstream | Adds a female body, an Arabic UI with right-to-left layout, Wikidata Arabic terms, and a deployment (atlas.taim.best). Male `atlas.json` is byte-length identical to ashemag's (1,335,285 B) but the git blob differs, and the `body-0.bin.gz` blobs differ (2,283,403 B vs 2,257,262 B), so the male chunks were re-optimised. Content-level equality was not checked (would need downloads). |
| Code licence | MIT (`LICENSE`, SPDX `mit`). |
| Data licence | Not MIT. The README says the anatomy data is CC BY 4.0 and that attribution must travel with it. `public/ATTRIBUTION.md` has the full credit text. |
| Male source | BodyParts3D 4.0 (DBCLS), CC BY 4.0, https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html. The repo notes the OBJ files carry a legacy CC BY-SA 2.1 Japan comment that it considers superseded by the current licence page (updated 2025-02-27). This is an ambiguity to be aware of, and we already carry the same data. |
| Female source | HRA "3D Reference Organ Set for Female" v1.10 (Browne and Schlehlein, HuBMAP, CC BY 4.0), built on the Visible Human Dataset (NLM). Eight pelvic meshes are carried over from v1.5. The cited DOI 10.48539/HBM637.DWBM.744 is stated in the repo as "not yet resolving". |
| Extra female sources | (a) 76 lower-limb muscles from Andreassen et al. 2023, Sci Data 10:34, CC BY 4.0 (a different woman, rigidly fitted to the HRA bones). (b) 180 bones copied from BodyParts3D male and fitted onto the female body (skull, ribs, shoulder girdle, arms, feet). |
| Attribution duties | CC BY 4.0 for BodyParts3D, HRA, and Andreassen. We must credit each creator, link the licence, and say the data was adapted. We already do this for BodyParts3D and HRA (`deploy/atlas/ATTRIBUTION.md`). Andreassen would be new. No non-commercial or share-alike term applies to the data (apart from the legacy BP3D comment noted above). |

## 2. The models

| | Male (`atlas.json`) | Female (`atlas-female.json`) |
|---|---|---|
| Chunks | `body-0..14.bin(.gz)`, 15 files | `female-0..14.bin(.gz)`, 15 files |
| Raw / gzip | 59,546,744 B / 33,466,685 B (about 33.5 MB gzip) | 58,754,248 B / 36,573,226 B (about 36.6 MB gzip) |
| Manifest | `atlas.json` 1,335,285 B | `atlas-female.json` 623,120 B |
| Parts | 2,234 meshes, 3,432 concepts, 15 systems | 1,220 meshes (964 HRA + 180 borrowed male bone + 76 donor muscle), 1,439 named concepts per README, 18 systems |
| Triangles | 2,288,268 | 2,765,488 (from 7,786,935 source) |
| Ids | Part id `FJ####`, `conceptId` = FMA (for example `FMA59763`). Same as ours. | Part id `HRAF####` (`BM####` borrowed, `VHF####` donor). `conceptId` is `HRA:<slug>`, `BORROWED:FJ####` or `VHF:<name>`. No FMA and no UBERON. |
| Coverage | Whole body, every BodyParts3D system | Skin and body surface, 283 Allen-atlas brain regions, 87 kidney parts, digestive, respiratory, vascular, reproductive (38), urinary. Native skeleton is only 65 meshes (vertebrae, sternum, pelvis, knee). Native muscle is 16 (eye and knee). Everything else is the borrowed or donor layers, off by default. So the female is organs-first, not whole-body. |
| Pose and scale | Both are re-based to metres, Y-up, resting on the stage; female skin spans y 0 to 1.658 m. Male and female are separate manifests with separate id spaces, so nothing is shared or aligned between them. | |

## 3. Compatibility with our pipeline

- **Viewer format.** Same manifest and chunk shape as ashemag's viewer and ours: `parts[]` with `chunk`, `positions`, `normals`, `indices` byte offsets, `bounds`, plus `concepts[]` and `chunks[]` with `url`, `gzip` and `gzipBytes`. Our own female build (`deploy/atlas/female/`) already produces that format with the same upstream `optimize-anatomy.mjs`. Extra keys (`sex`, `borrowed`, `donorMuscle`, `optimized`) are additive. Chunk URLs are hard-coded as `/models/female-N.bin`; we serve `female.json` and `female-N.bin`, so only the manifest filename and the system ids would differ.
- **Male switch.** Nothing to gain. Same BodyParts3D 4.0, same ids, same size as our male set (about 33 MB).
- **Female system ids differ from ours.** Their systems include `brain`, `connective`, `borrowed`, `donor-muscle`, `reproductive`. Ours (`apps/web/src/lib/anatomy.ts`) use `reproductive_female`, and our build has 606 parts and no borrowed layers. The `apps/web/src/lib/anatomy.ts` system table and colours would need new entries.
- **What breaks.**
  - `?select=FMA…` deep links for female-only structures: their parts carry `HRA:` slugs, so there is nothing to match an FMA or UBERON id against.
  - `data/graph/atlas_crosswalk.jsonl` and `rag/atlas.py` rows with `sex: female`, and `/api/spatial/resolve` for those rows.
  - Our hand-reviewed `deploy/atlas/female/id_map.csv` maps the older HRA v1.5 mesh names (`VH_F_skin`) to FMA, UBERON or HRA ids. Their v1.10 names are cleaned and differently cased (for example "Subcutaneous abdominal adipose tissue RUQ area"), so the map would have to be rebuilt by matching on the slug.
- **Remap approach.** Build `HRA:slug -> FMA/UBERON` by joining on lowercased slug against our existing `id_map.csv` (mesh name to concept). Review the misses by hand, as we did for v1.5. Keep `BORROWED:FJ####` and `VHF:` rows out of the crosswalk, since male-bone links would be wrong for a female body.
- **Size.** Female 36.6 MB gzip vs our 17.0 MB (organs-only, with Allen brain excluded) or 23.6 MB (with brain). That is a 55 to 115% increase on the lazy-loaded female payload. Ask whether the female chunks are lazy-loaded before accepting this.

## 4. Risks

1. **Maintenance.** One-day project, no commits since 2026-09-06. A single maintainer's derived data must be treated as a frozen snapshot, not a dependency.
2. **Provenance.** Chain is BodyParts3D, HRA v1.10, and Andreassen via one person's fitting scripts. Placement accuracy is the author's own claim (bone agreement 17 to 36 mm, anchor errors up to 25 mm); we would have no independent check.
3. **Mixed-person anatomy.** 180 male bones and 76 muscles from a second woman are shown on a woman's body. The repo defaults them off and labels them as a placeholder. For a medical-education product this misleads unless the UI says so, and a clinician could see a male skull on a female figure.
4. **Licence.** CC BY 4.0 across all three data sources, no non-commercial or share-alike term. Residual ambiguity is the legacy BP3D CC BY-SA comment, which we already carry. The unresolved HRA DOI weakens the citation.
5. **Loss of ontology links.** HRA slugs replace FMA and UBERON ids, so we lose the join to our graph.
6. **Untested here.** We did not load their binaries or view the render, so quality and exact pose match are unverified.

## 5. Migration plan (female only, if approved)

1. **Approval and fetch.** User approves downloading `public/models/atlas-female.json` (623,120 B) and `female-0..14.bin.gz` (36,573,226 B gzip total) from https://github.com/slorksmo/Human-Atlas/tree/main/public/models. Verify sizes against `chunks[].gzipBytes`. Skip the `.bin` raw files (58.8 MB) and skip every `body-*` and `atlas.json` file.
2. **Stage.** Put the files in a git-ignored folder `deploy/atlas/female-v110/`. Keep the current female files untouched for rollback.
3. **Id remap.** Write `deploy/atlas/female-v110/id_remap.py`: join `conceptId` slugs to `deploy/atlas/female/id_map.csv`; output FMA or UBERON where known and keep `HRA:` otherwise; flag `BORROWED:*` and `VHF:*` as no-crosswalk. Hand-review the unmapped.
4. **Manifest rewrite.** Rewrite `conceptId` and system ids to match `apps/web/src/lib/anatomy.ts` (`reproductive` to `reproductive_female`). Decide whether to drop the `borrowed` and `donor-muscle` systems (recommended: drop, to avoid male bones on the female).
5. **Rename.** Output `female.json` and `female-N.bin(.gz)` per `deploy/atlas/female/README.md` (our file names). Run `deploy/atlas/female/validate_female.mjs`, and extend its counts for 1,220 or the trimmed set.
6. **Repo files touched.** `apps/web/src/lib/anatomy.ts` (system entries and colours), `apps/web/src/components/canvas/*` (only if system ids are consumed there), `data/graph/atlas_crosswalk.jsonl` and `rag/atlas.py` (regenerate `sex: female` rows), `deploy/atlas/ATTRIBUTION.md` (add Andreassen et al. only if the donor muscles are kept; update HRA to v1.10), `deploy/atlas/female/README.md`.
7. **QA.** Every crosswalk female id resolves in the new manifest; `/api/spatial/resolve` for five female-only structures (uterus, ovary, uterine tube, vagina, cervix); `?select=` deep links for male and female (`&sex=female`); load time on mobile throttle; visual check of left/right and orientation; attribution page renders.
8. **Deploy.** Via `push_atlas.sh` (`rsync --delete` of `dist/`, so the files must be in the build). Check free disk on the VM first.
9. **Rollback.** Restore the previous `female.json` and `female-N.bin(.gz)` from the retained folder and redeploy; crosswalk rows revert with git.

## Summary (for approval)

1. Not a GitHub fork. It is an unmaintained one-day derivative of ashemag/human-atlas (last commit 2026-09-06), with MIT code and CC BY 4.0 data.
2. The male model is BodyParts3D 4.0, the same source and ids as ours. A switch gains nothing, so keep ours.
3. The female model is HRA v1.10 (CC BY 4.0), 1,220 parts, with 36.6 MB gzip in 15 chunks plus a 623 KB manifest.
4. About 21% of those parts are not original HRA: 180 male bones and 76 donor leg muscles from another woman.
5. Its ids are `HRAF####` with `HRA:` slugs, no FMA or UBERON, so our FMA deep links, crosswalk and `/api/spatial/resolve` break without a remap.
6. It is roughly double our current female payload (17 to 24 MB gzip).
7. The format is the same as ours, so the viewer can load it with only renames and system-id edits.
8. Licence needs no share-alike or non-commercial handling; attribution to Andreassen would be new.
9. Recommendation: keep current for both. If the user wants it, switch female only, drop the borrowed layers, and follow the plan above.
10. A download would be `atlas-female.json` (623,120 B) plus `female-0..14.bin.gz` (36,573,226 B), about 37 MB, from https://github.com/slorksmo/Human-Atlas/tree/main/public/models. Needs approval.
