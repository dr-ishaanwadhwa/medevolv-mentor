# Handoff Report — Explorer Survey 2: Graph Networking Pipeline Update & Metrics

## 1. Observation

### 1.1 Codebase Structure and File Locations
The investigation examined the following key scripts, documentation, and data directories:
- **Planning documents**:
  - `docs/graph_networking_plan.md`: Master architectural plan describing 8 stages (Stages 0–7) to convert the fragmented fact graph into a multi-tiered wiki network.
  - `docs/headings_to_ontology_plan.md`: Plan for Stage A–D headings densification and rules for `data/graph/headings.jsonl`.
- **Pipeline scripts**:
  - `scripts/graph_metrics.py` (lines 1–229): Computes metrics over the certified ontology, generates `reports/graph_metrics_<date>.json` and duplicate-merge proposals in `reports/merge_proposals.csv`.
  - `scripts/build_mentions.py` (lines 1–192): Scans the 2,676 textbook section markdowns in `data/okf/*/sections/*.md` against 20,342 certified ontology entity labels and acronyms from `ontology/registry.py:MEDICAL_SYNSETS`.
  - `scripts/build_hubs.py` (lines 1–326): Generates hub / map-of-content edges for organ systems (T2), mechanisms (T2), organism genera (T2), organism families (T3), drug classes (T3), and condition hierarchies (T3).
  - `scripts/build_crosswalk.py` (lines 1–350): Maps ontology conditions/phenotypes to BODHI graph conditions/symptoms via normalized name keys, bge-small cosine similarity, and two-pass DeepSeek adjudication (`v1` prompt and `verify1` second opinion).
  - `scripts/build_comention.py` (lines 1–184): Scans paragraphs in textbook sections and calculates Pointwise Mutual Information (PMI) for co-occurring entities, excluding existing certified fact edges.
  - `scripts/build_atlas_crosswalk.py` (lines 1–304): Resolves anatomical structure names against the 3D atlas catalogue in `/Users/ishaanwadhwa/Projects/third_party/human-atlas/public/models/atlas.json`.
- **Existing `data/graph/` artifacts**:
  - `data/graph/mentions.jsonl`: 20,342 lines, 23.2 MB (one record per certified entity).
  - `data/graph/by_section.jsonl`: 2,676 lines, 30.1 MB (one record per section).
  - `data/graph/meta.json`: 6 lines, 114 B (`{"sections": 2676, "max_df": 0.25, "labels_dropped_as_generic": 12, "links": 285095, "build_seconds": 13.0}`).
  - `data/graph/hubs.jsonl`: 7,923 lines, 2.6 MB (edges across 6 hub types).
  - `data/graph/hubs_llm_cache.json`: 53.7 KB (cached LLM responses for organism families and drug classes).
  - `data/graph/hubs_cost.json`: 64 B (`{"usd": 0.118, "note": "pessimistic estimate from char counts"}`).
  - `data/graph/crosswalk.jsonl`: 13,824 lines, 6.3 MB (crosswalk mappings).
  - `data/graph/crosswalk_emb.npz`: 21.5 MB (cached bge embeddings).
  - `data/graph/crosswalk_llm_cache.jsonl`: 15,737 lines, 2.5 MB (cached DeepSeek decisions for 15,052 `v1` and 685 `verify1` pairs).
  - `data/graph/crosswalk_meta.json`: 31 lines, 841 B (detailed crosswalk statistics).
  - `data/graph/comention.jsonl`: 24,644 lines, 5.8 MB (entity pairs with PMI >= 4.0, max 20 per entity).
  - `data/graph/atlas_crosswalk.jsonl`: 3,470 lines, 652 KB (atlas links).
  - `data/graph/atlas_crosswalk_llm_cache.jsonl`: 255 lines, 16.4 KB (cached atlas LLM judgements).

