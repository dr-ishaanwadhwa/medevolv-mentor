# Global networking plan: from a fact graph to a "second brain" wiki

Status: **plan only, nothing implemented.** Measured 2026-11-13 on a snapshot of `data/ontology/clinical_ontology.jsonl`
(26,661 rows, 24,096 CERTIFIED, 2,565 CANDIDATE; another session is still editing it, so re-measure before building).
Counts only; no textbook text is quoted. Throwaway scripts live in the session scratchpad, not in the repo. They are
`m1.py` to `m5.py` in `/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/f504bb28-7041-40b9-bd4d-ee71252ff7d4/scratchpad/`,
and they should be promoted to `eval/graph_metrics.py` in Stage 0 so every stage re-measures the same way.

## 1. Baseline (CERTIFIED facts only)

### 1.1 Structure of the ontology graph

| Metric | Value | Reading |
|---|---|---|
| Nodes / edges | 18,831 / 24,096 (24,003 unique pairs) | about 1.3 edges per node |
| Connected components | **1,354**; largest = 15,335 nodes (**81.4%**) | 938 components (69%) are a single isolated fact (2 nodes) |
| Orphans (degree 0) | 0 | by construction: a node exists only because a fact does |
| Degree-1 leaves | **12,982 (68.9%)**; degree <= 2: 15,275 (81%) | most nodes hang off exactly one edge |
| Degree: median / mean | 1 / 2.55 | |
| Top hubs | Fever 142, Glucocorticoids 125, Heart failure 119, Tuberculosis 113, Hypertension 113, RA 111, SLE 106, Alzheimer's 101, HIV 95, Asthma 86 | only 8 nodes have degree > 100 |
| Avg shortest path (150 BFS sources, largest component) | **6.1 hops**, max seen 20 | long, because the graph is tree-like |
| Mean degree by type | Condition 4.6; Drug 2.7; Phenotype 1.8; Etiological 1.6; Test 1.4; Target 1.3; Process 1.2; Stage 1.2 | leaf share: Stage 93%, Process 88%, Test 86%, Phenotype 81%, Drug 63%, Condition 42% |

Entity types in the data: PathologicalCondition 4,827, ClinicalPhenotype 4,352, TherapeuticAgent 3,618, DiagnosticModality 2,268
(this is the type name used in the data; there is no `DiagnosticTest`), PhysiologicalProcess 1,545, EtiologicalAgent 1,036,
ClinicalStage 710, MolecularTarget 468, OrganSystem 7.

### 1.2 Edges by predicate

TREATED_BY 7,119 · MANIFESTS_AS 6,266 · CONFIRMED_BY 3,176 · CAUSED_BY 2,357 · DISRUPTS_PATHWAY 1,487 · CAUSES_ADVERSE_EFFECT 977 ·
HAS_CLINICAL_STAGE 790 · TARGETS_MECHANISM 660 · CONTRAINDICATES 634 · is_a 317 · DIFFERENTIAL_OF 313.
97% of edges are Condition-centred (Condition to Drug 6,996; to Phenotype 6,225; to Test 3,145; to Etiology 1,578).
There is **no hierarchy layer**: `is_a` is 1.3% of edges (227 condition-to-condition, 24 drug-to-drug). There are no inverse edges.

### 1.3 Condition completeness (4,827 conditions)

| Has at least 1 | Share |
|---|---|
| drug (TREATED_BY) | 50.5% |
| symptom (MANIFESTS_AS) | 42.1% |
| test (CONFIRMED_BY) | 29.5% |
| all three | **13.7%** |
| none of the three | 22.3% |

### 1.4 Cross-book bridges

- Entities supported by 2+ books: **12.1%** (2,280 of 18,831). 3 books: 353, 4 books: 133, 5 books: 56. By type: Drug 15.6%, Condition 14.6%,
  Etiological 14.4%, Phenotype 12.9%, Test 6.7%, Process 4.9%, Stage 4.1%.
- Facts supported by 2+ books: 929 (3.9%). Source mix is Harrison 18,457 · Robbins 4,413 · Davidson 1,438 · Tripathi 1,122 · Micro 630 · Guyton 9.
  Harrison dominates, so most "bridges" are really Harrison plus one other book.
- 79.5% of entities cite exactly one section. Mean 1.66 sections per entity.

### 1.5 Duplicates still split

