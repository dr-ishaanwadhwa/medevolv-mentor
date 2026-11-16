# PrejudiceNeutrino/human-atlas-enhanced: can MedEvolv use its models or code?

As checked 2026-11-16 via the GitHub API (`gh api`), the repo README, `public/ATTRIBUTION.md`, `LICENSE`, `docs/female-anatomy.md`, `docs/female-enhancements.md`, `docs/core-muscle-source-review.md`, `app/model-registry.ts`, the full file tree (1,096 blobs, not truncated), the 572 KB `atlas-female.json` (read whole) and the first 500 KB and last 22 KB of `atlas-female-reconstructed.json`. Nothing was cloned or downloaded beyond those manifests. Repo: https://github.com/PrejudiceNeutrino/human-atlas-enhanced, live site https://anatomy.neutrino.live. Baselines: [slorksmo comparison](2026-11-16-slorksmo-human-atlas.md) and [female model survey](2026-11-15-female-anatomy-3d-models.md).

## Verdict

Ignore the models; optionally port a few viewer ideas. The male set is the same BodyParts3D 4.0 data we already serve. Its "HRA female reference" is the same HRA VH_F v1.5 assembly we already use (we trimmed it to 606 parts). Its only new model, the "female study model", is a male BodyParts3D body (2,181 of 2,245 meshes) reshaped by hand-tuned morph fields with 64 HRA parts fitted in. The authors label it experimental and review "unresolved". "Enhanced" means mostly application features (Learn, notes, study tools, explode, dissection), not new anatomy data.

## 1. Provenance

| Item | Finding (as checked 2026-11-16) |
|---|---|
| Relationship | A real GitHub fork: `fork: true`, parent and source `ashemag/human-atlas`. The GitHub compare against ashemag/main says diverged, 62 commits ahead, 2 behind. Merge base is 7a383d3 (2026-09-05). Ashemag's last push was 2026-09-06. |
| Author | PrejudiceNeutrino (single author for all fork-only commits). About 5 stars, 0 forks, 1 open issue. |
| Inherited work | Commits before 2026-09-26 are not the owner's. The female study model, breast and knee-ligament additions (PRs #2, #4, #5, 2026-09-06 to 09-07) and a three.js r185 upgrade (#6, 2026-09-10) are by `wiiiimm`, whose fork https://github.com/wiiiimm/human-atlas (MIT) has the same history. These PRs were not seen in the first four commits of ashemag main (only the top of its history was checked). The fork's author adds the viewer and Learn features on top. |
| Activity | Created 2026-09-25. About 58 own commits between 2026-09-26 and 2026-11-12. Last push 2026-11-12T01:50Z ("Integrate final three-subject Exam Cram reviews"). Active in the last 4 days, so far less stale than slorksmo (one day of work, 2026-09-06). |
| Model changes by the fork | None found. The last commit touching `public/models` is wiiiimm's 2026-09-07 (`048fce3`), and `atlas.json` last changed 2026-09-05. The 62 fork-only commits are all app, data, docs and content. |
| Maturity | Its own README says no comprehensive independent scientific audit has been done, and female teaching readiness is gated pending anatomy review. |

## 2. Licences

| Part | Licence (as checked 2026-11-16) |
|---|---|
| Code | MIT. `LICENSE` text still reads "Copyright (c) 2026 ashemag"; the fork adds no holder line. API SPDX `mit`. |
| Male data | BodyParts3D 4.0, DBCLS, CC BY 4.0 (per the page dated 2025-02-27). `ATTRIBUTION.md` notes OBJ headers carry a legacy CC BY-SA 2.1 Japan comment, which it says the current page supersedes. We carry the same ambiguity. |
| HRA female data | Browne and Schlehlein, HRA/HuBMAP, 3D Reference Organ Set for Female v1.5 (2023), CC BY 4.0. DOI https://doi.org/10.48539/HBM352.BTSQ.586. Same dataset we use. |
| Study model | Derived from the two above, so CC BY 4.0 with an adaptation notice. `model-registry.ts` records `CC-BY-4.0`. |
| Non-shipped research data in the repo | `data/anatomy/z-anatomy/` (Z-Anatomy core muscles) is CC BY-SA 4.0, and the Z-Anatomy licence file lists NC components (inner ear CC BY-NC-SA, kidney CC BY-NC). It is "not installed" in either atlas and not in `public/models`. `data/anatomy/cvh5/` is a CC BY 4.0 index (Wu et al. 2015) without geometry. If we ever copy anything under `data/`, do not take the Z-Anatomy files (share-alike). |
| Not licensed | Learn text, study tools, flashcards and the 30+ course gallery figures under `public/images/learn` and `data/learn`. The README calls the figures "supplied" and states no licence for this content. Treat as not reusable. |

