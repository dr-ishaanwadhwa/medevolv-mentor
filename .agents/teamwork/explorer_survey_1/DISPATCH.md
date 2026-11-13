# DISPATCH — Explorer Survey 1 (Headings Densification & Leak Prevention)

## Role & Identity
- Archetype: teamwork_explorer
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1/
- Original parent conversation ID: 57110369-e183-4fdc-9b47-086b61a6c6e5

## Mandatory Reading
- Original request: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md`
- Plan document: `docs/headings_to_ontology_plan.md`
- Scratchpad scripts: `/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/` (`hlib.py`, `hclass.py`, `h2.py`, `h4.py`–`h7.py` and any related files)

## Mission
Investigate and map the full requirements, existing code, and dependencies for R1 (Headings Densification Stage A) and non-T1 leak prevention:
1. Examine `docs/headings_to_ontology_plan.md` in detail: Rules 1, 3, 4, 5a, 6, and 8.
2. Examine the scratchpad directory `/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/` and analyze `hlib.py`, `hclass.py`, `h2.py`, `h4.py`–`h7.py`. What does each script do, how do they connect, and what needs to be promoted into `rag/headings.py`?
3. Check `rag/headings.py` (does it already exist or is it a new module?) and inspect current heading representations and data formats.
4. Check where `data/graph/headings.jsonl` should be written, schema requirements, and relationship to existing graph files.
5. Check `eval/heading_metrics.py` (does it exist, what metrics must it measure?).
6. Check how answers generate `graph_block` in the current RAG pipeline (e.g. search for `graph_block` across `rag/`), and determine how non-T1 heading records can leak and how leak tests should be structured.

## Output Requirements
Produce a comprehensive handoff report in `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1/handoff.md` detailing:
- Exact findings with code citations and file paths
- Proposed architecture for `rag/headings.py`
- Step-by-step implementation strategy for Rules 1, 3, 4, 5a, 6, 8
- Leak test design for `graph_block` non-T1 prevention
- Identified risks, edge cases, and dependencies
Send a message when complete.


## 2026-11-13T08:48:32Z
Read your task dispatch instructions in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1/DISPATCH.md.
Also read the original request in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.
Investigate R1: Headings Densification (Stage A), docs/headings_to_ontology_plan.md, scratchpad scripts in /private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/ (hlib.py, hclass.py, h2.py, h4.py-h7.py), rag/headings.py, eval/heading_metrics.py, and graph_block non-T1 leak prevention.
Write your complete findings and handoff report to /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1/handoff.md and update progress.md in your directory.
Send a message to your parent when done.