### 1.2 Baseline Graph Metrics
Execution of `.venv/bin/python scripts/graph_metrics.py` yielded:
```
date                               2026-11-13
certified_facts                    25902
nodes                              20342
edges                              25902
unique_edge_pairs                  25803
components                         1444
largest_component_nodes            16546
largest_component_pct              81.3
single_fact_components             987
degree1_nodes                      14031
degree1_pct                        69.0
median_degree                      1.0
mean_degree                        2.55
conditions                         5222
conditions_with_drug_pct           48.6
conditions_with_test_pct           29.2
conditions_with_symptom_pct        42.5
conditions_with_all_three_pct      13.5
conditions_with_none_pct           23.6
nodes_in_2plus_books               2494
nodes_in_2plus_books_pct           12.3
bodhi_available                    True
conditions_with_bodhi_id           413
conditions_with_bodhi_id_pct       7.9
phenotypes_with_bodhi_id           293
phenotypes_with_bodhi_id_pct       6.1
sections_reachable                 1143
sections_total                     2676
sections_reachable_pct             42.7

merge proposals (reports/merge_proposals.csv): cross_type=699, modifier_base=196, same_key_synonym=1, word_order=82
wrote reports/graph_metrics_2026-11-13.json
```

### 1.3 Pipeline Execution Verifications
All 5 pipeline scripts were executed in the environment:
1. `scripts/build_mentions.py`:
   - Execution time: 13.0s.
   - Result: 285,095 links across 2,676 sections; 12 generic labels dropped.
2. `scripts/build_hubs.py`:
   - Funnel: `{'class_candidates': 410, 'classes_kept': 330, 'proposed': 3766, 'accepted': 1648}`.
   - LLM calls: 0 (100% cached); cost: $0.000.
   - Hub edges produced: `organ_system` 5,319 (18 hubs), `mechanism` 248 (95 hubs), `organism_family` 336 (72 hubs), `organism_genus` 176 (51 hubs), `drug_class` 1,648 (234 hubs), `condition_hierarchy` 196 (152 hubs). Total 7,923 edges.
   - Network connectivity effect:
     - Facts only: 20,342 nodes, 1,444 components, largest component 81.3%.
     - Plus T2 hubs: 20,506 nodes, 170 components, largest component 98.1%.
     - Plus T2+T3 hubs: 20,730 nodes, 147 components, largest component 98.4%.
3. `scripts/build_crosswalk.py`:
   - Uncached pairs to judge: 0 (15,028 cached in `crosswalk_llm_cache.jsonl` for `v1`, 685 cached for `verify1`).
   - LLM calls: 0; cost: $0.000.
   - Output: 13,824 rows (857 T2, 12,967 T3; 1,059 exact, 3,088 broader, 1,752 narrower, 7,925 related).
4. `scripts/build_comention.py`:
   - Execution time: 21.4s.
   - Scanned: 81,790 paragraphs.
   - Output: 24,644 pairs after filtering out fact edges (3,050) and substring inclusions (2,320).
5. `scripts/build_atlas_crosswalk.py`:
   - Execution time: ~7.0s.
   - LLM calls: 0 (100% cached); cost: $0.000.
   - Output: 3,470 records into `data/graph/atlas_crosswalk.jsonl`.
6. Test suite:
   - Command: `.venv/bin/pytest tests/`
   - Result: 143 passed, 5 warnings in 42.38s.

---

## 2. Logic Chain

### 2.1 Dependency Ordering of Pipeline Scripts
Tracing script inputs and outputs establishes a strict execution order:
1. **`scripts/graph_metrics.py` (Step 1)**:
   - Reads: `data/ontology/clinical_ontology.jsonl`.
   - Writes: `reports/graph_metrics_<date>.json` and `reports/merge_proposals.csv`.
   - *Dependency*: `scripts/build_hubs.py` line 254 (`hierarchy_hubs`) explicitly opens and reads `reports/merge_proposals.csv` to extract `modifier_base` pairs for condition hierarchy hubs (`hub:isa:<base_id>`). Therefore, `graph_metrics.py` MUST run prior to `build_hubs.py`.
2. **`scripts/build_mentions.py` (Step 2)**:
   - Reads: `data/ontology/clinical_ontology.jsonl` and `data/okf/*/sections/*.md`.
   - Writes: `data/graph/mentions.jsonl` and `data/graph/by_section.jsonl`.
   - *Dependency*: `scripts/build_hubs.py` line 231 (`drug_class_hubs`) calls `rag.mentions.sections_for(label, k=600)` to require that a drug class and its proposed candidate member share at least one section in the textbooks before accepting the link. Therefore, `build_mentions.py` MUST run prior to `build_hubs.py`.
