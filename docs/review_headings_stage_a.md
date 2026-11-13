# Gate review: Stage A headings (Gemini, worker_m1)

Reviewer: Claude. Date: 2026-11-13. Review only. No code or data changed. No textbook body text is quoted below; heading titles only.

## Verdict: APPROVE as an unused navigation module (safe to commit)

Nothing heading-derived can reach the answer prompt today, and the file is not stale. The issues below are label quality and test quality. They block any UI use, not the commit. The plan's own bar (a 100-link audit at 90% or better on primary topics) was not run, so do not show primary topics in the UI yet.

## Dead-id count: 0

- Every one of the 2,675 `section_id`s in `headings.jsonl` exists in the current `data/okf/*/toc.json` (2,676 ids).
- The file was written at 14:45, after the Gray's toc at 12:44. It already reflects the 614-section Gray's split.
- I rebuilt into a scratchpad copy with `build_headings(output_path=...)`. The CLI has no output option, but the function does. The rebuild is record-for-record identical to the committed file (3,135 rows, 0 differences). Re-running `python -m rag.headings` would change nothing.
- `primary_topic("grays/160-abdomen-inguinal-hernias")` returning None is correct. The id is live (Groin > Inguinal hernias). Its heading is class `entity` (T3, no ontology node). `primary_topic` only returns class `matched`, and the ontology has no "Inguinal hernias" node under the strict key.
- The only gap runs the other way. One toc id has no record: `tripathi/0260-43-haematinics-and-erythropoie-uses`. It is the duplicated Tripathi path, `Maturation Factors > Uses`. `parse_heading_tree` keys sections by path tuple, so the second one overwrites the first. This is the plan's known 2,675 vs 2,676 difference. It is harmless, but it is an undocumented one-section blind spot.

## 1. Correctness against the Stage A rules

| Rule | Result |
|---|---|
| Facet before entity match (Rule 3) | Correct. `FACET_EXACT` runs at step 3, before `r["match"]`. "Joints", "Nerves", "Arteries" and "Toxicity" are all class `facet` with no concept ids. The hard gate holds (0 facets promoted). |
| Primary topic (Rule 1) | Mostly right, with defects. 419 exact, 49 paren, 13 variant, 26 bridge. Single-word bridges are withheld unless `allow_bridge=True`. In my 24-link sample, 21 to 22 were clearly right. |
| Parenthetical aliases (Rule 5a) | Works as designed. "Pertussis (Bordetella pertussis)" matches Pertussis. `parenthetical_aliases()` is computed on demand and is not persisted to the file. |
| Cross-book identical headings (Rule 6) | Works as designed (64 identical, 37 in the ontology, 71 near-duplicate groups). The near-duplicate count in the report was not re-derived by me. |
| Case headings to conditions (Rule 8) | OK. "Case 2: Cervical spinal cord injury" gets the right label. 77 of 98 conditions are matched. |
| `subtopic_of` | Present only as `parent_id` plus `subtopics()` and `facets_for()`. There is no explicit edge record. `part_of` candidates come from `part_of_candidates()`, not from the file. Reasonable for navigation. |
| Tiers | Correct. T2 605, T3 1,221, navigation 1,309, T1 zero. Asserted at build time and in tests. |

### Defects found

1. **Wrong-type match.** Gray's "Pulmonary valve" links to the TherapeuticAgent node "Pulmonary valve replacement". The plan listed this exact case as a known hazard. The code has no type guard when only one candidate exists, because `disambiguate_candidates` returns early at `len == 1`.
2. **Possessive misses.** `merge_key` keeps the possessive ("hodgkins lymphoma" vs "hodgkin lymphoma"). Three headings that would match after stripping the possessive stay unmatched: "Hodgkin's Lymphoma", "Non-Hodgkin's Lymphoma", "Parkinson's Disease". They are listed as T3 entity. This is small but it is the plan's own eponym case.
3. **Unstripped numbering in Tripathi.** `clean_heading` does not strip "17a." or "41b.". Eight headings keep the prefix, for example "17a. Introduction", "7b. Cholinergic System and Drugs" and "41b. Diuretics". Four of them are `topic` and would be facets.
4. **Entity vs topic misclassification.** The regex fallback labels many topic or facet-of-parent headings as T3 `entity`. Examples:
   - "Aetiology and pathogenesis of diabetes" (Davidson). This is a facet of Diabetes mellitus.
   - "Identification and assessment of deterioration" (Davidson).
   - "Overview of cellular responses to stress and noxious stimuli" (Robbins).
   - "Cellular pathology of the central nervous system" (Robbins).
   - "Pathogenesis, Diagnosis, and Treatment of Fungal Infections" (Harrison).
   - "The Role of Epigenetics in Disease and Treatment" (Harrison).
   - "Integration of Renal Mechanisms for Control of Extracellular..." (Guyton).
   - "General Mycology and Overview of Fungal Infections" (Micro).
   
   This matches the plan's 15% to 30% tolerated error and is the reason Stage B exists. T3 entities carry no concept ids, so the harm is limited to display noise.
