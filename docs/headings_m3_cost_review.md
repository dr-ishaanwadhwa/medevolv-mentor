# Headings plan, Milestone 3: gap-fill cost review (dry run, $0 spent)

Date: 2026-11-13. Nothing was sent to an LLM, nothing under `ontology/` or `data/ontology/` changed, no schema was applied.
Reproduce with `.venv/bin/python scripts/plan_anatomy_relations.py` (writes `reports/anatomy_relations_plan.json`, counts only,
no textbook text). Guard rules are pinned by `tests/test_plan_anatomy_relations.py`.

## 1. Price assumptions (and where they come from)

| Name | Input $/M | Output $/M | Source |
|---|---|---|---|
| repo assumed | 0.28 | 0.42 | `ontology/gapfill.py` `PRICE_IN/PRICE_OUT`, same in `ontology/verifier.py` and `ontology/grays.py` (imported). The plan doc says the same. |
| pessimistic | 0.56 | 1.68 | `scripts/build_hubs.py` (deliberately pessimistic cap) |
| plan upper | 0.56 | 1.10 | output price the older plans allow |

`rag/backends.py` has no prices (it only routes calls). Tokens use the repo convention `chars // 4`. All totals add 15% for retries
(the repo cache stores only successes, so a failed call is paid again). Recheck the DeepSeek price page before any real run.

## 2. Stage C (Rule 9): Gray's anatomy relations

### 2.1 Target selection (what the script does)

- Source: the 614 Gray's sections. The 102 "Clinical cases" sections are skipped (`ontology/grays.py` already reads them whole), leaving 512.
- A passage is a **heading-scoped block**: the `###`/`####` blocks of one section, "In the clinic" boxes removed (already extracted),
  figure-label paragraphs removed (heuristic: at most 6 words and no closing punctuation; 446 removed), neighbouring blocks of the
  same section merged until about 450 words, cap 700. A passage never leaves its section, so it never crosses a region.
- A passage is a **target** only if it contains a relation cue (supplied by, innervat-, drain-, bound-, contains / passes through, branch of / arises from...).
  Without a cue the call would return nothing. Cue regexes are in the script.

| Item | Value |
|---|---|
| Passages built | 776 (avg 401 words) |
| Passages targeted | **690**, in 462 of the 512 sections |
| Skipped, no cue | 86 |
| Words targeted | 276,747 |
| Passages by cue (overlapping) | BRANCH_OF 419, CONTAINS 359, BOUNDED_BY 357, INNERVATED_BY 241, SUPPLIED_BY 158, DRAINED_BY 138 |
| Passages by region | Head and Neck 226, Lower Limb 91, Upper Limb 85, Abdomen 80, Thorax 71, Pelvis 58, Neuroanatomy 28, The Body 27, Back 24 |

Sensitivity: merging only to 120 words (`--min-words 120`) gives 1,016 targeted passages and 1.69M input tokens; the fixed 1,186-token
system prompt (existing clinical prompt plus the proposed anatomy addendum) is repeated per call and is 62% of input at the default
size. Bigger passages are cheaper, which matches the plan's 500 to 700 words.

### 2.2 Tokens and cost

| Quantity | Value |
|---|---|
| Input tokens | 1.32 M |
| Output tokens | 0.31 M (15 facts per 1,000 words), 0.41 M (20 per 1,000 words), 0.41 M (repo guess of 600 per call) |
| Raw facts expected | 4,150 to 5,540 |
| Certified expected (90% pass) | 3,740 to 4,980 |
| Wall clock | about 38 minutes at 6 workers, 20 s per call |

| Price set | Extract + verify, with 15% retries |
|---|---|
| repo assumed | **$0.69 to $0.77** (0.74 on the 600-token guess) |
| pessimistic | $1.71 to $1.98 (1.91 on the 600-token guess) |
| plan upper (0.56 in / 1.10 out) | $1.68 |
| 40-passage pilot, repo prices | about $0.04 |

