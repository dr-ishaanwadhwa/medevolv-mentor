# Female 3D anatomy for the MedEvolv atlas: candidate models and plan

Researched 2026-11-15. Every claim is "as checked 2026-11-15" unless a different date is given. Items I could not verify are marked UNVERIFIED.

## 1. Bottom line

- Best option: **HRA "3D Reference Organ Set for United, Female" v1.5** (Visible Human Female, VH_F), CC BY 4.0. It is the only candidate that is whole-body-ish, segmented per structure, has ontology ids, has female-specific anatomy and carries a licence that allows a public web app.
- It is NOT a full female twin of BodyParts3D. Skeleton and muscle are partial (no skull, ribs, arm bones or named skeletal muscles found in the node list), but it adds a full brain atlas, vessels, GI tract, organs and the female reproductive tract.
- Recommended product: a **"Male / Female" switch** where Male = current BodyParts3D, Female = HRA VH_F. Do not mix them in one scene (different subjects, scales, poses).
- Strong finding: `human-atlas` already shipped exactly this female set in earlier revisions (see 3.1), and `scripts/optimize-anatomy.mjs` still contains a `female` branch. Our pinned commit (1c38bf3) has the data removed, but the path is proven. The old build recorded 888 meshes and 1,073 nodes, which matches my GLB inspection exactly.

## 2. What a model must provide (from the local pipeline)

- Checked locally: `/Users/ishaanwadhwa/Projects/third_party/human-atlas` and `/Users/ishaanwadhwa/Projects/med-rag/deploy/atlas/`.
- `public/models/atlas.json` has `parts[]` and `concepts[]`. Each part carries `id`, `name`, `conceptId` (FMA...), `system`, `chunk`, byte offsets for `positions` (float32 xyz), `normals` (int16 x3) and `indices` (uint32), `vertexCount`, `indexCount` and `bounds`. Concepts are `{id, name, elements[]}`. There are also `chunks[]` (urls and byte sizes), `triangles`, `sex`, `source`, `scope` and `version`.
- Current male build: 2,234 parts, 3,432 concepts, 2,288,268 triangles, 15 chunks `body-N.bin(.gz)`, about 33 MB gzip (about 90 MB raw in `public/models`).
- Pipeline: `convert-anatomy.py` (OBJ to bin; mm/Z-up to m/Y-up), then `optimize-anatomy.mjs` (meshoptimizer, 0.2% relative error per structure, repacks to `body-N.bin`), then `compress-models.mjs` (gzip).
- `optimize-anatomy.mjs` takes the manifest name as argv. If the name contains "female" it writes `female-N.bin` and first welds coincident vertices and averages normals. This is needed because HRA GLB exports duplicate vertices.
- Our deep links use FMA ids (`?select=FMA19667`, `?system=`). `deploy/atlas/deep-link.patch` ranks concept names/ids. The crosswalk (`data/graph/atlas_crosswalk.jsonl`) maps mentor structures to FMA ids.
- A usable model therefore needs: per-structure meshes, a stable name per mesh, and an id (FMA ideal, UBERON mappable) for the crosswalk.

## 3. Candidates

### 3.1 HRA 3D Reference Organ Library, VH_F united set (RECOMMENDED)

- Sources:
  - Metadata: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/graph.json
  - Landing: https://lod.humanatlas.io/ref-organ/united-female/v1.5
  - GLB: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb
  - Repo: https://github.com/hubmapconsortium/ccf-3d-reference-object-library (folders VH_Female, VH_Male, Androgenous, NodeLists; female file `VH_Female/V1.2/VH_F_United.glb`; the repo is the older V1.x line)
  - Our historical record: DOI https://doi.org/10.48539/HBM352.BTSQ.586 (cited in our `deploy/atlas/ATTRIBUTION.md`)
