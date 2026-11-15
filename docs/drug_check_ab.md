# DRUG_CHECK A/B: adversarial clinician review and evals

Date: 2026-11-14. Compares the same adversarial reviewer prompt over the 18 hard vignettes (3 runs each),
without the post-answer patient drug check (BEFORE) and with `DRUG_CHECK=1` (AFTER, `rag/drug_check.py`
as of 18:32:57). Raw AFTER runs: scratchpad `drugcheck/` (`<id>.json`, `hard_run{1,2,3}.json`, `product.json`).

## Per-case severity and clean runs

| Case | Before | Clean before | After | Clean after | Change |
|---|---|---|---|---|---|
| c01 | minor | 0/3 | major | 0/3 | **worse** (check inverted PTU→methimazole switch, stripped pregnancy drug plan) |
| c02 | major | 0/3 | major | 0/3 | same (check banned allopurinol, left its dosing; lost azathioprine dose-reduction route) |
| c03 | minor | 0/3 | minor | 0/3 | same (check flagged "urea", deleted the urea breath test in run 2) |
| h01 | major | 0/3 | major | 0/3 | same (missed morphine; ACE-i still first-line at 82/50) |
| h02 | major | 0/3 | major | 0/3 | same (missed esmolol/labetalol trap in run 3; garbled differential) |
| h03 | **none** | **3/3** | major | 2/3 | **worse** (false rule: phenoxybenzamine ruled out on "severe_hypertension") |
| h04 | major | 0/3 | major | 0/3 | same, but check *created* the run-1 harm (thionamide and iodine "avoided") |
| h05 | major | 0/3 | major | 0/3 | same, but check removed insulin 9x, leaked scaffolding ("Sentences to fix:") |
| h06 | major | 0/3 | major | 0/3 | same (atropine flagged as ruled out for bradycardia) |
| h07 | major | 0/3 | major | 0/3 | same (bronchodilators removed from first-line list) |
| h08 | major | 0/3 | major | 1/3 | slightly better count, but check stripped labetalol/nicardipine in run 1; run 2 "insufficient" |
| h09 | major | 0/3 | major | 0/3 | same (steroids "avoided" for a non-existent contraindication) |
| h10 | major | 0/3 | major | 0/3 | same (etiology for ACE-i/spironolactone replaced by orphan fragments) |
| h11 | major | 0/3 | major | 0/3 | same (digoxin flagged from "stop digoxin" lines; Fab sentence beheaded) |
| h12 | minor | 0/3 | minor | 0/3 | same (antibiotics flagged as ruled out in run 2) |
| h13 | minor | 2/3 | minor | **0/3** | **worse** (artemisinin false positive; ACT follow-on lost) |
| h14 | minor | 2/3 | major | 2/3 | **worse** (epinephrine flagged as ruled out; "Drug of choice" line deleted) |
| h15 | major | 0/3 | major | 0/3 | same, but run 2 "Acetylcysteine is avoided here" is a check artefact (trap-t1 harm) |

## Totals

| | Major | Minor | None | Clean runs (of 54) |
|---|---|---|---|---|
| Before | 12 | 5 | 1 | 7 |
| After | 15 | 3 | 0 | 5 |

No case improved in severity. Three cases regressed (h03 none→major, c01 minor→major, h14 minor→major);
h13 lost both clean runs. Every one of the 18 cases has a `check_damage` entry from the reviewer.

## Eval comparison

| Metric | Before (3 runs) | After run 1 | run 2 | run 3 | After mean |
|---|---|---|---|---|---|
| Rubric recall | 0.827 | 0.835 | 0.826 | 0.835 | 0.832 |
| Pharmacology recall | 0.715 | 0.729 | 0.708 | 0.750 | 0.729 |
| Traps hit | 2 | 0 | 0 | 3 | 3 total |
| Refusals / errors | 0 | 0 | 0 | 0 | 0 |
| Groundedness | 0.977 | 0.963 | 0.954 | 0.966 | 0.961 |
| Hard-eval latency p50 | n/a | 10.31 s | 10.35 s | 9.94 s | ~10.2 s |

| Product eval | Before | After (base) | After (multihop) |
|---|---|---|---|
| Right behaviour | 39/39 | 38/39 (q24 → insufficient) | 39/39 |
| Fully grounded | 30/30 | 27/29 | 28/30 |
| Latency p50 | ~2.75 s | 2.37 s | 2.76 s |

