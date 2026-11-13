# DISPATCH — Challenger M1-2 (Adversarial Leak Stress Testing)

## Role & Identity
- Archetype: teamwork_challenger
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/challenger_m1_2/
- Original parent conversation ID: 57110369-e183-4fdc-9b47-086b61a6c6e5

## Mandatory Reading
- Original request: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md`
- Project scope & interface contracts: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/PROJECT.md`
- Worker handoff report: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1/handoff.md`

## Mission
Adversarially probe and stress-test the leak prevention boundaries around `data/graph/headings.jsonl` and `rag/headings.py`:
1. Craft adversarial tests attempting to smuggle heading records into `graph_block` or `p.graph_facts`:
   - Inspect all places in `rag/` where `graph_facts` is formed.
   - Test whether any combination of concept search or hops can inadvertently resolve a heading navigation record into `graph_facts`.
   - Verify that non-T1 records are strictly ignored by `ontology_facts.graph_facts_for`.
   - Verify that AST checks and poisoning traps cannot be circumvented.
2. Check for data pollution: verify that `data/ontology/clinical_ontology.jsonl` is completely free of heading records.
3. Conclude with a clear verdict: **APPROVE** (leak boundaries are airtight) or **REQUEST_CHANGES** (leak pathway found).

## Output Requirements
Write your complete report to `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/challenger_m1_2/handoff.md` and send a message when done.


## 2026-11-13T09:14:41Z
Read your challenger instructions in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/challenger_m1_2/DISPATCH.md.
Also read ORIGINAL_REQUEST.md, PROJECT.md, and worker_m1/handoff.md.
Adversarially probe and stress-test leak prevention boundaries: attempt to smuggle heading records into graph_block or p.graph_facts, test AST guards, poisoning traps, and ontology file purity.
Write your complete report to /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/challenger_m1_2/handoff.md with a clear verdict (APPROVE or REQUEST_CHANGES). Send a message when complete.