| Kind | Count | Examples (labels only) |
|---|---|---|
| Same normalised key and type, different id | 1 group | thyroxine / levothyroxine (a synonym `merge_key` misses) |
| Same words in a different order or with a stopword (token-set equal, same type) | **83 groups / 169 nodes** | Medullary carcinoma of the thyroid / Medullary thyroid carcinoma; CSF culture / Culture of CSF; Salmonella Paratyphi / Salmonella Paratyphi A |
| Modifier + base condition ("Acute X" / "X", Severe, Primary, ...) | 147 pairs | Primary hypertension / Hypertension. Some are legitimate subtypes and should become `is_a`, not merges. |
| Same label, **different type** (kept apart on purpose) | **577 label groups** | 322 are Phenotype vs Condition; also Stage vs Condition (55), Etiological vs Condition (29), Process vs Condition/Phenotype (72) |
| Case-only duplicates | 0 | already handled |
| Labels with parentheses | 206 | qualifier noise such as "(disorder)" |

`ontology/merge.py` already handles case, plural, hyphen, apostrophe and British/US spelling. The remaining duplicates are word order, synonyms
and cross-type twins. Cross-type twins are not errors. A symptom node "Dyspnoea" and a condition node of the same name are two roles, and they
need a `same_concept_as` link, not a merge.

### 1.6 Cross-layer alignment

| Alignment | Result |
|---|---|
| Ontology conditions that carry a BODHI id | **381 of 4,827 = 7.9%** (name-key match adds only 3 more) |
| Ontology phenotypes that carry a BODHI id | **292 of 4,352 = 6.7%**; only 158 land on a BODHI *Symptom* node. 83 land on Concept and 51 on Condition, which is a typing mismatch |
| Ontology drugs / tests with a BODHI id | 406 of 3,618 (11.2%) / 14 of 2,268 (0.6%) |
| Reverse: BODHI Condition nodes with an ontology hit via `ontology_facts.match_conditions` | 454 of 755 (60%); of the 555 that have symptom edges, 377 (68%) |
| Reverse: BODHI symptoms with a same-name ontology phenotype | 420 of 2,582 (16%) |
| `graph.link_entities` run on 400 sampled ontology condition labels (includes the semantic fallback) | 30% return something, **9% return the same-named node** |
| Same for 400 sampled phenotype labels | 25% return something, **4% same-named** |

BODHI holds only 2,284 Condition/Concept nodes and 2,582 Symptoms, so the ceiling for the crosswalk is limited by BODHI's size.
The realistic target is roughly 15-20% of ontology conditions, not 100%. The ontology is much wider than BODHI.
The fuzzy `link_entities` numbers show that its semantic fallback fires on many labels but rarely finds the equivalent node, so it must
not be used as a crosswalk without an adjudication step.

### 1.7 Entity-to-section links

All 18,831 entities have at least one section through fact provenance (this is by construction). Mention scan: lowercase, crude plural
folding, exact phrase of 1 to 8 tokens, run over all 33,830 passages (6 seconds, no LLM). The scan is **not yet validated for precision**;
it is a lower bound on recall (no synonyms or abbreviations) and has false-positive risk on short generic labels such as Fever and Pain.

| | Provenance only | Mention scan |
|---|---|---|
| Entities with at least 1 section | 100% | 81.9% (labels too rare or worded differently for the rest) |
| Entities with 2+ sections | 20.5% | **59.3%** |
| Entities with 5+ sections | n/a | 38.6% |
| Entities seen in 2+ books | 12.1% | **48.8%** |
| Sections reachable from the ontology | 916 of 2,062 (**44%**) | 2,055 of 2,062 (99.7%) |
| Entity-section links | 31,292 | 267,344 (8.5x) |
| By type, at least 1 passage | | Condition 88%, Drug 89%, Phenotype 85%, Stage 84%, Etiological 74%, Process 65%, Test 65% |

61% of entities are mentioned in at least one section where no fact about them was extracted. That is the main missing link layer.

### 1.8 Raw material for hubs and chains (already in the data)

