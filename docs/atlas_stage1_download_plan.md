# Atlas Stage 1: download plan (nothing downloaded yet)

Date: 2026-11-15. Scope: the data Stage 1 needs from `docs/atlas_coverage_plan.md` (tier-1 "closest model" fallback: child -> nearest modelled parent via part-of, one hop). Checked: HEAD requests only (`curl -sI`), no bodies fetched, nothing installed, nothing committed.

## 1. What is already on disk

- `~/Projects/third_party/human-atlas/public/models/atlas.json` (1.3 MB) holds 3,432 concepts (`id`, `name`, `elements`), 2,234 parts, and no relations. It cannot say part-of vs branch-of. Stage 1 cannot use it for hierarchy.
- The BodyParts3D relation tables are not on disk. `public/ATTRIBUTION.md` says the atlas used the "IS-A and PART-OF concept, element, and inclusion tables from the same archive", but those files were never saved locally. The OBJ mesh archives are not on disk either.
- `data/graph/` in med-rag holds the crosswalk and caches, not a parent table. The `anatomy-relations` worktree has about 2,643 certified relations (BRANCH_OF / part_of), but these come from the project's own extraction, not an official table, and the coverage plan treats them as a separate, certified-quote layer (Option C, 9 usable bridges).

**Verdict: nothing on disk satisfies Stage 1 as an official source.** The official tables are one small download away.

## 2. Candidates (sizes from HEAD `Content-Length`, 2026-11-15)

| # | File | URL | Size | Licence | Provides |
|---|---|---|---|---|---|
| 1 | `partof_inclusion_relation_list.txt` | https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_inclusion_relation_list.txt | 91,241 B (91 KB) | CC BY 4.0 (BodyParts3D) | PART-OF parent/child pairs between organs. This is the part-of table Stage 1 needs. |
| 2 | `isa_inclusion_relation_list.txt` | https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_inclusion_relation_list.txt | 207,664 B (208 KB) | CC BY 4.0 | IS-A parent/child pairs. Useful for "segment of artery" style parents, not part-of. Optional. |
| 3 | `partof_parts_list_e.txt` | https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/partof_parts_list_e.txt | 59,351 B (59 KB) | CC BY 4.0 | Maps 3D organ model IDs (FJ numbers) to names for the PART-OF tree. Needed to join table 1 to the atlas IDs. |
| 4 | `isa_parts_list_e.txt` | https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST/isa_parts_list_e.txt | 128,086 B (128 KB) | CC BY 4.0 | Same mapping for the IS-A tree. Needed only if table 2 is used. |
| 5 | `isa_element_parts.txt` / `partof_element_parts.txt` | same LATEST directory | 1.14 MB / 0.65 MB | CC BY 4.0 | Which atomic ELEMENT meshes make up each compound organ. Not needed for one-hop parent lookup. Skip. |
| 6 | `isa_BP3D_4.0_obj_99.zip` / `partof_BP3D_4.0_obj_99.zip` | same directory | 136 MB / 62 MB (page figures; not re-measured) | CC BY 4.0 | Mesh geometry. The atlas already has this geometry in converted form. Not needed. Do not download. |
| 7 | FMA full OWL, `https://purl.obolibrary.org/obo/fma.owl` (also `http://purl.org/sig/ont/fma.owl`) | purl.obolibrary.org | **208,047,132 B (208 MB)** | `CUSTOM`: the SIG licence at http://sig.biostr.washington.edu/projects/fm/FMA_Release (must be read before any use; not verified here) | Full FMA ontology. Overkill for Stage 1 and the licence needs checking. Not recommended. |

The FMA OWL is larger than the BodyParts3D tables by roughly 700 times. It adds nothing Stage 1 needs, because the atlas's 3,432 concepts are already keyed to BodyParts3D FMA ids.

## 3. Recommendation

**Download candidates 1 and 3 (plus 2 and 4 if the IS-A parents are wanted): about 150 KB for the part-of pair alone, 490 KB for all four.** These are small text files from the same archive the atlas already credits (CC BY 4.0, attribution already in `deploy/atlas/ATTRIBUTION.md`), so no new licence needs to be accepted.

Single recommended download: **`partof_inclusion_relation_list.txt` + `partof_parts_list_e.txt` (about 150 KB total)**. Add the two IS-A files only if the audit shows part-of misses branch-type parents.

Caveats before the "yes":
- Format is not verified. I have not read any body. Column layout and whether the parts list carries FMA ids are unconfirmed. The first build step must check this, and stop if the join to the atlas's FMA ids fails.
- The data-detail pages cited in search results give 1,367 PART-OF inclusion entries and 2,904 IS-A entries. Use those as a row-count check, not a proof.
- No checksum file was published that I could find on the page. Record SHA-256 at download and keep it in the repo's audit notes.
- The LATEST files are dated 2013-05-22 (Last-Modified). BodyParts3D 4.0 is the release the atlas uses, so this matches.

## 4. Commands (prepared, not run)

Run only after the user says yes. Output goes outside the repo so nothing is committed.

```sh
DEST="$HOME/Projects/third_party/bodyparts3d-relations"
mkdir -p "$DEST" && cd "$DEST"
BASE=https://dbarchive.biosciencedbc.jp/data/bodyparts3d/LATEST

curl -fSL --max-time 120 -o partof_inclusion_relation_list.txt "$BASE/partof_inclusion_relation_list.txt"
curl -fSL --max-time 120 -o partof_parts_list_e.txt            "$BASE/partof_parts_list_e.txt"
# optional, only if IS-A parents are wanted:
# curl -fSL --max-time 120 -o isa_inclusion_relation_list.txt "$BASE/isa_inclusion_relation_list.txt"
# curl -fSL --max-time 120 -o isa_parts_list_e.txt            "$BASE/isa_parts_list_e.txt"

# Verify size against the HEAD values in section 2 (91241 and 59351 bytes)
wc -c partof_inclusion_relation_list.txt partof_parts_list_e.txt
# Expect 91241 and 59351. Any other value means a partial or changed file: stop and re-check.

# Record checksums (no published checksum exists to compare against)
shasum -a 256 partof_inclusion_relation_list.txt partof_parts_list_e.txt | tee SHA256SUMS.txt

# Row sanity: about 1,367 PART-OF inclusion entries per the archive data-detail page
wc -l partof_inclusion_relation_list.txt
```

Tell the orchestrator the SHA-256 values once they exist. Nothing here writes to the repo.

## 5. Not required for Stage 1

- The 136 MB and 62 MB mesh archives: the atlas already has the geometry.
- The full FMA OWL (208 MB, CUSTOM licence): not needed for one-hop part-of.
- The element-parts files: needed only for compound-organ membership, not for parent lookup.

## Sources

- BodyParts3D download page, file list and sizes: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/download.html
- BodyParts3D licence: https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html (CC BY 4.0 per `public/ATTRIBUTION.md`)
- FMA OBO page (OWL URL, CUSTOM licence): https://obofoundry.org/ontology/fma.html
- Size and Last-Modified values: HEAD requests on 2026-11-15
