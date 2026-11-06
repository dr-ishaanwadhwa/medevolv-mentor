# BODHI graphs: what's actually in them (checked 2026-11-07)

Source: Hugging Face `ekacare/BODHI-S`, `ekacare/BODHI-M`. License **CC BY-NC 4.0** (non-commercial, attribute Eka Care).
Fetch with `python -m ingest.fetch_bodhi`. Each repo has `triples.jsonl` (IDs only) and `nl_facts.jsonl`
(one English sentence per triple, e.g. `"Cobalamin deficiency (Concept) is treated by vit b12 (Drug)."`).
Node **names live only in nl_facts** — the loader must parse `Name (Type)` out of those sentences.

## BODHI-S — 13,204 triples (diagnosis side)
| Count | Edge |
|---|---|
| 10,352 | Symptom `PRESENT_IN` Condition (props: likelihood_condition_given_symptom / likelihood_symptom_given_condition) |
| 1,558 | Condition `TREATED_BY` Speciality |
| 1,020 | Condition `IS_INFLUENCED_BY` Condition |
| 221 | Symptom `RELATED_TO` Symptom |
| 53 | Condition `HAS_PREREQUISITE` Condition |

## BODHI-M — 3,566 triples (drugs and labs)
| Count | Edge |
|---|---|
| 1,768 | Concept `CHILD_OF` Concept (SNOMED hierarchy) |
| 908 | Concept `TREATED_BY` Drug (prop: exclusivity) |
| 808 | LabInvestigation `IMPACTS` Concept |
| 82 | Concept `MONITORED_BY` LabInvestigation |

## Linking S and M
- Conditions (S) and Concepts (M) share SNOMED IDs: **289 overlap** out of 755 conditions.
- **92** conditions have a drug directly; **208** have one via a `CHILD_OF` ancestor.
- Drugs are specific agents ("abiraterone acetate"), not drug classes, and edges carry no "first-line" signal.

## Design consequence
The graph can propose candidate drugs for ~28% of conditions, but **the textbook (pharmacology) remains the source
for "first-line" / drug class / mechanism**. The graph drug list is used as a cross-check on the textbook answer,
and for the other ~72% of conditions the treatment hop is textbook-only.