No NC or SA term applies to the model chunks themselves. No `LICENSE` file for the data, only `ATTRIBUTION.md`.

## 3. Models

Three manifests ship in `public/models`:

| Manifest | Source | Parts | Ids | Whole body? |
|---|---|---|---|---|
| `atlas.json` | BodyParts3D 4.0 male | 2,234 meshes, 3,432 concepts | part `FJ####`, `conceptId` = FMA (e.g. `FMA59763`). Crosswalk lists 3,432 bp3d-male-4 concepts. | Yes |
| `atlas-female.json` ("HRA female reference", v1.5) | HRA united-female v1.5 | 888 meshes, 1,073 concepts. Systems: nervous 295, skeletal 91, urinary 87, respiratory 70, sensory 67, digestive 61, venous 57, reproductive 38, cardiac 36, arterial 31, integumentary 17, muscular 16, lymphatic 14, pregnancy 8. | part `VH_F_*`; `conceptId` prefixes: UBERON 412, FMA 264, HRA-local 210 (includes about 285 Allen brain `HRA:Allen...` ids per concept list). | No (organs, partial skeleton, 16 muscles) |
| `atlas-female-reconstructed.json` ("Female study model v3", route `/female`) | BodyParts3D male framework plus HRA female parts | 2,245 meshes, 4,248 concepts, 2,437,148 triangles | BP3D parts keep `FJ####` and FMA ids; HRA parts keep source ids and ontology ids (UBERON/FMA/HRA-local). Every part has a `provenance` block (source, sourceId, adaptation). | Yes, but male-derived |

The study model: 2,181 BodyParts3D meshes reshaped by a whole-body morph (stature, torso, thorax, head, nose, a waist refinement of -6.7%, a glute contour). Eight HRA pelvis meshes are affine-fitted to the male hip-bone envelope and replace the male pelvis and sacrum. 38 HRA reproductive meshes are placed by one affine fit on bladder bounds. 16 HRA breast meshes get an artistic contour. 2 HRA knee ligaments are fitted. 53 male or pelvic-floor parts are dropped (no female urethra, levator ani, puborectalis, anal sphincter or perineal muscles). The docs state the morph, breast and glute adjustments are "artistic estimates", not measurements. Acetabular fit is not established.

So the female is a whole-body model only because it borrows 97% of its meshes (2,181 of 2,245) from the male skeleton, muscle, vessels and nerves, morphed. That is the opposite of native female data, and the same issue slorksmo has (male bones on a female body), only more extensive.

## 4. Formats and sizes

All chunk files are `.bin` plus `.bin.gz`, sizes from the git tree (bytes).

| Set | Files | Raw | Gzip |
|---|---|---|---|
| Male | `atlas.json` 1,335,285 + `body-0..14` (15) | 59,546,744 | 32,956,129 (about 33.0 MB) |
| HRA female v1.5 | `atlas-female.json` 572,477 + `female-0..9` (10) | 38,347,208 | 23,616,158 (about 23.6 MB) |
| Female study v3 | `atlas-female-reconstructed.json` 1,612,830 + `female-base-0..15` (16) + `female-joint-additions-8d95b6b434cd4e04.bin(.gz)` 15,528 raw / 9,333 gz + `female-fit-report.json` 273,385 | 62,093,032 + 15,528 | 35,129,304 + 9,333 (about 35.1 MB) |

Total `public/models` is about 255 MB in the repo. The study model does not share chunks with the male set, so a deployment that offers both sexes pays 33 + 35 MB gzip, and about 59 MB if the HRA reference is also kept.