3. **`scripts/build_hubs.py` (Step 3)**:
   - Consumes the outputs of Step 1 and Step 2.
   - Generates `data/graph/hubs.jsonl`.
4. **`scripts/build_crosswalk.py` (Step 4)**:
   - Independent of `mentions.jsonl` and `hubs.jsonl`. Reads `clinical_ontology.jsonl` and BODHI graph. Uses `crosswalk_emb.npz` and `crosswalk_llm_cache.jsonl`.
5. **`scripts/build_comention.py` (Step 5)**:
   - Independent of `hubs.jsonl` and `crosswalk.jsonl`. Reuses entity loading from `build_mentions.py`.
6. **`scripts/build_atlas_crosswalk.py` (Step 6)**:
   - Independent of other graph layers; matches Gray's and ontology labels against the human-atlas catalogue.
7. **Post-update Re-measurement (Step 7)**:
   - Run `scripts/graph_metrics.py` to produce a post-update metrics report and verify baseline stability.

### 2.2 Integration with R1 (`headings.jsonl`)
In accordance with `docs/headings_to_ontology_plan.md`:
1. **Nature of `headings.jsonl`**:
   - Written to `data/graph/headings.jsonl` with schema:
     `{heading_id, book, section_id, level, class, facet, concept_ids, parent_id, tier, method, evidence}`.
   - Tiers are strictly T2 (derived navigation: `primary_topic`, `subtopic_of`, `illustrated_by`), T3 (inferred: `part_of` candidates), or navigation (facets). Never T1 certified facts.
2. **Separation from Certified Ontology**:
   - `docs/headings_to_ontology_plan.md` Section 2 & 7 dictates: headings data is NEVER written to `data/ontology/clinical_ontology.jsonl`.
   - `rag/answer.py:201` strictly constructs `graph_block` from `p.graph_facts` (T1 certified facts).
   - In `tests/test_graph_walk.py`, leak tests enforce that `hops.py` never reads hubs, co-mentions, or non-T2 crosswalk links into `graph_facts`. An equivalent leak test in `tests/test_headings.py` (or `tests/test_graph_walk.py`) must guarantee that no record from `headings.jsonl` can reach `graph_block`.
3. **Coupling Points with Graph Networking**:
   - **Hierarchy schema alignment**: `docs/headings_to_ontology_plan.md:239-240` notes that `headings.jsonl`'s Rule 4 (`subtopic_of`) reuses the record format of `hubs.jsonl` (`hub_type: heading_hierarchy`).
   - **Mention alias enhancement**: Rule 5a parenthetical aliases ("Rifampin (Rifampicin, R)") can optionally be ingested by `scripts/build_mentions.py:load_aliases` to broaden mention recall without LLM cost.
   - **Execution order**: Headings densification (R1) can run in parallel with or prior to R2, because R2 graph networking scripts read `data/ontology/clinical_ontology.jsonl` and `data/okf/*/sections/*.md`.

---

## 3. Caveats

1. **Snapshot Invariance**: The current pipeline scripts run against `data/ontology/clinical_ontology.jsonl` which currently contains 25,902 certified facts and 20,342 unique nodes. If another agent or pipeline stage modifies `clinical_ontology.jsonl`, all graph scripts must be re-run in order.
2. **LLM Cache Completeness**: Current test runs demonstrated 100% cache hit rates on all LLM stages (`hubs_llm_cache.json`, `crosswalk_llm_cache.jsonl`, `atlas_crosswalk_llm_cache.jsonl`), incurring $0.000 in API costs. If new entities are added to the ontology, uncached pairs will require DeepSeek API calls subject to the configured `--budget` caps.
3. **BODHI Crosswalk Coverage Limit**: BODHI contains only 755 conditions (555 with symptom edges) and 2,582 symptoms. The theoretical maximum coverage of the ontology by BODHI is bounded by BODHI's size (~15–20% of ontology conditions), not by the matcher.
4. **Co-mention Non-causality**: Co-mention (PMI) is purely statistical association (T4). It must remain disabled by default in UI and strictly barred from retrieval fact paths in `rag/hops.py`.

---

## 4. Conclusion

