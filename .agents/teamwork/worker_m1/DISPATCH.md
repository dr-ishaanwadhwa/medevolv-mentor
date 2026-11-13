# DISPATCH — Worker M1 (Headings Densification Stage A & Leak Prevention)

## Role & Identity
- Archetype: teamwork_worker
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1/
- Original parent conversation ID: 57110369-e183-4fdc-9b47-086b61a6c6e5

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Mandatory Reading
- Original request: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md`
- Project scope & interface contracts: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/PROJECT.md`
- Explorer handoff report: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1/handoff.md`
- Master plan: `docs/headings_to_ontology_plan.md`
- Scratchpad source scripts: `/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/` (`hlib.py`, `hclass.py`, `h2.py`, `h4.py`–`h7.py`)

## File Write Ownership
You exclusively own and may modify:
- `rag/headings.py`
- `data/graph/headings.jsonl`
- `eval/heading_metrics.py`
- `reports/heading_metrics.json`
- `tests/test_headings_leak.py`
Do NOT modify any files outside this ownership without approval. Under NO circumstances modify `data/ontology/clinical_ontology.jsonl`.

## Task Objectives
1. **Implement `rag/headings.py`**:
   - Promote heading extraction, cleaning, and classification logic from scratchpad scripts (`hlib.py`, `hclass.py`, `h2.py`, `h4.py`–`h7.py`).
   - Implement the Section 3.0 decision list from `docs/headings_to_ontology_plan.md`.
   - **CRITICAL HARD GATE**: Ensure `FACET_EXACT` check (91 strings) runs BEFORE entity matching (`match()`) so structural headings like "Joints", "Nerves", "Arteries", "Toxicity" are NEVER classified as entities.
   - Implement Rules 1, 3, 4, 5a, 6, and 8:
     - Rule 1: Primary topic linking (strict + relaxed, disambiguation by book context + degree tie-break).
     - Rule 3: Facets (tier `navigation`).
     - Rule 4: Hierarchy `subtopic_of` and Gray's `part_of` candidates.
     - Rule 5a: Parenthetical aliases (abbreviations, synonyms, alias matching, merge proposals).
     - Rule 6: Identical cross-book headings.
     - Rule 8: Gray's case section links (`illustrated_by`).
   - Implement builder: `build_headings(output_path)` writing to `data/graph/headings.jsonl`.
   - Implement cached loaders and query functions (`primary_topic`, `section_heading`, `headings_for_concept`, `facets_for`, `subtopics`, `part_of_candidates`, `parenthetical_aliases`, `cross_book_headings`, `all_headings`).
   - Support CLI execution: `.venv/bin/python -m rag.headings`.

2. **Generate `data/graph/headings.jsonl`**:
   - Run the builder and verify all 3,135 ToC nodes (2,675 section leaves) across the 7 books are processed.
   - Verify every line is valid JSON conforming to `{heading_id, book, section_id, level, class, facet, concept_ids, concept_label, parent_id, tier, method, evidence}`.
   - Verify `tier in ("T2", "T3", "navigation")` on 100% of records; `tier == "T1"` MUST NEVER OCCUR.

3. **Implement `eval/heading_metrics.py`**:
   - Promote scratchpad evaluation logic (`h1.py`–`h7.py`).
   - Report book distributions, primary topic yields (% same section, % same book), facet protection gate (0 generic facets promoted), hierarchy edges, aliases, case links, and leak checks.
   - Write structured JSON report to `reports/heading_metrics.json`.
   - Run `.venv/bin/python eval/heading_metrics.py` and capture stdout and JSON artifact.

4. **Implement `tests/test_headings_leak.py`**:
   - 5-barrier automated leak test suite:
     1. Tier Invariant: every record in `data/graph/headings.jsonl` has `tier in ("T2", "T3", "navigation")`, never `"T1"`.
     2. Ontology Contamination: `data/ontology/clinical_ontology.jsonl` contains 0 heading records.
     3. AST Static Isolation: `rag/hops.py` and `rag/answer.py` do not import `rag.headings`.
     4. Poisoning Test: monkeypatched `rag.headings` methods do not trigger during `hops.make_plan`.
     5. Prompt Inspection: `graph_block` in answer generation contains 0 non-T1 heading records.
   - Also add functional tests for `rag/headings.py` query APIs.

5. **Run Verification Commands**:
   - `.venv/bin/python -m rag.headings`
   - `.venv/bin/python eval/heading_metrics.py`
   - `.venv/bin/pytest tests/test_headings_leak.py`
   - `.venv/bin/pytest tests/` (assert all 143 existing tests + new tests pass)

## Output Requirements
Write a complete handoff report in `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1/handoff.md` detailing:
- Exact changes made and file paths
- Build and test commands executed with verbatim outputs and return codes
- Key metrics from `reports/heading_metrics.json`
- Verification evidence that non-T1 heading records cannot leak into `graph_block`
Send a message when complete.


## 2026-11-13T08:59:04Z
Read your task dispatch instructions in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1/DISPATCH.md.
Also read the original request in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.
MANDATORY INTEGRITY WARNING: DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.
Implement Milestone 1: Headings Densification (Stage A) in rag/headings.py, generate data/graph/headings.jsonl, implement eval/heading_metrics.py (and reports/heading_metrics.json), and implement tests/test_headings_leak.py.
Run all verification commands (.venv/bin/python -m rag.headings, .venv/bin/python eval/heading_metrics.py, .venv/bin/pytest tests/test_headings_leak.py, .venv/bin/pytest tests/) and verify that all 143 existing tests plus new tests pass cleanly with zero regressions.
Write your complete handoff report to /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1/handoff.md and send a message when done.