Format is the same ashemag chunk format as ours: `parts[]` with `chunk`, `positions`, `normals`, `indices`, `vertexCount`, `indexCount`, `bounds`; `concepts[]` with `elements`; `chunks[]` with `url`, `bytes`, `gzip`, `gzipBytes`. Extra keys (`provenance`, `reconstruction`, `jointAdditions`, `optimized`) are additive. Chunk URLs are hard-coded as `/models/<name>.bin`, so renames are needed only if we change filenames. `app/model-download.ts` shows a gzip-detection fallback (decode only if the payload starts with 1f 8b), which our viewer may or may not already have.

## 5. Compatibility with our stack

- **Male.** Drop-in, but nothing to gain. Same FMA `conceptId`s, same size. We could not verify byte identity without downloading (the manifest is the same byte length as ashemag's and slorksmo's, 1,335,285).
- **HRA female v1.5.** Same source as ours. Its 888 parts versus our 606 (we dropped Allen brain, which is 285 concepts and about 6.6 MB gzip extra). Ids are the same `VH_F_*` mesh names our `deploy/atlas/female/id_map.csv` already maps, and 678 of 888 conceptIds are already UBERON or FMA. Nothing new unless we wanted the brain and pregnancy parts.
- **Study v3.** Parts keep FMA conceptIds for the 2,181 BP3D meshes, so `?select=FMA...` works for male-derived structures in the female view. Whether the 64 HRA parts carry FMA or UBERON ids depends on the source row, the same split as our `id_map.csv`. We would need to regenerate the crosswalk for `sex: female` rows: most structures would now resolve (via FMA) to a female-body mesh that is really a morphed male mesh. For `/api/spatial/resolve` that is a semantic change, "present in female" would be true for male-origin muscles and bones. A flag is needed to separate native from borrowed (the `provenance.source` field gives it).
- **The fork's own identity layer.** `public/identity/core-crosswalk-v1.json` (2,531,622 B) is a crosswalk with `atlas:concept:######`, `externalId{namespace, value, relation}` (FMA exact for about 3,447 rows in the first MB, "other" for 56), `sourceModelId` and `reviewStatus`. In the first 1 MB: 3,432 `bp3d-male-4` rows, 1,073 `hra-female-v1.5` rows (we have not read those), 71 `female-study-v3` rows, relations exact 4,561 and candidate 15. This is conceptually the same idea as our `atlas_crosswalk.jsonl`. It is not a drop-in, but the model-scoped identity concept (concept versus per-model representation, "no automatic male-to-female geometry fallback") fits our design and is worth reading in `app/identity-*.ts` and `docs/` if we revise the crosswalk.

## 6. What "enhanced" means

Features, not data. The README's "What this fork adds" is a UI and teaching layer, none of which changes the BodyParts3D meshes: UI palettes (Classic, Ignition, Ultraviolet, Iris & Ember, light/dark); Learn for digestive, respiratory and lymphoid systems (articles, exam cram, 111+ MCQs, flashcards, glossary, gallery with label practice, personal notes and highlights in IndexedDB); canonical concept versus representation identity; 8 Regions and 17 Teaching Areas; search and browse with aliases and modelled-piece counts; persistent isolation workspaces; per-structure hide/restore with history; staged anatomical explosion with Play/Pause; "context reveal" for obscured anatomy; Random Anatomy; display controls; motion polish; reduced-motion support. It also ships a large validation harness (`npm run check` and about 70 `test:*` scripts, plus browser smoke tests). The model side adds only the inherited wiiiimm study model.

## 7. Code worth porting (regardless of models)

We have not read our own viewer in this task, so these are candidates to compare against `apps/web`. File sizes are from the tree (all MIT, all Three.js r185 and React):