- Licence: CC BY 4.0. Confirmed in graph.json (`license: https://creativecommons.org/licenses/by/4.0/`), on the GitHub repo and on NIH 3D organ entries (for example Left Ovary 3DPX-020979). NIH 3D says the brain moved to CC BY 4.0 in v1.3.
- Creators: Kristen Browne, Heidi Schlehlein (medical illustrators), HuBMAP / Human Reference Atlas. Source data is the NLM Visible Human Female, with the Allen Institute brain atlas (nodes prefixed `Allen_`).
- Format and size (HEAD request, 2026-11-15): single GLB, 211,624,968 bytes (about 202 MB), last-modified 2026-06-10. The male twin is 153,596,592 bytes.
- Structure of the GLB (read the JSON chunk with a 1 MB range request; no large download):
  - Authoring tool: Babylon.js exporter for Maya 2023.2. glTF 2.0, 1,073 nodes, 888 mesh nodes, 92 materials.
  - 606 non-brain meshes and 282 `Allen_*` brain meshes.
  - About 5.56 M triangles and 5.47 M vertices before welding, of which 0.65 M triangles are the brain. That is about 2.4 times the male atlas.
  - Names are `VH_F_<name>`, with `_L`/`_R` suffixes and a node hierarchy (for example `VH_F_integumentary_system`, `VH_F_skin`, `VH_F_mammary_gland_L`).
