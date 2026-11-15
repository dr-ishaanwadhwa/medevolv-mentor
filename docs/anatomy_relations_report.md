# Gray's anatomy relations (Stage C / Rule 9): report

Date 2026-11-14. Branch `anatomy-relations` (worktree `med-rag-anatomy`). Not deployed, not pushed. The facts live in the worktree's
`data/ontology/clinical_ontology.jsonl` (git-ignored, never committed); a copy of the file from before this work is
`clinical_ontology.pre-anatomy-20261114.jsonl` next to it. Main's `data/ontology` was not touched.

## What was built

- `ontology/schema.py`: INNERVATED_BY, SUPPLIED_BY, DRAINED_BY, BOUNDED_BY, CONTAINS, BRANCH_OF (PART_OF already existed, value `part_of`);
  optional facets `structure_kind`, `object_structure_kind`, `spinal_levels`.
- `ontology/reconciler.py`: type rules (structure to structure; PART_OF may end at a body system) and the guard gate.
- `ontology/anatomy.py`: guard rules G1-G9, the anatomy prompt, the runner (`python -m ontology.anatomy [--pilot N] [--part-of]`).
  Heading-scoped passages come from `scripts/plan_anatomy_relations.py` (690 targets). Calls are cached in `data/ontology/cache_anatomy/`;
  `builder --rebuild` re-adds them with no LLM call.
- Guards: G1 BRANCH_OF same vessel/nerve family only; G2 same-family PART_OF only for a named segment (so "coronary artery PART_OF ascending aorta"
  is dropped and "coronary artery BRANCH_OF ascending aorta" is kept); G3 a system is never part of a structure; G4 vessel/nerve PART_OF organ goes
  to a hidden CANDIDATE; G5/G6 object/subject kind rules per predicate; G7 the verified quote must carry a cue word for the predicate and name the
  object; G8 no self-relation, and PART_OF/BRANCH_OF stay acyclic after the merge (`compiler.save_compiled_facts`); G9 kinds come from the extractor,
  a fact whose kind had to be inferred from the name is never certified. Heading nesting is never turned into PART_OF (prose only).
- Existing gates are unchanged: quote must be found verbatim in the passage, then the DeepSeek verifier (yes/partial/no, "no" demotes), entity
  merges, multi-source merge. The verifier prompt got one line per new predicate.
- **Kept out of answers:** `rag/ontology_facts.py` `facts()` now hides `ANATOMY_PREDICATES`; `all_facts()` / `anatomy_facts()` add them back for
  `rag/concepts.py` only (concept pages, with INVERSE names: innervates, supplies, drains, bounds, contained in, has branch, has part).
  `graph_facts_for`, hops, atlas, diagrams, headings and `scripts/graph_metrics.py` still read `facts()`.
- Tests: `tests/test_anatomy_relations.py` (guards, reconciler, cycle drop, hidden from answers, INVERSE for every predicate);
  `tests/test_deploy_imports.py` passes (no served module imports `ontology.anatomy`). Full suite: 186 passed.

## Counts (CERTIFIED unless noted)

| Predicate | Certified |
|---|---|
| INNERVATED_BY | 573 |
| part_of | 505 |
| BRANCH_OF | 472 |
| BOUNDED_BY | 379 |
| CONTAINS | 375 |
| SUPPLIED_BY | 221 |
| DRAINED_BY | 118 |
| **Total** | **2,643** (plus 159 hidden CANDIDATE) |

Verifier: 2,530 yes, 113 partial; 382 facts have two or more source sentences. Raw extraction was 5,708 triples (first pass) plus the PART_OF pass;
about 4,000 were dropped by the gates (largest causes: quote without a cue word for the predicate, wrong kind for the predicate (mostly the model
writing the relation backwards), quote not naming the object, low confidence). The cost review's 3.7k to 5.0k estimate was therefore too high: 2.6k certified.
The plan's 15-20 facts per 1,000 words was optimistic for certified facts (about 9.5).

## Precision (sonnet audits of seeded random samples of CERTIFIED facts, plus my own spot check)

