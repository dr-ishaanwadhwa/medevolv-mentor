# Ontology relationships: audit and reinforcement plan

Status: **plan only, nothing run yet.** Measured 2026-11-13 on a snapshot of `data/ontology/clinical_ontology.jsonl`
(written 00:18 by the "finish ontology pilot" session after commit 6fe8492) and on an in-memory re-reconcile of the
extraction cache, which makes no LLM calls. This file has counts only. It holds no textbook quotes.

## 1. Tier A run: incomplete

| | sections | extracted (cached) | left |
|---|---|---|---|
| Tier A (`reports/ontology_tierA.txt`) | 642 | 450 | **192** (155 Robbins, 37 Harrison ch. 460+) |
| all ranked (`reports/ontology_sections_all.txt`) | 742 | 550 | 192 |

- The 192 sections still to do are exactly the ones in `reports/ontology_failed.txt`; the run stopped on the usage limit. No backup jsonl
  was found in the repo. The extraction cache in `data/ontology/cache/` is the real backup, because `--rebuild` regenerates the jsonl from it for free.
- About 0.95M words (roughly 1.3M input tokens) remain, which is **≈ $1–2 of DeepSeek**. (Assumed pricing: about $0.28/M input and $0.42–1.10/M output. Check it against the current DeepSeek price page.)
- To resume (needs approval; cached sections are skipped automatically):
  `python -m ontology.builder --sections-file reports/ontology_failed.txt --workers 4`
  Run it with `LLM_BACKEND=deepseek`, and only when no other session is writing the jsonl.

## 2. Measurements

**Size.** 570 sections gave 22,244 raw items. 21,306 were kept after the gates. After the compiler's dedup there are **19,691 facts:
19,195 CERTIFIED (97.5%) and 496 CANDIDATE**.

**Gate outcomes (share of raw items).** Wrong types dropped: 725 (3.3%). Swapped: 272 (1.2%). Negated and dropped: 126.
FIRST_LINE downgraded: 118. Low confidence: 81. Self-contradictory: 6. Quote not found (CANDIDATE): 547 (2.5%).

**By predicate.** Every predicate is 95–99% certified. TREATED_BY 6,587 · MANIFESTS_AS 4,039 · CONFIRMED_BY 2,628 ·
CAUSED_BY 1,746 · DISRUPTS_PATHWAY 1,227 · CAUSES_ADVERSE_EFFECT 950 · HAS_CLINICAL_STAGE 725 ·
TARGETS_MECHANISM 641 · CONTRAINDICATES 626 · DIFFERENTIAL_OF 323 · is_a 199.

**By book.** Heavily skewed toward Harrison: Harrison 17,292 · Robbins 1,072 · Tripathi 727 · Davidson 462 (**79% certified**, the
weakest) · Micro 123 · Guyton 15.

**Entities.** 15,400 certified nodes. **Only 6.5% resolve to BODHI IDs; the rest are minted.** 10,529 nodes (68%) appear in only one fact.
- 754 near-duplicate groups cover 1,600 IDs: plurals (Glucocorticoid/Glucocorticoids, Fever/Fevers), qualifiers (Asthma/Acute
  asthma, Dengue/Dengue fever) and type splits. **459 labels carry more than one type**, for example a drug typed as both
  EtiologicalAgent and TherapeuticAgent, or Pregnancy appearing under three types.
- 22 minted labels differ from a BODHI name only in punctuation or hyphens (e.g. "Graves' disease", "Deep-venous thrombosis").

**Conditions.** 3,880 conditions appear as subjects. 2,255 (58%) have two facts or fewer, and 424 have ten or more. Among the 944 conditions with five or more facts, this many have each key predicate:
TREATED_BY 88% · MANIFESTS_AS 81% · CONFIRMED_BY 73% · CAUSED_BY 54% · **CONTRAINDICATES 18%**.
- line_of_therapy on TREATED_BY: FIRST_LINE 2,430 · none 2,541 · ADJUNCT 567 · SUPPORTIVE 491 · SECOND_LINE 354 · REFRACTORY 35.

**Cross-book.** `compiler.save_compiled_facts` dedups on (subject, predicate, object) and **keeps a single provenance**. The
jsonl therefore cannot show corroboration, so I measured it before dedup:
- 729 triples are supported by 2 or more sections, and **249 by 2 or more books** (93 TREATED_BY, 54 MANIFESTS_AS, 40 CAUSED_BY).
- 367 conditions are covered by 2 or more books. **60 conditions have FIRST_LINE drugs from 2 or more books, and in all 60 the sets don't overlap.** Most of this
  is naming and granularity (insulin vs regular insulin, "antimicrobial TB therapy" vs rifampin), not real disagreement.
- **60 (condition, drug) pairs are both TREATED_BY and CONTRAINDICATES.** Some are real nuance tied to a subgroup or timing. Others
  are errors.