So the plan's "about $2" holds only as a ceiling: at the repo's own prices the full run is under $1. The certified-fact range (3.7k to 5.0k)
is lower than the plan's 4,500 to 6,500 because only cue-bearing passages are sent (277k words instead of the 366k the plan applied the rate to).
The 15 to 20 facts per 1,000 words rate is the plan's figure and is **not validated**: the pilot must measure it before the full run.
Cost is not the constraint; the audit and the gold set are (3 to 4 days of engineering per the plan).

### 2.3 Proposed schema additions (listed, not applied)

| File | Addition |
|---|---|
| `ontology/schema.py` `ClinicalRelation` | `INNERVATED_BY`, `SUPPLIED_BY`, `DRAINED_BY`, `BOUNDED_BY`, `CONTAINS`, `BRANCH_OF` (`PART_OF` already exists) |
| `ontology/schema.py` `ClinicalFacet` | `structure_kind` and `object_structure_kind` (muscle, nerve, artery, vein, lymphatic, bone, ligament, fascia, space, organ, system, region, joint, gland, skin, sheath), optional `spinal_levels`. No new EntityType. |
| `ontology/reconciler.py` `TYPE_RULES` | each new predicate (AnatomicalStructure, AnatomicalStructure), one direction; `PART_OF` allows OrganSystem on either end per the guard below |
| `ontology/reconciler.py` new gate | `check_anatomy_kinds` (section 3.3) plus a quote-cue gate: `BRANCH_OF` needs "arises from / branch of / given off", `PART_OF` needs "part / segment / component" |
| `ontology/verifier.py` `SYSTEM` | one definition line per new predicate |
| `rag/concepts.py` `INVERSE` | innervates, supplies, drains, bounds, contained in, has branch (wording fixed, never generated) |
| new `ANATOMY_ADDENDUM` | normal anatomy only, the mirror of `ontology/grays.py`'s clinical addendum |
| `eval/` | about 40 gold triples for the 14-question smoke set |

The full list is in the `proposed_schema` key of `reports/anatomy_relations_plan.json`.

## 3. Correction: PART_OF versus BRANCH_OF

Gemini's v2 plan used "coronary artery PART_OF ascending aorta". That is wrong. The coronary arteries arise from the aortic sinuses
of the ascending aorta and are **branches** of it (right coronary artery from the right sinus, left main from the left). They are separate named
vessels that leave the aorta. They are not components of it.

### 3.1 Semantics

| | PART_OF | BRANCH_OF |
|---|---|---|
| Relation | constitutive: the subject is a component or segment of the object | derivational: the subject vessel or nerve arises from the object |
| Test | remove the object and the subject goes with it; the subject is not a distinct vessel | the subject is a distinct named vessel or nerve with its own course and territory |
| Examples | left ventricle part_of heart; ascending aorta part_of aorta; aorta part_of cardiovascular system; lobe part_of lung | coronary artery branch_of ascending aorta; radial artery branch_of brachial artery; ulnar nerve branch_of medial cord |
| Kinds allowed | any structure; organs to systems; segments of one vessel | vessel to vessel of the same family, nerve to nerve (cord, trunk, plexus count as nerve) |
| Transitive | yes | no (lineage only; do not roll a grandchild up as a part) |
| Reading back | has part | has branch |

Related and not the same: `SUPPLIED_BY` (heart supplied by coronary arteries), `CONTAINS` (a space holds a structure that passes through it),
continuation ("subclavian continues as axillary") which is neither and is out of scope for this batch. Veins and lymphatics use `BRANCH_OF`
with the inverse wording "has tributary" in the UI; that wording choice is open.

### 3.2 Layout is not anatomy

Gray's section paths nest by chapter layout. For example the diaphragm sits under "Posterior abdominal wall > Bones" in the ToC. A heading
nesting must never be turned into `PART_OF`. This is why the Stage A `part_of_candidates` (T3) stay navigation-only and Stage C takes
relations only from sentences with a verified quote.