| Audit | Sample | Correct |
|---|---|---|
| Pilot (40 passages, gate) | 100 of 209 | **96%** (96 correct, 2 incorrect, 2 unsure). My own check of 25 of them found 4 loose "kidney BOUNDED_BY neighbour" facts; still above 90% |
| Full run, before tightening | 100 of 2,292 | 88% (BOUNDED_BY from adjacency was the main error) |
| After tightening BOUNDED_BY | 100 of 2,177 | 89%; 90.8% once the facts removed afterwards are excluded (re-scored, not re-audited) |
| **Final, complete set (incl. part_of)** | 100 of 2,643 | **96%** (96 correct, 2 incorrect, 2 unsure) |

Fixes made between audits (all deterministic, no extra LLM calls): BOUNDED_BY needs boundary vocabulary in the quote and a space/region subject
(organs only "lay next to" things); object must be named in the quote. The remaining known weak spots: "continuation" read as BRANCH_OF (kept; the
label is "branch of"), CONTAINS where the sentence says a structure is surrounded, one part_of read the wrong way round. The audit sample rows hold
textbook quotes, so they are kept outside the repo.

## Bugs found on the way

The anatomy prompt's `PART_OF` did not match the enum value `part_of`, so the first full pass silently lost every PART_OF triple. Fixed with a
case-normalising validator and a PART_OF-only second pass (552 passages), then the gate compared the wrong case; fixed and rebuilt from cache.

## Cost (DeepSeek at the repo's assumed prices, chars/4)

| Step | USD |
|---|---|
| Pilot, 40 passages (extract 0.043, verify 0.005) | 0.05 |
| Full run, 650 more passages (extract 0.642, verify 0.064) | 0.71 |
| PART_OF pass, 552 passages | 0.33 (+ a few cents verifier) |
| **Total** | **about 1.1** (cap was 2.0; subagent audits not counted) |

## Ten example facts (labels only)

1. Diaphragm INNERVATED_BY Phrenic nerve
2. Right coronary artery BRANCH_OF Ascending aorta (and Left coronary artery; "Coronary artery PART_OF Ascending aorta" does not exist)
3. Head of femur SUPPLIED_BY Acetabular branch of obturator artery
4. Inguinal canal CONTAINS Genital branch of the genitofemoral nerve
5. Axilla CONTAINS Brachial plexus
6. Levator scapulae muscle INNERVATED_BY Dorsal scapular nerve
7. Oropharyngeal triangle BOUNDED_BY Superior constrictor muscle of the pharynx
8. Neck BOUNDED_BY Mandible
9. Head of pancreas part_of Pancreas
10. Diaphragm SUPPLIED_BY Superior phrenic artery

## Before / after

| Measure | Before | After |
|---|---|---|
| Certified facts in the compiled file | 25,902 | 28,545 (25,902 + 2,643) |
| Facts that can reach answers (`facts()`) | 25,902 | 25,902 |
| `graph_facts_for` over all 5,001 condition labels (hash) | c0ac851e | c0ac851e (identical) |
| `scripts/graph_metrics.py` output | | byte-identical (it reads answer-side facts) |
| Gold set (`ontology.gold`): precision / recall / recall_added | 0.941 / 0.914 / 0.714 | 0.941 / 0.914 / 0.714 |
| Anatomy smoke (14 questions, answer_multihop, DeepSeek) | all 14 same status, same graph facts | same; one question cited a different book set in one run and the same in another (LLM sampling) |
| Graph including anatomy (concept pages only) | 20,342 nodes, 1,444 components | 22,023 nodes, 1,521 components; only 154 of 1,835 anatomy nodes touch the clinical graph |

Note: the anatomy facts form a mostly separate island. "MI has no route to the right coronary artery" is still true: RCA is now reachable from
its own structures (sinu-atrial node, coronary sulcus, aorta), but no certified condition fact links Myocardial infarction to it. That needs
INVOLVES_STRUCTURE links or alias resolution, and a deliberate decision to let anatomy facts into answers (they are hidden by `ANATOMY_PREDICATES`).

## Not done / follow-ups

- The cost review's 40 hand-written gold triples for the smoke set were not written; the smoke check here is "no regression", not recall.
- Anatomy facts reach concept pages only; no UI was changed or checked.
- The audits are sonnet judgements of 100 facts each (about plus or minus 6 points), not an expert review.