**BODHI alignment.** 994 of 15,400 ontology nodes are BODHI nodes, and 237 of BODHI's 755 Conditions have ontology facts.
- MANIFESTS_AS against BODHI PRESENT_IN: of 264 pairs with both ends in BODHI, 86 match (33%). For the same conditions BODHI has
  about 1,600 symptom links the ontology does not reach, mostly because ontology symptoms are minted and unresolved.
- BODHI's TREATED_BY points to *specialities*, not drugs, so it can't be compared with the ontology's TREATED_BY.

**Precision sample.** 30 CERTIFIED facts, stratified by predicate, each checked by hand against its quote:
- **26/30 triples supported (≈87%; 95% CI roughly 70–95%).** 3 of the 26 are only partly supported.
- Error patterns:
  1. A table row of adverse effects read as TREATED_BY.
  2. Subject drift: a craving drug attached to cirrhosis instead of alcohol use disorder.
  3. A test that is part of a workup labelled CONFIRMED_BY.
  4. A metabolising enzyme labelled TARGETS_MECHANISM, taken from a table fragment.
- One FIRST_LINE label was not stated in its quote. The quote check proves the text exists. It does not prove that the text supports the triple.

## 3. Reinforcement options

Costs are DeepSeek estimates. Bulk labelling or review work goes to haiku subagents.

| # | Option | Expected gain | Cost | Risk |
|---|---|---|---|---|
| A | **Keep all provenances in the compiler** (list of sources per triple, not one) | Unlocks corroboration (B) and the contradiction view (F). The 249 multi-book triples become visible. | $0, small code change | Low. The jsonl format changes, so `rag/ontology_facts.py` must read a list. |
| B | **Corroboration score**: count of books and sections, shown as "confirmed in 2 books" and used to rank drill-down items | Better ordering and student trust | $0 | Low |
| C | **Entity resolution, deterministic**: plurals, punctuation, "X fever"→X, a type-preference rule (drug→TherapeuticAgent), more BODHI synonym matching | Merges ~800 IDs, lifts BODHI share, improves B and F | $0 | Medium. Bad merges can conflate concepts (asthma ≠ acute asthma for therapy). Merge only exact-after-normalisation cases. Review the list of merges. |
| C2 | Entity resolution with an LLM over the ~750 near-dup groups (yes/no per group) | Catches synonyms rules miss | ≈ $0.10 | Medium. Spot-check 50 groups. |
| D | **Verifier pass**: a second prompt asks "does this quote state this triple? yes/no/partial" for TREATED_BY, CONFIRMED_BY, CONTRAINDICATES and FIRST_LINE, then demote failures to CANDIDATE | Targets the 13% error in §2. Expected precision ≈ 93%+ | ≈ $1–3 for ~10k facts, batched 20 per call | Low. It only demotes and never adds. Recall loss is a few %. |
| D2 | Re-check the 496 CANDIDATE facts with fuzzy quote matching or the verifier | Recovers some of the 2.5% | < $0.10 | Low |
| E | **Finish Tier A** (192 sections) | +~6k facts, more Robbins pathology | ≈ $1–2 | Low. Uses the same gates. |
| E2 | Gap-fill thin, high-value conditions: targeted CONTRAINDICATES and MANIFESTS_AS extraction for the top ~100 exam conditions from Tripathi and Davidson | CONTRAINDICATES coverage 18% → ~50% for those | ≈ $1 | Low |
| F | **Contradiction flags**: TREATED_BY+CONTRAINDICATES on the same pair, and FIRST_LINE sets that differ across books *after* C. Shown to students as "books differ: see both". | Teaching value, plus it surfaces errors | $0 (+ a haiku triage pass) | Medium. It must not look like an error to students. Wording matters. |
| G | **Inferred edges**: is_a inheritance (subtype inherits parent's MANIFESTS_AS) and drug class → member (needs class membership edges, which are rare today: only 199 is_a) | More answers for thin conditions | $0 | **High.** Inheritance is often clinically wrong (a subtype's first-line drug ≠ parent's). Keep inferred edges in a separate, labelled layer and do not use them in answers. |
| H | **Gold set**: ~150 hand-checked triples over 15 gold conditions, scored for precision and recall after every rebuild (`tests/` or `reports/`) | Tracks quality over time and stops regressions | ≈ 2 h of review (haiku draft, user confirms) | Low. It must stay out of git if it carries quotes. Store triples only. |

### Recommended order
1. **A + B + C** (free, code-only) → re-measure.
2. **D** (verifier, ~$2) and **H** (gold set), so precision is measured rather than estimated.
3. **E** (finish Tier A, ~$2), then **F**.
4. E2, C2 and D2 if gaps remain. **G only as a separate, opt-in layer.**

Total for steps 1–3 is roughly **$5 or less in DeepSeek**.

## Coordination
The "Finish ontology pilot: eval, UI check, deploy" session is editing `ontology/reconciler.py` and
`rag/ontology_facts.py` and rewriting the jsonl. Options A, C and D touch the same files, so run them after that session lands, or in
one session at a time.