| Hub / chain | Today |
|---|---|
| Organ system | `ontology_facts.catalog()` already groups 4,661 conditions into 18 systems and about 100 categories (rule-based on chapter; documented as presentation only). `clinical_facets.organ_system` is **0% filled**. `OrganSystem` has 7 nodes. |
| Drug class | 293 drug nodes have class-like labels (Glucocorticoids, SGLT2 inhibitors, ...), but only 24 `is_a` drug edges, so class to member is almost entirely missing. |
| Mechanism | 507 targets; only 95 are shared by 2+ drugs. 990 of 3,138 treating-drugs treat 2+ conditions. |
| Organism to disease to drug | 1,040 etiological agents cause a condition; **668 (64%)** cause a condition that has a drug. 556 of 1,079 organism-linked conditions have a drug. This chain already exists in the data and nobody walks it. |
| Shared test / symptom | 323 of 2,248 tests serve 2+ conditions; 690 of 3,953 phenotypes manifest in 2+ conditions (the differential-diagnosis bridges). |
| Co-mention | 456k entity pairs co-occur in 2+ passages and are not a fact edge (see Stage 6). Adding all of them would lift the largest component from 81% to 97%, which shows the graph is connectable and also that this would be mostly noise. |

### 1.9 What the numbers say

1. The fact graph is shallow and fragmented by design: one fact per quote. More extraction raises coverage but not interlinking.
2. The two cheapest and largest gains are **deterministic and need no LLM**: the mention index (reachable sections 44% to about 100%) and
   derived hubs and inverses.
3. BODHI crosswalk gains are real but small in volume and large in clinical risk. Do them with adjudication, and only for navigation.

## 2. Principles

1. **Link tiers, never mixed.** T1 CERTIFIED (a verbatim quote exists), T2 DERIVED (logical consequences of T1: inverses, same-entity,
   hierarchy roll-ups), T3 INFERRED (LLM or embedding said so, with evidence span), T4 CO-MENTION (statistics only). Each stored edge carries `tier`,
   `method`, `evidence` (section ids) and `created_by`. The UI draws T1 solid, T2 thin solid, T3 dashed, T4 dotted and off by default.
2. **Navigation-only rule.** Anything below T1 is for finding, ordering and displaying. It is never given to the answer model as a clinical statement. See section 5.
3. **Separate files, never the ontology jsonl.** All new layers are written under `data/graph/` (derived, rebuildable, git-ignored) and loaded
   by a new `rag/wiki.py`. The certified file and `ontology_facts.py` are not changed, so this does not collide with the ontology session.
4. **Deterministic first, LLM last, human spot-check on every LLM stage** (a 100-link sample with a pass threshold before the layer ships).

## 3. Staged plan

DeepSeek cost assumes about $0.28 per million input tokens and $0.42-1.10 per million output tokens (same assumption as `docs/ontology_reinforcement_plan.md`; recheck current prices).