Reading: rubric/pharmacology recall moved inside run-to-run noise (+0.005 / +0.014); groundedness fell
about 0.016 and fully-grounded answers fell by 2-3. The keyword rubric does not see the damage the reviewer
sees (orphan doses, inverted recommendations), because the drug names often survive somewhere in the text.
Traps did not go down (3 in run 3 vs 2 baseline). The checker fired in 47/54 runs, 233 "conflicts", with
c01/c02/h11 at 9-14 per run.

## Notable check_damage (by root cause)

1. **Avoid/Warnings lines read as recommendations.** "Stop digoxin", "avoid giving iodide before the
   antithyroid drug", "PTU avoided in children", "avoid delaying antibiotics" each made the named drug
   "recommended" and then "ruled out" (h04, h11, h12, h09, c01, c02). This is the single biggest source of
   false conflicts.
2. **Wrong patient rules.** phenoxybenzamine ruled out by severe hypertension (h03), atropine by
   bradycardia (h06), epinephrine in anaphylaxis (h14), bronchodilators in asthma (h07), insulin in DKA
   (h05), artemisinins from a prophylaxis-only warning (h13), labetalol/nicardipine in eclampsia (h08).
   The check removed the first-line drug in each of these.
3. **Non-drugs parsed as drugs.** "pregnancy" (c01, h08), "intravenous" (h05), "urea" in urea breath test
   (c03).
4. **The rewrite garbles text.** Orphan doses with no drug ("...; or 10-20 mg orally 3-4 times daily"),
   lowercase fragments ("it is avoided in this patient [6][9]."), sentences cut mid-word, "until the stated
   contraindication resolves" pointing at nothing, and leaked pipeline text ("Sentences to fix:",
   "the graph facts do not name a specialist").
5. **Misses the real conflicts.** h01 morphine in RV infarct, h02 esmolol/labetalol after cocaine (trap
   t1, run 3 "no conflicts"), h11 calcium/isoproterenol in digoxin toxicity, h05 insulin before K+ ≥3.3.

## Failure patterns the check does not cover (would remain even with a perfect checker)

- **Invented findings / severity misgrading:** "inferolateral" with no lateral leads (h01), "active eye
  disease" not in vignette (c01), "all present here" with HR not given (h01), mild-moderate asthma step for a
  life-threatening attack (h07).
- **Wrong doses and units:** pralidoxime 8-10 g/kg/h (h06), diazepam every 3-5 *hours* (h02), digoxin in
  mmol/L (h11), nonstandard NAC regimens (h15), Harrison-wrong bicarbonate threshold (h05).
- **Omissions of rubric actions:** no succinylcholine warning (h06), no glucagon for beta-blocked
  anaphylaxis (h14), no K+ ≥3.3 rule (h05), no insulin/glucose for K 7.4 (h10), no calcium gluconate
  antidote (h08), no ACT follow-on (h13). The check only deletes or rewrites, so it cannot add these.
- **Off-patient source transfer:** CCB-poisoning management applied to digoxin (h11), MELD for acute
  paracetamol failure (h15), "first-line options... check each against this patient" lists that include
  irrelevant drugs (acyclovir/ART in h12, teprotumumab in c01, lidocaine in heart block in h11).
- **Diagnosis hedging:** "a differential to consider, not a diagnosis" for confirmed DKA, phaeo, H. pylori.

## Decision: keep DRUG_CHECK off and iterate

Do not enable it by default, and do not deploy it before or after the demo in its current form. Next fixes,
in order:

1. Skip sentences that are themselves Avoid/Warnings/contraindication statements (negation and "stop/avoid/
   do not" scope) when collecting "recommended" drugs.
2. Require a patient finding to be an explicit contraindication *for that drug* in the ontology (drug →
   contraindicated_in → finding), and add an indication allow-list so a drug indicated for the presenting
   condition (atropine/OP, epinephrine/anaphylaxis, insulin/DKA, phenoxybenzamine/phaeo) is never ruled out.
3. Restrict drug recognition to real agents: drop "pregnancy", "intravenous", "urea", and class words like
   "bronchodilator" unless they appear as a recommended agent.
4. Replace in-place sentence rewriting with flag-only: keep the answer text and add a separate "Safety
   notes" block (or a single LLM regenerate with the conflict list), so no orphan doses or fragments.
5. Add a damage gate: if the check reports more than ~3 conflicts or removes a drug the graph lists as
   first-line for the axis, discard the revision and keep the original answer.
6. Re-run the 18-case reviewer A/B and hard eval; enable only if no case regresses in severity, groundedness
   is back to ≥0.975, and h02/h05/h10 traps drop.
