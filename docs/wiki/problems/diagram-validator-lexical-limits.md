# Flowchart validator: word rules cannot guarantee meaning

**History.** On 2026-11-16/17 four red-team rounds were run against the R1 flowchart validator
(`api/diagram_validate.py`). Each round's fixes were word-level rules (direction stems, antonym pairs, negation windows,
number binding, borrowed-word checks). Round 3 found 9 accepted meaning flips; they were closed in `main@e88176b`
(RULES_VERSION 6, 558 tests). The same engineer then listed 4 flips that **still pass** at e88176b:
1. an un-listed verb swap ("accelerate initiation" where the text says "freeze initiation");
2. verb/object swaps inside one sentence ("restores sympathetic overactivity");
3. an inserted "only";
4. a meaning word with no listed opposite ("absent" where the text says "occurs").
Sources: workflow `wf_52cca90d-cff` results and the e88176b engineer report (session 2026-11-17).

**Pattern.** Each word list closes the cases it names and leaves the next synonym open. Recall stayed flat while rules
grew, so the cost is complexity, not coverage.

**Decision on 2026-11-17.** The `diagram` flag was turned **off** on the live site (VM `~/v2-state/features.json`)
because an earlier live validator accepted an unsupported arrow and round 3 found medical meaning flips. Release bar
recorded: "zero known meaning flips pass", not "every known flip has a failing test".

**Proposed direction (awaiting the user).** Keep the word rules as a cheap first filter, and add a per-box/per-arrow
entailment check (DeepSeek, temperature 0, JSON yes/no + quoted span) against the exact cited sentence; decline the
box when the model cannot quote a supporting span. Then re-run the red team suites (redteam1-4) and the live eval.
Related: [PRD R1](../../prd/2026-11-15-next-release-prd.md), [flags stale after deploy](flags-stale-after-deploy.md).

**Update 2026-11-17 (supersedes "Proposed direction").** The user approved the entailment check; built in
`main@f822135` (`api/diagram_entail.py`, RULES_VERSION 7). One DeepSeek call per diagram judges each box/arrow against its
cited sentences and must return a quote that a code check finds verbatim in a sentence the item cites; it only removes
items; failures decline `verifier_unavailable` (uncached). Measured by the engineer: the 4 known flips caught live; red
teams 1-4 bad cases 73/73 declined by the verifier alone; false drops on 35 good diagrams 0/287 boxes, 8/231 arrows; about
+1.9 s per request. Deployed and the `diagram` flag turned back **on** the same day. Live end-to-end check after deploy:
6/7 question types drew a diagram (comparison, metformin, facial nerve, beta blockers, T1D, superior orbital fissure),
digoxin declined, a patient-specific question was refused before any flowchart was offered. Known soft spot: arrows from a
lead-in to "division" items and backward connectives ("is attributed to") are sometimes dropped (lost diagrams, not
wrong ones).