### 3.3 Guard rules (implemented in the dry-run script as `check_anatomy_kinds`, proposed for the reconciler)

| # | Rule | Result |
|---|---|---|
| G1 | `BRANCH_OF` needs both ends in {artery, vein, nerve, lymphatic} and **the same family** | otherwise drop (organs, muscles, systems do not branch; no artery branch of a nerve) |
| G2 | `PART_OF` between two vessels (or two nerves) of the same family is allowed only when the child is a named segment of the parent (all words of the parent appear in the child's name, plus a qualifier: Ascending aorta / Aorta) | otherwise drop, suggest `BRANCH_OF` if the quote says it arises from the parent. This is the "coronary artery part_of ascending aorta" case. |
| G3 | Organs, vessels, nerves, muscles, bones are `PART_OF` a system, never the reverse | system as subject: drop |
| G4 | A vessel or nerve is not `PART_OF` the organ it supplies | review: use `SUPPLIED_BY`, `INNERVATED_BY` or `CONTAINS` |
| G5 | `INNERVATED_BY` object is a nerve; `SUPPLIED_BY` object an artery; `DRAINED_BY` object a vein or lymphatic | otherwise drop |
| G6 | `BOUNDED_BY` and `CONTAINS` subject is a space, canal, region, sheath or organ | otherwise drop |
| G7 | Predicate-from-quote: the cue words in the verified quote must match the predicate (arises / branch for `BRANCH_OF`, part / segment for `PART_OF`) | otherwise drop |
| G8 | No self-relation; `PART_OF` and `BRANCH_OF` graphs must stay acyclic after merge | drop and log |
| G9 | `structure_kind` comes from the extractor; the name-based `infer_kind` is a fallback only and is not trusted for certification | |

Checked cases: PART_OF Coronary artery > Ascending aorta: drop. BRANCH_OF the same pair: ok. PART_OF Ascending aorta > Aorta: ok.
PART_OF Heart > Cardiovascular system: ok. BRANCH_OF Heart > Aorta: drop. BRANCH_OF Radial artery > Median nerve: drop.

## 4. Stage B: LLM typing of entity headings

Input: the `entity`-class rows in `data/graph/headings.jsonl`. There are **1,224** (the brief said about 1,227): Guyton 335, Gray's 275,
Harrison 263, Robbins 114, Davidson 113, Tripathi 68, Micro 56. One call per 40 headings (31 calls). Each heading is sent with its book and
parent path and answers `{kind: entity|class|topic|facet, type, canonical_name}`.

| Quantity | Value |
|---|---|
| Calls | 31 |
| Input tokens | about 52 k (450-token system prompt per call, about 25 tokens per heading) |
| Output tokens | about 56 k (45 per heading) |
| Cost, repo assumed prices | **$0.04** |
| Cost, pessimistic prices | $0.14 |
| Pessimistic plus an adjudication pass on 20% of headings | $0.17 |

This is under the plan's $0.05 to $0.10 (which covered about 1,600 headings including Gray's body headings, with more tokens per item). Output
size and system-prompt size are my assumptions; the price is certain only to the order of magnitude. Effort is dominated by the 100-item audit per class (plan bar: 90%).

## 5. Recommendation

- Total new LLM spend for Stage B plus Stage C: **about $0.8 at repo prices, about $2.1 pessimistic.** Spend is not the risk.
- Order: Stage B first (so extracted anatomy names resolve to heading concepts), then a 40-passage Stage C pilot on the diaphragm, inguinal canal,
  femoral sheath, carotid sheath, head of femur, rectal veins, superior orbital fissure and ureter passages.
- Go criteria from the plan stay: certified precision at least 90% on 100 sampled facts, and gold-triple recall on the smoke set.
- Before the pilot: implement G1 to G9 in the reconciler with tests, and write the 40 gold triples.
- Whatever Stage C produces reaches answers only as `status: CERTIFIED` facts through the normal gates. Everything from `headings.jsonl` stays navigation.