5. **Dubious alias match.** Tripathi "Dipeptidyl peptidase-4 (DPP-4) inhibitors" matches the node "DPP-4" through the parenthetical. The enzyme is not the drug class.
6. **Generic hubs.** "Autoimmunity" in Micro is correctly held back as a bridge. "Stomach", "Foot" and "Heart" stay unmatched. These are acceptable false negatives.

### 40-record spot-check (seed 7, 6 per book, 40 shown)

I judged each record's class and match.

- **Class right and match right:** 24 of 40. These were facets ("Overview" ×5), group/structural/topic headings, the case, and the matches Pertussis, Viral gastroenteritis, Shock, "The inflammatory response", "Cancer of the Skin" (to Skin cancer) and the correctly unmatched organ and structure entities.
- **Class wrong:** 11 of 40, all `entity` that should be `topic`/facet (defect 4). One more is a facet mislabelled by its numbering prefix (defect 3).
- **Match wrong or doubtful:** 2 of 40 (the DPP-4 alias; and Hodgkin's, a missed match).
- **Remaining 2 of 40:** borderline. They are plausible entities that I could not confirm either way without reading the book (for example "Needle Stick Injury").

Entity-typing accuracy is about 70%, which agrees with the plan's audit. Primary-topic match accuracy is about 90% in the sample (21 to 22 of 24). That is at the bar, not above it, and the sample is small.

## 2. Staleness: see "Dead-id count" above (0, none, rebuild identical)

## 3. Leak safety: clean

- Nothing in `rag/` imports `rag.headings`. Only `tests/test_headings_leak.py` and `eval/heading_metrics.py` import it. `rag/hops.py`, `rag/answer.py` and `rag/ontology_facts.py` have no heading imports or references. `ontology/grays.py`, `rag/chunk.py` and others only contain the English word.
- `tests/test_deploy_imports.py` still passes (2 tests). `rag/headings.py` imports only `ontology.merge` (shipped), `rag.atlas` and `rag.ontology_facts`.
- Deploy note: `deploy/build_hf_bundle.py` copies all of `rag/` and all of `data/graph/` except the LLM caches. That means `rag/headings.py` and the 2.3 MB `headings.jsonl` will ship in the HF bundle even though they are unused. Harmless, but decide whether to exclude them.
- Value of `tests/test_headings_leak.py` (16 tests):
  - Barrier 1 (tier invariant) is meaningful, but it hardcodes `3135`, `605`, `1221` and `1309`. The next Gray's re-split or toc change will break it for no good reason.
  - Barrier 2 (no heading rows in the ontology) is meaningful but loose. Its `"rule" in method` check is a weak signal.
  - Barrier 3 (AST) is meaningful but only covers direct imports in `hops.py` and `answer.py`. The extra string check `"headings." not in src` can false-fail on any word ending in "headings." in a comment.
  - Barrier 4 (poison) monkeypatches every callable and runs `hops.plan`. It proves `hops` does not call it at runtime, which is meaningful, but it needs retrieval and an LLM or backend to be available and may be slow or flaky.
  - Barrier 5 is a **tautology**. It builds a string from a literal and asserts that the literal contains no forbidden words. It tests no production code and should be deleted or replaced with a real `graph_block` test.
  - A stronger and simpler guard is one test: walk every `rag/*.py` except `headings.py` and assert none imports `rag.headings`, directly or via `from rag import headings`.

## 4. Code quality

- **Size.** 760 lines for what is, in value, a classifier plus a loader. The query APIs are fine. The module-level regexes and the classifier are about 250 lines and are the part that does the work.
- **Dead or duplicated code.**
  - Line 353 has a vacuous condition: `n_children >= 0 and (n_children > 0 or CLASSWORDS.search(h))`. It is equal to `CLASSWORDS.search(h)`.
  - Lines 528 to 529 assert `tier in (...)` and then assert `tier != "T1"`. The second is redundant.
  - `ORGANWORDS` is used for Guyton and Robbins/Davidson typing only. It produces an `AnatomicalStructure/Process` and a `Topic?` type that nothing consumes. The `ctype` it computes is not written to the file at all (the record has no type field). So the entity typing code (about 80 lines) has no output.
  - `slugify` truncates to 50 characters, so heading ids can collide on long paths. There were 0 collisions in this data, but nothing checks it.
- **Duplication.**
  - `rag/concepts.py` and `rag/mentions.py` do not cover headings. There is no real duplication except `_entity_index()`, which rebuilds the label index that `concepts._index()` already builds (a second full pass over `facts()`).
  - Both `match_heading` and `relaxed_match` exist, but `relaxed_match` is never called in the build (47 relaxed matches in the plan are not produced by a separate pass; they are partly absorbed by `atlas.variants`). I confirmed the 13 variant matches in the file.
- **Hardcoded paths.** `PATH = Path("data/graph/headings.jsonl")` and `Path(f"data/okf/{b}/toc.json")` are relative to the working directory, as elsewhere in the repo. `BOOKS` is a fixed tuple. `eval/heading_metrics.py` also uses relative paths and a `sys.path.insert` hack.
- **Regex misclassification risk.**
  - "Joints" as a drug is **blocked**, by the facet filter.
  - `CONDWORDS` includes loose stems (`osis`, `oma`, `pain`, `stone`, `cough`), so "Stomach"-like organ headings are safe but physiology headings are sometimes typed as conditions. The type is not persisted, so no harm in the file.
  - `FACET_EXACT` includes "bone", "fascia" and "contents". The plan says a body-part heading at region level should stay an entity. Gray's "Fascia" (×3) and "Bone" are turned into facets, losing a few real structures. "Peritoneum" and "Heart" correctly stay entities.
  - `FRONT` treats any single letter and "index" as structural. OK in this data.
  - `STATEMENT` plus 6 words marks Gray's headings as procedural. Fine for 15 records.

## 5. What it would take to make it useful in the app

Smallest first. Estimates are for one person.

1. **Fix the five defects above** (type guard for single candidates, strip possessives for matching, strip "17a.", delete tautology test, drop hardcoded counts): about 2 to 3 hours.
2. **Run the plan's 100-link primary-topic audit** and record the result in `reports/`: 1 hour. Without this the 90% bar is unproven.
3. **Topic page in Explore** (a "discussed in" panel: heading, section links, parent chain, facets as chips, "also in" other books via `cross_book_headings`). The data is already there through `section_heading`, `subtopics`, `facets_for` and `headings_for_concept`. It would need a single call into `rag/concepts.py` to join certified facts. It must label itself as navigation ("discussed in", never "the book says"): about 1 day, including a test that no non-certified fact text is shown as a claim.
4. **Eponym aliases, such as Erb's palsy** (plan Rule 10). The heading file does not contain these (Gray's never says "Erb"). That needs the curated or LLM alias table (about 400 pairs, about $0.05, plus a 100-pair human spot check) and query-time expansion in retrieval. Estimate 1 day, behind a flag. Headings alone will not fix that miss.
5. **Stage B (LLM pass)** to type entities, canonicalise names and split "X and Y": 3 days, about $0.15 to $0.30. This is what turns the 1,221 T3 entities (about 70% typed correctly) into the roughly 900 usable concepts.

## Top issues, in one list

1. Wrong-type single-candidate match ("Pulmonary valve" to a replacement-procedure node). There is no type guard.
2. Tautological Barrier 5 test, and hardcoded record counts that will break on the next toc change.
3. 70% entity accuracy: topic and facet headings labelled `entity` (11 of 40 in my sample).
4. Possessive eponyms not matched (3 headings) and Tripathi "17a." numbering not stripped (8 headings).
5. One toc section (Tripathi "Maturation Factors > Uses") has no heading record.
6. Dead typing code, a vacuous condition, and `headings.jsonl` plus `rag/headings.py` shipping in the deploy bundle although unused.
7. The plan's 100-link primary-topic audit was never run.

Dead ids: **0**.
