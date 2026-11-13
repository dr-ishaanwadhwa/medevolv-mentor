# DISPATCH — Explorer Survey 2 (Graph Networking Pipeline Update & Metrics)

## Role & Identity
- Archetype: teamwork_explorer
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_2/
- Original parent conversation ID: 57110369-e183-4fdc-9b47-086b61a6c6e5

## Mandatory Reading
- Original request: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md`
- Plan document: `docs/graph_networking_plan.md`
- Graph scripts:
  - `scripts/build_mentions.py`
  - `scripts/build_hubs.py`
  - `scripts/build_crosswalk.py`
  - `scripts/build_comention.py`
  - `scripts/build_atlas_crosswalk.py`
  - `scripts/graph_metrics.py`

## Mission
Investigate and map the full requirements, current state, and update needs for R2 (Graph Networking Pipeline Update):
1. Examine `docs/graph_networking_plan.md` in detail to understand what changes/updates are required in the networking pipeline.
2. Inspect `scripts/build_mentions.py`, `scripts/build_hubs.py`, `scripts/build_crosswalk.py`, `scripts/build_comention.py`, `scripts/build_atlas_crosswalk.py`, and `scripts/graph_metrics.py`.
3. Check existing files in `data/graph/` (`mentions.jsonl`, `hubs.jsonl`, `crosswalk.jsonl`, `comention.jsonl`, `atlas_crosswalk.jsonl`). How large are they, what are their schemas, and how are they consumed?
4. How does `headings.jsonl` from R1 integrate with or feed into the graph networking pipeline? What is the order of execution between headings densification and the graph networking scripts?
5. How does `scripts/graph_metrics.py` work? Can it be run right now to establish a baseline before any updates?

## Output Requirements
Produce a comprehensive handoff report in `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_2/handoff.md` detailing:
- Exact findings with code citations and file paths
- Pipeline dependency graph and execution order (including integration with headings)
- Necessary updates to pipeline scripts per `docs/graph_networking_plan.md`
- Baseline graph metrics command and expected metrics output
- Identified risks, performance bottlenecks, and edge cases
Send a message when complete.

## 2026-11-13T08:48:32Z
Read your task dispatch instructions in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_2/DISPATCH.md.
Also read the original request in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.
Investigate R2: Graph Networking Pipeline Update, docs/graph_networking_plan.md, scripts/build_mentions.py, scripts/build_hubs.py, scripts/build_crosswalk.py, scripts/build_comention.py, scripts/build_atlas_crosswalk.py, scripts/graph_metrics.py, and existing data/graph/ artifacts.
Write your complete findings and handoff report to /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_2/handoff.md and update progress.md in your directory.
Send a message to your parent when done.
