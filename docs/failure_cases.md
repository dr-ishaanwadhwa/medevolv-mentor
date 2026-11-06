# Failure cases (observed during the build, 2026-11-07)

Each case: what happened → root cause → what we changed or would change. Re-run the examples with
`python -m rag.answer [--hops] "<question>"` and `python -m eval.run_eval retrieval`.

## 1. Comparison question retrieved one side only
**Question:** "Compare the mechanism of action of penicillins and aminoglycosides."
**Observed (baseline):** 5 of 6 retrieved passages were about aminoglycosides; penicillins had one.
**Cause:** a single embedding of a two-topic question lands nearer whichever topic dominates the vector space.
**Fix (built):** query decomposition — the question is split into one sub-question per drug class and each is
retrieved separately. After the fix: penicillin passages [1],[3] and aminoglycoside passages [4]–[7].
**Category:** retrieval.

## 2. Small model stated a false similarity (unfaithful answer)
**Question:** same comparison, after decomposition fixed retrieval.
**Observed:** llama3.2 (3B, local) wrote that both classes "inhibit bacterial cell wall synthesis" — false for
aminoglycosides, and not supported by the retrieved passages, which describe protein-synthesis inhibition.
**Cause:** generation, not retrieval — a 3B model over-generalised under a "compare" prompt.
**Fix:** use the larger OCI-hosted model for answers; add a faithfulness check (every sentence must cite a passage;
uncited comparative claims are flagged). The local model remains only as an offline fallback.
**Category:** generation / faithfulness.

## 3. Graph ranked the wrong condition for a classic vignette (data gap)
**Question:** "Fever, cough and night sweats for 3 weeks with weight loss."
**Observed:** BODHI ranked *Lung abscess* first; *Pulmonary tuberculosis* tied with pneumonia lower down.
**Cause:** BODHI's *Pulmonary tuberculosis* node lists fever and cough but not night sweats or weight loss, so TB
can only match 2 of 4 symptoms. The code ranked correctly given the data.
**Fix (proposed):** add textbook evidence to ranking — retrieve "fever cough night sweats weight loss" and boost
conditions named in the top passages; report graph and textbook disagreement instead of hiding it.
**Category:** knowledge-source coverage.

## 4. Treatment hop borrowed an unrelated passage
**Question:** "Fever, joint pain and rash — likely diagnosis and treatment?"
**Observed (before fix):** for *Chikungunya fever* the treatment hop retrieved an unrelated problem-solution passage
(similarity 0.68, above the 0.60 threshold) and the answer could have cited it.
**Cause:** similarity alone cannot tell "about this condition" from "about something nearby".
**Fix (built):** a treatment passage is accepted only if it names the condition; otherwise the evidence explicitly
says the indexed books do not cover that treatment. (With Davidson's indexed, dengue/chikungunya management is
now found in the medicine book.)
**Category:** retrieval precision / grounding.

## 5. Clinical phrasing not linked to the graph
**Questions:** "burning micturition", "noisy breathing", "weight loss".
**Observed:** no BODHI symptom linked, so the graph route cannot use them.
**Cause:** BODHI uses different wording; the semantic fallback threshold (0.86) is strict to avoid false matches
(an earlier looser rule mapped "bite" → "Seizure bite").
**Fix (proposed):** a small synonym table of common clinical terms → BODHI names, and calibrating the threshold
on the hand-written eval questions.
**Category:** entity linking.

## 6. Structure recovery errors (chunking)
**Observed:** in Tripathi, "Second line anti-TB drugs" was filed under *Streptomycin* because the book styles it like
a sub-heading; chapter intros were initially dropped (~4% of Guyton's text) and one Robbins chapter with no
sub-bookmarks was missing.
**Fix (built):** Overview sections for chapter intros and whole-chapter sections when no sub-bookmarks exist —
coverage went from ~96% to 99–101%. Heading-level mistakes remain; a domain expert reviewing `index.md` is the
cheapest fix.
**Category:** chunking / metadata.

## 7. Operational: one backend error killed a long job
**Observed:** STAIR question generation stopped at section 43/447 after a single Ollama HTTP 500 (two jobs were
using the local model at once); the shell reported success because of a trailing command.
**Fix (built):** retries with backoff, per-section flushing and resume-from-file; the job now reports the
generator's own exit code.
**Category:** engineering.