| # | Stage | What it builds | Expected gain (metrics above) | Effect on answers / UI | DeepSeek cost | Effort | Risk |
|---|---|---|---|---|---|---|---|
| 0 | **Metrics harness and hygiene** | `eval/graph_metrics.py` (this report's numbers, one command). Merge 83 word-order duplicate groups and the synonym list (thyroxine and similar) via `merge.py` rules. Add `same_concept_as` links for the 577 cross-type label twins. | Nodes -100 to -250. Cross-type twins linked, so Dyspnoea-as-symptom reaches Dyspnoea-as-condition. Components -10 to -30. | Fewer split pages in Explore. | $0 (or about $0.05 to verify ambiguous merges) | 0.5 day | Low. A wrong merge fuses two diseases. Merge only on token-set equality of the same type; send "Acute X / X" pairs to `is_a` (Stage 3), never to a merge. Coordinate: `merge.py` and the jsonl belong to the other session; emit the merge list as a proposal file. |
| 1 | **Canonical entity pages and backlinks** | `data/graph/entities.jsonl`: one record per node with id, label, aliases, type, all outgoing and incoming facts (T1) grouped by predicate, fact ids, books, sections. Inverse edges are computed here (TREATED_BY gives "treats", CAUSED_BY gives "causes", MANIFESTS_AS gives "manifestation of", CONFIRMED_BY gives "confirms", and so on). A pure function of the jsonl. | Every node answers "who points at me". Drug page lists all conditions it treats (990 drugs treat 2+). Phenotype page lists all 690 multi-condition symptoms as a differential list. Leaves stop being dead ends. | Explore: pages for drugs, tests, symptoms, organisms (today only conditions have a page). Backlinks panel. | $0 | 1 day | Very low. Inverse wording must not flip meaning: CONTRAINDICATES inverse reads "contraindicated in", not "treats". Whitelist the inverse label per predicate and test it. |
| 2 | **Entity to section/passage mention index** | `data/graph/mentions.sqlite`: entity id to (section_id, passage_id, count, first heading), from the exact-phrase scan plus aliases from Stage 0/1, with a stoplist for generic labels and a "specific enough" rule (IDF or 2+ tokens). Provenance sections flagged `evidence=certified`; mention-only sections flagged `mention`. | Reachable sections 44% to about 100%. Entities with 2+ sections 20% to 59%. Cross-book entities 12% to 49% (**only after the precision check**). Entity-section links 31k to 267k. | UI "Appears in" list across books, grouped by book and chapter. Retrieval can filter by `section_ids` (the argument already exists in `retrieve.search`). | $0 (6 s scan). Optional $0.2-0.5 for an LLM alias list for the top 2,000 entities. | 1-1.5 days incl. a 100-link precision audit | Medium for UX, none for clinical claims (navigation only). Short or ambiguous labels (Fever, Pain, Iron, Shock) will flood; cap per entity, rank by TF-IDF or heading match, show counts. Abbreviations (MI, TB) need the synonym table in `ontology/registry.py`. |
| 3 | **Hub / map-of-content nodes and hierarchy** | (a) Organ-system hub from `catalog()` rules (T2) with membership edges. (b) Organism family hubs: genus parsed from the label, plus family via a single batched LLM pass over 1,036 agents (T3). (c) Drug-class hubs: 293 class-like nodes are already in the graph; link members by LLM classification over 3,618 drugs, accepted only if the class and the member both appear in the same section (T3, with evidence section). (d) Mechanism hubs from existing TARGETS_MECHANISM (T2; 95 shared targets). (e) Condition hierarchy: the 147 "Acute X / X" pairs as `is_a` (T3), plus roll-up counts. Each hub gets an index page. | Largest-component share 81% to about 88-90% (hubs bridge small components). Leaves: each drug gets a class parent. Average path 6.1 to about 4.5. Components with 2 nodes drop sharply where a hub touches them. Organism chain: 64% of agents are reachable as organism to disease to drug. | "Browse by class / organism family / mechanism" like Obsidian MOC pages. Retrieval: hub membership lets "which fluoroquinolones..." be answered by listing T1 facts of each member. | (a) $0; (b) about $0.1; (c) about 3,600 drugs x 300 tokens in batches of 40 is under $0.30; (e) about $0.05. **Total under $1** | 2-3 days | **Highest clinical risk of the structural stages.** A wrong class membership implies class-level contraindications. Rule: class edges are T3, shown with evidence, and **never** used to propagate TREATED_BY or CONTRAINDICATES from class to member in answers. Audit 100 per hub type, ship only if >= 95% precise. |
| 4 | **BODHI crosswalk table** | `data/graph/crosswalk.jsonl`: ontology id, BODHI id, relation (`exact`, `broader`, `narrower`, `related`), score, method (id match, name key, embedding top-5 + LLM adjudication), checked flag. Candidates come from `merge_key` name keys, the `registry.py` synsets, and bge embeddings of BODHI names (free, local). The LLM only judges the ambiguous top-5 pairs. | Conditions linked 7.9% to roughly 15-20%; BODHI conditions that reach ontology facts 60% to roughly 75%; phenotypes linked 6.7% to roughly 12-15%. Typing mismatches become explicit instead of silent. | The graph route (symptoms to conditions in `hops.plan`) gets certified drug, test and warning facts for more of its candidate conditions (today 68% of BODHI conditions with symptom edges have an ontology hit). Explore can show "BODHI says these symptoms point here" on the entity page. | About 3,000 ambiguous pairs x 400 tokens = $0.3-0.5 | 2 days | **High if misused.** An `exact` link to the wrong disease routes the wrong drugs into a vignette answer. Mitigate: only `exact` plus `checked` links may feed `ontology_facts.graph_facts_for`; `broader`, `narrower` and `related` are display only. Cross-type links (phenotype to BODHI Condition) are `related` only. BODHI is CC BY-NC: keep attribution, never copy its text into certified facts. |
| 5 | **Navigation-only retrieval/answer integration** | New "neighbour hop" in `hops.py` (design in section 4). | Better recall for multi-concept and comparison questions; sections from other books are surfaced. Measured by the eval set below, not by graph metrics. | Answer panel: "Related concepts" and "Also covered in" chips under the answer, each citing section links. | $0 at query time (no extra LLM call) | 2 days | Medium. Extra passages can dilute the context. Cap neighbour sections at 2 of the 5 slots, and run the existing eval before and after. |
| 6 | **Co-mention layer (weak)** | `data/graph/comention.sqlite`: entity pairs co-occurring in the same passage, scored by pointwise mutual information (PMI), minimum 3 passages, 2+ books preferred, generic entities excluded. Cap 20 neighbours per entity. | 456k raw candidate pairs (2+ passages) reduce to about 50-100k after PMI and caps. Touches about 51% of the 12,982 leaves. Fully connectable (97% in one component) but meaningless as a clinical path. | "See also (co-mentioned)" in a grey, collapsed section, plus an optional dotted layer in the graph. Off by default. | $0 | 1 day | Low technical risk, **high misuse risk**: co-occurrence is not causation (a drug and its side effect share passages with the disease it treats). Must be visually and in code separate (`tier=T4`), never read by `hops.py`'s fact path, never counted in connectivity metrics reported as "knowledge". |
| 7 | **UI: backlinks panel, related concepts, local graph** | Explore: click-through entity pages (Stage 1 pages), "Linked from" and "Appears in" panels (Stage 2), "Related concepts" by tier, and an Obsidian-style *local graph*: the selected node plus 1-2 hops, edges coloured by tier. | Does not change the metrics. Increases click-depth per session and is the demo-visible payoff. | `rag/graph_component/index.html` already draws a levelled graph from `clinical_graph.build(...)`. Add a `neighbourhood(entity_id, hops, tiers)` builder with kind colours per type and line style per tier; drop the 5-level disclosure for this mode. | $0 | 2-3 days | Low. Hairball risk: cap 25 nodes, group by predicate, default to T1 plus T2 only. |

### Recommended order

**0, 1, 2 first** (about 3 days, $0), then **7 for the demo**, then **3 (organ, mechanism, organism parts first)**, **4**, **5**, **6 last**.
Reasons: Stages 0-2 are deterministic and give most of the measured link gain (reachable sections 44% to about 100%, 8.5x entity-section links)
with no clinical risk. Stage 7 turns them into something visible. Stage 3 and Stage 4 add LLM judgement, so they ship only after a precision audit.
Stage 6 stays last and optional.

Total new LLM spend for everything: **about $1-2 of DeepSeek**. The real cost is engineering time (about 12-14 days) and the audits.

## 4. How the links plug into retrieval (`hops.py`)

Today `plan()` links the question to BODHI nodes, then BODHI candidate conditions, then `ontology_facts.graph_facts_for`, plus `search()` over
Chroma (`search(..., section_ids=...)` already supports filtering). Proposed addition, all behind a flag (`GRAPH_WALK=1`):

1. **Resolve entities.** After `link_entities`, resolve question terms and candidate conditions to ontology ids through the entity registry plus crosswalk (`exact`+`checked` only).
2. **Section expansion (Stage 2).** For each resolved entity, take the top 2-3 mention sections ranked by TF-IDF and book diversity, prefer sections from books that are not already in the evidence. Run `search(sub_query, section_ids=those)`. This is a new `Hop("expand", ...)` after the case/graph hops and before `_add_hits`.
3. **Walk (Stages 1, 3).** For comparison or "difference between" questions, add the 1-hop T1 neighbours of both entities (their shared tests and symptoms, from entity pages) as `graph_facts`, labelled with their fact id so the answer cites it as `[G#]` like any certified fact.
4. **Related concepts (Stages 3, 6).** Hub siblings and co-mentions go into a separate `Plan.related` list that is rendered in the UI only and never goes into `graph_block`.
5. **Trace.** Each added hop records its tier and method in `trace` so the "How it works" tab shows why a section was pulled in.

Guard rails in `answer.py`: the prompt's graph block receives only T1 fact lines (as now). `cross_check` stays as is. Add a unit test that fails if any non-T1 edge can reach `graph_block`.

## 5. What must never generate clinical claims (navigation only)

- T4 co-mention edges and any "related" list built from them.
- Any inferred class membership (drug class, organism family, "Acute X is_a X"), including roll-ups. Do not propagate TREATED_BY, CONTRAINDICATES or CAUSES_ADVERSE_EFFECT from class to member, or from parent condition to child, in answers.
- Crosswalk rows that are not `exact` and `checked`. BODHI symptom likelihoods stay a ranking signal for candidate conditions (as today), not a statement in an answer.
- Mention-index hits ("appears in"): a passage that mentions a drug near a disease does not say the drug treats it.
- Inverse edges are logically safe but must carry the same fact id and quote as the original and read in the correct direction; they add no new claim.
- Organ-system and chapter-derived groupings (already documented as presentation only in `ontology_facts.py`).
- Embedding nearest-neighbour "similar concepts".

Note an existing risk to review in this context: `hops.plan` already places BODHI drug links into `graph_facts` as sentences. Those are not
textbook-certified, so treat them as T3 and keep them visibly separate from certified lines in answers.

## 6. Success metrics (re-measure after each stage with `eval/graph_metrics.py`)

| Metric | Baseline | S0 | S1 | S2 | S3 | S4 | S6/S7 |
|---|---|---|---|---|---|---|---|
| Certified nodes / edges | 18,831 / 24,096 | -1% nodes | same | same | same | same | same |
| Largest component share (T1 only) | 81.4% | ~82% | same | same | ~88-90% (T1+T2+T3 hubs) | ~90% | n/a: report T4 separately |
| Components (T1 only) | 1,354 | ~1,330 | same | same | < 900 with hubs | < 850 | |
| Degree-1 leaves with at least 1 non-fact link (backlink / section / hub) | 0% | 0% | 100% (backlinks) | 100% | 100% | 100% | |
| Avg shortest path (T1+T2) | 6.1 | 6.1 | ~5.5 (inverses make it traversable both ways) | | ~4.5 | | |
| Conditions with drug+test+symptom | 13.7% | same | same | same | same | same (via BODHI display) | |
| Entities in 2+ books | 12.1% | | | **49%** (after precision audit) | | | |
| Sections reachable from ontology | 44% | | | **~100%** | | | |
| Entity-section links | 31k | | | 267k | | | |
| Conditions linked to BODHI | 7.9% | | | | | **15-20%** (checked >= 95% precise) | |
| Phenotypes linked to BODHI symptom | 3.6% (158) | | | | | **10-15%** | |
| Duplicate groups (token-set + synonym) | 83 + 1 | **0** | | | | | |
| Link precision (100-sample audit, per layer) | n/a | >= 99% | 100% (logical) | >= 90% mention | >= 95% hubs | >= 95% exact | no gate (display only) |
| Answer eval: multi-concept recall / citation hit rate (existing `eval/`) | measure now | | | | | | no regression on single-topic questions; improvement on compare/vignette sets |
| Leak test: non-T1 edges that reach `graph_block` | 0 | 0 | 0 | 0 | 0 | 0 | 0 (hard gate) |

## 7. Biggest risks, in order

1. **Wrong class / organism / crosswalk link silently becomes a clinical claim** (a wrong "exact" BODHI link sends another disease's drugs into a vignette answer). Mitigation: tiering, the leak test, `exact`+`checked` only into facts, audits with a pass threshold.
2. **Mention-scan noise on generic labels** inflates the "appears in" lists and the cross-book numbers. The 49% figure is unvalidated. Run the 100-link audit before quoting it, and apply a specificity filter.
3. **Merging distinct concepts** (Acute X vs X, Type 1 vs Type 2, Salmonella Paratyphi vs Paratyphi A). Use proposals, not auto-merge, and keep cross-type twins as links.
4. **Moving target and write collisions** with the ontology session. Build only from a snapshot file and write only under `data/graph/`.
5. **Hairball UI and context dilution.** Cap nodes, keep T3 and T4 off by default, and cap neighbour slots in retrieval.
6. **Source skew.** 77% of certified facts are Harrison, so "cross-book" gains for Guyton (9 facts) and Micro (630) stay thin until more extraction is run. The mention index is what gives these books any presence in the graph.
7. **Licence.** BODHI is CC BY-NC; the crosswalk and any BODHI-derived hub must keep attribution and stay non-commercial. Textbook text stays local (the mention index stores ids and counts, not text).