| Candidate | Files (bytes) | Value for us |
|---|---|---|
| Cursor-centred wheel zoom with a target-plane fallback; respects hidden layers and isolation | `app/viewer-interaction.ts` 4,467, `app/viewer-shortcuts.ts` 2,020, `app/pointer-tap.ts` 770 | Small, self-contained. A nice usability win. |
| Hide/restore per structure plus history | `app/hide-restore.ts` 3,644, `app/visibility.ts` 2,774 | Useful for dissection-style teaching. |
| Context reveal (show surrounding organs ghosted) | `app/context-reveal.ts` 2,922, `app/context-reveal-renderer.ts` 5,413 | Distinctive; check cost on mobile. |
| Staged explode with Play/Pause, camera-safe | `app/explosion-layout.ts` 9,389, `app/explode-playback.ts` 1,283, `app/use-explode-playback.ts` 3,629 | Demo-friendly; the layout code is the useful part. |
| Search with aliases and muscle-group shortcuts (hamstrings 8 meshes, quads 8, calves 8, glutes 6) | `app/anatomy-search.ts` 5,433, `app/anatomy-discovery.ts` 3,364 | Likely relevant to our RAG-to-3D resolve; groups map to FMA ids. |
| Model-safe gzip fetch and size check | `app/model-download.ts` 812 | Tiny; add if we ever see double-decode bugs on static hosts. |
| Identity and registry layer | `app/model-registry.ts` 4,304, `app/identity-contracts.ts` 2,904, `app/identity-index.ts` 6,585 | Design reference for sex-scoped ids. |

Not worth porting: Learn, Notes, Study Tools, Gallery. They are large (hundreds of KB of content with unclear licensing), single-subject course material, and unrelated to our RAG product. The 40 KB `app/page.tsx` and 41 KB `scene.tsx` are monoliths. Performance: the repo shows no new performance work on mesh loading, since it still uses the upstream `optimize-anatomy` pipeline and 15-chunk format, and `compress-models.mjs` is the same gzip step.

## 8. Side-by-side

| | Our live set | slorksmo/Human-Atlas | human-atlas-enhanced |
|---|---|---|---|
| Fork status | n/a | Not a fork (derivative, no parent) | Real fork of ashemag, 62 ahead and 2 behind |
| Activity | n/a | 7 commits, one day (2026-09-06) | About 58 own commits, last 2026-11-12 |
| Code licence | n/a | MIT | MIT (ashemag holder only) |
| Data licence | CC BY 4.0 (BP3D, HRA) | CC BY 4.0 (BP3D, HRA v1.10, Andreassen) | CC BY 4.0 (BP3D, HRA v1.5); Z-Anatomy CC BY-SA in `data/`, not shipped |
| Male | BP3D 4.0, FMA ids, 33 MB gz | Same BP3D 4.0 | Same BP3D 4.0, 33.0 MB gz, 2,234 meshes |
| Female source | HRA VH_F v1.5, organs only | HRA v1.10 + 180 borrowed male bones + 76 donor muscles | (a) HRA v1.5 full, 888 parts, 23.6 MB gz; (b) study model: male BP3D morphed + 64 HRA, 2,245 parts, 35.1 MB gz |
| Female parts | 606 | 1,220 (964 HRA native, 256 borrowed or donor) | 888 (a); 2,245 (b) |
| Native whole-body female? | No (organs) | No (organs first, 21% borrowed) | (a) no; (b) no, 97% male-derived and reshaped |
| Female gz | 17.0 MB | 36.6 MB | 23.6 MB (a); 35.1 MB (b) |
| Female ids | FMA via `id_map.csv` | `HRA:` slugs, `BORROWED:FJ####`, `VHF:` | (a) `VH_F_*` with UBERON/FMA/HRA ids, same as ours; (b) FMA for BP3D, source ids for HRA |
| FMA deep links and crosswalk | Native | Break without remap | (a) same as ours; (b) work, but rows must be flagged native versus borrowed |
| Format | ashemag chunks | Same | Same |
| New anatomy data vs ours | n/a | Yes (v1.10, donor muscles) | None, apart from the male-derived study model |
| Scientific status | Reference data | Author claims only | Author says no audit; study model review unresolved |

## 9. Recommendation

1. **Models: ignore.** Nothing new that is native or validated. The study model would add a whole-body female silhouette, but it is male anatomy reshaped, with an unreviewed pelvis, which is the wrong trade for a medical product unless it is clearly labelled.
2. **Code: port selectively, only if the user wants viewer upgrades.** First choice is cursor-centred zoom, hide/restore and search groups, because they are small, MIT, and independent of the data. Second is explode and context reveal. Any port needs a diff against our viewer first, so a follow-up task should read our `apps/web` viewer plus the six or seven files above (about 50 KB).
3. **Do not import** `data/anatomy/z-anatomy`, Learn content, or gallery images.
4. If the user later wants a whole-body female anyway, see the survey doc for native options (e.g. Z-Anatomy female is CC BY-SA, which has its own consequences) before using this.