1. **Readiness**: R2 Graph Networking Pipeline is fully functional, robustly cached, and deterministic. All scripts (`build_mentions.py`, `build_hubs.py`, `build_crosswalk.py`, `build_comention.py`, `build_atlas_crosswalk.py`) execute successfully in under 2 minutes total wall-clock time without external API spend.
2. **Baseline established**:
   - Certified facts: 25,902; Nodes: 20,342; Unique edge pairs: 25,803.
   - Connected components: 1,444; Giant component: 16,546 nodes (81.3%).
   - Hub addition (`hubs.jsonl`): lifts giant component to 98.4% (20,730 nodes) and collapses components to 147.
   - Sections reachable via mentions: 2,676 / 2,676 (100%), linking 285,095 entity-section occurrences.
   - Crosswalk: 857 T2 trusted links, 12,967 T3 display links.
3. **Execution Plan for Implementation**:
   - Execute Stage 1: `scripts/graph_metrics.py` (writes baseline `reports/graph_metrics_<date>.json` and `reports/merge_proposals.csv`).
   - Execute Stage 2: `scripts/build_mentions.py` (writes `data/graph/mentions.jsonl`, `by_section.jsonl`, `meta.json`).
   - Execute Stage 3: `scripts/build_hubs.py` (reads `merge_proposals.csv` and `mentions.jsonl`, writes `hubs.jsonl`).
   - Execute Stage 4: `scripts/build_crosswalk.py` (writes `crosswalk.jsonl`).
   - Execute Stage 5: `scripts/build_comention.py` (writes `comention.jsonl`).
   - Execute Stage 6: `scripts/build_atlas_crosswalk.py` (writes `atlas_crosswalk.jsonl`).
   - Execute Stage 7: `scripts/graph_metrics.py` (post-update measurement and comparison).
   - Execute Stage 8: `.venv/bin/pytest tests/` (full regression and leak validation).

---

## 5. Verification Method

### 5.1 Baseline & Script Verification Commands
To independently verify the pipeline:

1. **Verify Baseline Metrics**:
   ```bash
   .venv/bin/python scripts/graph_metrics.py
   ```
   *Expected output*: 25,902 certified facts, 20,342 nodes, 1,444 components, largest component 81.3% (16,546 nodes). File written: `reports/graph_metrics_2026-11-13.json` and `reports/merge_proposals.csv`.

2. **Verify Mentions Build**:
   ```bash
   .venv/bin/python scripts/build_mentions.py
   ```
   *Expected output*: `{'sections': 2676, 'max_df': 0.25, 'labels_dropped_as_generic': 12, 'links': 285095, 'build_seconds': ~13-20}`.

3. **Verify Hubs Build**:
   ```bash
   .venv/bin/python scripts/build_hubs.py
   ```
   *Expected output*: 7,923 edges across 6 hub types, 0 LLM calls, giant component reaches 98.4% (T1+T2+T3).

4. **Verify Crosswalk Build**:
   ```bash
   .venv/bin/python scripts/build_crosswalk.py
   ```
   *Expected output*: 13,824 rows, 0 uncached pairs to judge, deepseek spent $0.2724 (cumulative).

5. **Verify Co-mention Build**:
   ```bash
   .venv/bin/python scripts/build_comention.py
   ```
   *Expected output*: 24,644 pairs after cap, ~20-25s build time.

6. **Verify Atlas Crosswalk Build**:
   ```bash
   .venv/bin/python scripts/build_atlas_crosswalk.py
   ```
   *Expected output*: 3,470 records into `data/graph/atlas_crosswalk.jsonl`.

7. **Verify Test Suite & Leak Prevention**:
   ```bash
   .venv/bin/pytest tests/
   ```
   *Expected output*: 143 passed in ~42s without regressions.

### 5.2 Invalidation Conditions
- Any decrease in test pass count below 143.
- Any non-T1 edge (from `hubs.jsonl`, `headings.jsonl`, `comention.jsonl`, or non-T2 `crosswalk.jsonl`) appearing in `p.graph_facts` or `graph_block` in `rag/answer.py`.
- Execution of `build_hubs.py` before `graph_metrics.py` (which causes missing `reports/merge_proposals.csv` and drops 196 condition hierarchy hubs).