- Ontology: the dataset graph labels each organ with an UBERON or FMA id (`representation_of`), for example UBERON:0013754 (integumentary system), UBERON:0002097 (skin), FMA:57991 (mammary gland). The graph.json for the united set has only 20 top-level records (skin and breast parts). Per-organ datasets, such as `ref-organ/ovary-female-left/v1.1` (linked from NIH 3D), carry the ids for the other organs. **Per-mesh FMA ids inside the united GLB are not provided; only names.** So the name-to-FMA/UBERON mapping must be built (see 5).
- Sex: female, a single subject (VH_F). `organ_owner_sex: Female`. Bounding box about 967 x 1666 x 329 mm in the metadata.
- Female-specific coverage (verified from node names): vagina, cervix, cervicovaginal junction, internal and external cervical os, body, fundus, anterior/posterior wall and lower segment of uterus, both ovaries, fallopian tubes with ampulla/isthmus/infundibulum/fimbriae, broad, round, cardinal, uterosacral, ovarian and suspensory ligaments, mesovarium, uterovesical pouch, uterine arteries and veins, plus breast (gland, lobes, ducts, sinuses, areola, nipple, suspensory ligaments, fat) and placenta/umbilical items (8 in total, which human-atlas hid by default). No vulva/clitoris/labia nodes found.
- Other coverage: skin, heart with chambers, valves and coronary vessels, lungs with bronchopulmonary segments, bronchial tree, liver (Couinaud segments, ducts), gallbladder, pancreas, spleen, kidneys, ureters, bladder, GI tract, aorta and large vessels, spinal cord segments, eyes (many sub-structures), larynx cartilages, thymus, thyroid cartilage, knee ligaments, pelvic bones and femur/tibia/fibula/patella, vertebrae (25 named), sacrum, coccyx.
- Gaps (honest): I found no skull, mandible, ribs, sternum, clavicle, scapula, humerus, radius, ulna, hand or foot bones, and only about 20 "muscle" names (eye, heart, bladder). Skeleton and muscle coverage is partial. This matches the note already in our `ATTRIBUTION.md`.
- Conversion difficulty: moderate, because it is GLB with meshes not OBJ-per-FMA, and because of mesh duplication and size. The `female` branch of `optimize-anatomy.mjs` exists. Earlier human-atlas revisions did it, producing a manifest with 888 parts.
- NIH 3D (https://3d.nih.gov/collections/40) hosts the same library per organ as separate downloads, CC BY 4.0 on the entries I opened. The collection page itself lists no count or formats. Useful for per-organ updates, but the united GLB is simpler.

### 3.2 Z-Anatomy

- Sources: https://www.z-anatomy.com, https://github.com/LluisV/Z-Anatomy (Unity app project), .blend files on Google Drive per its page.
- Licence: conflicting on 2026-11-15. The repo page says CC BY-SA 4.0. A raw LICENSE link on the `Mobile-Version` branch is GPL-3.0 (that is for the app code). A 2021 forum post claims restrictive terms inherited from BodyParts3D, which looks outdated. Treat the model licence as CC BY-SA 4.0, but UNVERIFIED in detail.
- Base: derived from BodyParts3D (male base) and reworked by the Open 3D Model Project (about 70% of shapes modified, per a secondary source).
- Female reproductive anatomy: I found no source confirming it. UNVERIFIED. I did not open the .blend, so I cannot say what is in it.
- Format: Blender and FBX. Conversion would need Blender export, naming cleanup and TA2 or FMA ids that the page does not list.
- Verdict: share-alike and unclear female content make it a poor primary candidate. It could be worth a manual check for a better male-and-female skeleton or muscle set. Not recommended now.

### 3.3 BodyParts3D itself

- https://dbarchive.biosciencedbc.jp/en/bodyparts3d/ (licence page updated 2025/02/27: CC BY 4.0).
- The README (2011 release) and licence page do not mention sex. Our `ATTRIBUTION.md` says it is an adult male reference. I found no female BodyParts3D set (web search 2026-11-15 found none). Reproductive organs in it are male; our README already says the atlas has no uterus.
- Verdict: not a female source.

### 3.4 Visible Korean (Dongguk / Ajou)

- https://sites.google.com/dongguk.ac.kr/anatomy/ lists a female whole-body surface model (PDF, 229 MB), a female pelvis surface model (20 MB), female sectioned images (970 MB reduced) and NIfTI volumes.
- No licence stated on the page. KISTI repository items show the Korea Open Government License on at least one record (fetched via search, not confirmed for this dataset). The 3D PDF format is not directly convertible, and per-structure naming and ids are not provided.
- Verdict: not suitable (licence unclear, PDF-only, no ontology ids). Contact the owners only if HRA falls through.

### 3.5 Open Anatomy Project / AnatomyTOOL / others

- Open Anatomy (https://www.openanatomy.org/about.html): aims at free atlases, but states no specific licence or female model on the About page. UNVERIFIED. The brain and abdomen atlases are not whole-body female.
- AnatomyTOOL (https://anatomytool.org) hosts the Open 3D Model Project; the page fetch failed on 2026-11-15 (expired certificate), so licence and female content are UNVERIFIED. Per-item licences vary.
- Commercial female models (Complete Anatomy, CGTrader, Sketchfab marketplace sets) are not open for redistribution. I did not evaluate individual Sketchfab CC-BY listings; none seen is a segmented, ontology-tagged whole-body female set.
- IT'IS Yoon-sun (Visible Korean female) exists but its download licence is not stated in the results I saw, and the IT'IS Virtual Population is generally licensed commercially. Not usable.

### 3.6 Comparison

| Candidate | Licence | Female? | Per-structure | Ids | Fit |
|---|---|---|---|---|---|
| HRA VH_F united v1.5 | CC BY 4.0 | yes, full reproductive + breast | 888 meshes / 1,073 nodes | UBERON/FMA at organ level, names per mesh | Best |
| Z-Anatomy | CC BY-SA 4.0 (UNVERIFIED) | UNVERIFIED | yes | unclear | Poor |
| BodyParts3D | CC BY 4.0 | no (male) | 2,234 | FMA | Already used |
| Visible Korean | not stated | yes (PDF) | PDF | none | No |
| Open Anatomy / AnatomyTOOL | not verified | no/unknown | unknown | unknown | No |

## 4. Licence obligations

CC BY 4.0 for HRA VH_F:
- Credit the creators, give the title, version, source link and licence link, and indicate changes. Use the text below. Put it in the About sheet, in `dist/ATTRIBUTION.md`, and in the footer credit line (as already done for BodyParts3D).
- Suggested attribution (adapted from the entry already in our `ATTRIBUTION.md`): "Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, 3D Reference Organ Set for United, Female, v1.5. CC BY 4.0. https://doi.org/10.48539/HBM352.BTSQ.586 . Source geometry: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb . Adapted: re-centered, vertex-welded, simplified, re-packed, colors and system groupings added." Also credit the underlying data (NLM Visible Human Project; Allen Institute brain atlas) as the HRA metadata does. Check the exact required credit on the DOI page before shipping; I did not open it.
- No share-alike. Nothing here forces our site or code under CC BY. BodyParts3D is also CC BY 4.0. Combined CC BY datasets are fine in one app, and each keeps its own notice.
- Do not imply endorsement by HuBMAP, NIH or DBCLS.

If Z-Anatomy were used (CC BY-SA 4.0): adapted model files must be shared under the same licence. The app code would likely stay separate, but this is a legal question and I did not analyse it.

## 5. Conversion plan (HRA GLB to human-atlas chunk format)

Environment note: the source GLB is about 202 MB. Download it once to the build machine (not into the repo). I did NOT download it in this research.

1. Fetch the GLB to `~/Projects/third_party/hra-vhf/` and record its sha256 plus the commit/version in the attribution file.
2. Convert GLB to the intermediate manifest `female.json` plus an initial `female-N.bin`: write `scripts/convert-glb.mjs` or `.py` using `@gltf-transform/core` (Node) or `trimesh`/`pygltflib` (Python).
   - For each mesh node, bake the node hierarchy transform to world space; pick the node name as `name` (strip `VH_F_`, replace `_` with space; keep `_L`/`_R` as Left/Right).
   - Source units: meters, Y-up per the optimize script's comment about "native meter/Y-up coordinates". Then translate so the feet rest on the stage, as the male conversion does (the male converter shifts by `+.0781112` in Y and `-.1` in Z; recompute for the female bounds).
   - Write positions float32, normals int16, indices uint32, `bounds`, `vertexCount`, `indexCount`, using the same `parts[]` record layout and `chunks[]` list.
   - Set `sex: "female"`, `source: "HRA VH_F united v1.5"`, `scope: ...`, `version`.
3. Build ids. Create a CSV `mesh name -> id` with `conceptId` and `conceptName`:
   - First pass: automatic match of names against BodyParts3D FMA names (exact, then the variants function already in `rag.atlas.variants`), and against the UBERON/FMA labels in the per-organ HRA datasets (for example `ref-organ/ovary-female-left/v1.1`).
   - Second pass: curate by hand the remaining items that matter (uterus parts, ovary, tube, vagina, breast, ligaments). Estimate: about 100 female-specific and major organ names; brain `Allen_*` names map to the Allen ontology, not FMA, and can use FMA only where a direct name match exists.
   - Where there is no FMA id, keep a synthetic `HRA:<node-name>` or `UBERON:<id>` concept id. The deep link patch already ranks by name and id, so UBERON/HRA ids work with a small change to the `?select=` matcher.
4. Assign `system` per part using the node hierarchy (`VH_F_<system>` parents such as integumentary, circulatory, digestive) plus a hand-written mapping to the 15 display systems. Add a "Reproductive (female)" system and a "Pregnancy reference" system for placenta items, hidden by default as before.
5. Run `node scripts/optimize-anatomy.mjs female.json`. The `female` branch welds coincident vertices and averages normals, then simplifies at the 0.2% error. Run `node scripts/compress-models.mjs` to produce `female-N.bin.gz`.
6. Validate with `scripts/validate-atlas.mjs` (mesh buffers, names, concept membership). Visually QA in the viewer.
7. Add `ATTRIBUTION.md` text, the `deep-link.patch` changes (below), then rebuild with `deploy/atlas/build_atlas.sh`. Add the female files to `public/models/` and push with `push_atlas.sh`.

Effort: roughly 1 to 2 days for the converter and QA, plus 1 day for id curation. The original author did the conversion once already (888 parts).

## 6. UI

- Header toggle "Male | Female" (also `?sex=female|male`, default male). Persist in `localStorage`; deep links keep working without a `sex` param.
- Implementation in the viewer: `atlas.json` and `female.json` are separate manifests loaded on demand, only one resident at a time. The switch disposes the current scene's buffers, then loads the other model. Selection state resets (keep the selected concept id if it exists in the target model).
- Label and click mapping to mentor pages: the crosswalk is keyed by FMA id. For structures present in both models and mapped to the same FMA id, nothing changes. For female-only structures (uterus, ovary, tube, vagina, breast), add rows to `atlas_crosswalk.jsonl` with `sex: "female"`, and have `?select=` take effect only in the model where it matches. If `?select=` targets a female-only structure while the male model is loaded, auto-switch to Female.
- Mentor side: pages about uterus, ovary, cervix, breast, pregnancy can now get a 3D link (our README says these currently get no link by design). Keep the existing behaviour for everything else.
- Show a small note under the toggle: "Female model: Visible Human Female reference organs; skeleton and muscles are partial."

## 7. Size budget

- Estimated, not measured: the HRA scene has about 5.56 M source triangles (about 5.47 M vertices before welding). After welding and 0.2% simplification, the last time this ran, human-atlas shipped it alongside the male model. I did not find recorded sizes. Expect the female chunks to land near the male's 20 to 40 MB gzip.
- Plan for about 30 MB gzip for female, loaded only when the user picks Female. Combined with the male's 33 MB, `dist/` goes from about 108 MB to about 140 MB on the OCI VM. Measure after the first conversion.
- Reduce further if needed: drop the 282 Allen brain parts (0.65 M source triangles) behind a "Brain detail" option, or use a stricter simplification error for small parts.

## 8. Caveats

- Different subjects: the male is a Japanese MRI-based reference (TARO); the female is the NLM Visible Human Female cadaver. Proportions, pose and scale differ, so side-by-side or morphing views are not valid. Do not overlay them.
- Not a mirror of the male: the female has no skull or most bones, no hands, feet or ribs, and almost no skeletal muscle, so "same systems, female version" will not hold for skeletal and muscular systems. Say so in the UI.
- Single-subject, cadaver-derived (the Visible Human dataset is of a specific donor). Anatomy variation is not represented.
- Names come from HRA node labels, not FMA; some are non-standard (for example `jejenum`, `eigth thoracic spinal cord segment`, duplicate `gallbladder_`). Clean them when generating display names.
- GLB metadata for the united set lists only 20 records, so ids at mesh level need our own mapping, with some error risk. Spot-check the clinically important structures.
- The male and female models have different coordinate frames (the HRA placement metadata uses a -90 degree X rotation and millimetre units). Check axes before baking transforms.
- My inspection read only the GLB header and JSON chunk (about 0.8 MB). I did not render the model, so visual quality, mesh integrity and normals are unchecked.
- Licence details for Z-Anatomy, Open Anatomy, AnatomyTOOL and Visible Korean are UNVERIFIED. HRA's licence was confirmed on 2026-11-15 in three places (graph.json, GitHub repo, NIH 3D entry).

## 9. Sources (all visited 2026-11-15)

- https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/graph.json
- https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb (HEAD plus 1 MB range read)
- https://github.com/hubmapconsortium/ccf-3d-reference-object-library
- https://3d.nih.gov/collections/40 and https://3d.nih.gov/entries/3DPX-020979
- https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html and the 2011 README
- https://github.com/LluisV/Z-Anatomy and its Mobile-Version LICENSE page
- https://www.openanatomy.org/about.html
- https://sites.google.com/dongguk.ac.kr/anatomy/
- Local: `third_party/human-atlas` (README, `scripts/*`, `public/models/atlas.json`, `public/ATTRIBUTION.md`) and `med-rag/deploy/atlas/*`