## 10. If the user still wants the study model: download list for approval

Source: https://github.com/PrejudiceNeutrino/human-atlas-enhanced/tree/main/public/models (raw URLs `https://raw.githubusercontent.com/PrejudiceNeutrino/human-atlas-enhanced/main/public/models/<file>`).

| File | Bytes |
|---|---|
| `atlas-female-reconstructed.json` | 1,612,830 |
| `female-base-0.bin.gz` to `female-base-15.bin.gz` (16 files) | 35,129,304 total |
| `female-joint-additions-8d95b6b434cd4e04.bin.gz` | 9,333 |
| `female-fit-report.json` (optional, provenance) | 273,385 |
| Total | about 36.75 MB (37.02 MB with the report) |

Skip all `.bin` raw (62.1 MB), all `body-*`, `atlas.json`, `atlas-female.json` and `female-0..9`. Verify each chunk against `chunks[].gzipBytes`, and add a SHA-256 for each file to our provenance doc, since the repo has no checksums for the models.

Migration sketch:
1. Stage under a git-ignored `deploy/atlas/female-study/`, keeping the current female set for rollback.
2. Rename to `female-study.json` and `female-study-N.bin(.gz)` (rewrite `chunks[].url`).
3. Build a `native|borrowed` flag from `provenance.source` ("BodyParts3D 4.0" versus HRA). Make the crosswalk and `/api/spatial/resolve` return `borrowed: true` for female rows backed by BP3D meshes. Only HRA-origin rows may be shown as female-specific.
4. Add the system `mammary` and any new ids to `apps/web/src/lib/anatomy.ts`. Extend `validate_female.mjs`, which assumes 606 parts.
5. Add an in-viewer "experimental study model, male-derived" label, and an opt-in switch (default stays our HRA organs-only female).
6. Attribution: add Wiiiimm/ashemag adaptation notes and the adaptation paragraph from `ATTRIBUTION.md` (CC BY 4.0, BP3D and HRA).
7. QA: five female-only structures (uterus, ovary, uterine tube, vagina, cervix) via `/api/spatial/resolve`; `?select=` for male and `&sex=female`; mobile load at 35 MB; left/right check.
8. Deploy via `push_atlas.sh` after checking free disk (adds 35 MB). Rollback is restoring the old files.

## Summary (10 lines)

1. Real fork of ashemag/human-atlas, 62 commits ahead and 2 behind; last push 2026-11-12, single author (PrejudiceNeutrino) on about 58 own commits.
2. Code is MIT (holder line still ashemag); anatomy data is CC BY 4.0 (BodyParts3D 4.0, HRA v1.5), with no NC or SA on the shipped models.
3. The repo's `data/anatomy/z-anatomy` is CC BY-SA 4.0 with NC components and is not shipped; avoid copying it.
4. The fork changed no model files. Its last `public/models` commit is wiiiimm's 2026-09-07, which it inherited.
5. Male is the same BodyParts3D set as ours (2,234 meshes, FMA ids, 33.0 MB gz). Its HRA female v1.5 (888 parts, 23.6 MB gz) is our source set, untrimmed.
6. The "female study model" has 2,245 parts and 35.1 MB gz, but 2,181 are male BodyParts3D meshes reshaped by hand-tuned morphs. The author calls it experimental, and its review status is unresolved.
7. "Enhanced" means application features: Learn, notes, study tools, hide/restore, staged explode, context reveal, search and identity layer. It adds no new data.
8. Format matches ours, so loading is easy; FMA ids on BP3D parts keep deep links working, but a native versus borrowed flag would be needed in the crosswalk.
9. Recommendation: ignore the models; optionally port small viewer pieces (cursor zoom, hide/restore, search groups, explode), after a diff against `apps/web`.
10. If the study model is wanted anyway: `atlas-female-reconstructed.json` (1.61 MB), `female-base-0..15.bin.gz` (35.13 MB), the joint-additions gz (9 KB), about 36.75 MB in total, needing your approval first.
