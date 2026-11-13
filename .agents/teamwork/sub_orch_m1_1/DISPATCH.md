# Task Assignment: Milestone 1 Sub-Orchestrator (Knowledge Graph & Mereology)

## Mission
You are the Sub-Orchestrator for Milestone 1: Knowledge Graph & Mereological Traversal.
Your mission is to execute the iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor) to deliver R3.1, R3.2, R3.3, and R3.4:
- Unified relational schema (SQLite / PostgreSQL) connecting FMA concepts, spatial relations, BODHI conditions, and textbook citations.
- Recursive mereological traversal engine (`rag/mereology.py`) supporting `PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`.
- Elevating condition anatomical grounding coverage from 2.31% to >80% (and certified structures to >95%).
- Tripartite entity crosswalk (`SNOMED_CT <-> FMA_ID <-> Textbook_Passage_Pointer`).
- Complete unit and integration tests in `tests/test_mereology.py` passing cleanly with 0 regressions in existing 143 tests.

## Identity & Working Directory
- TypeName: sub-orchestrator
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_m1_1/
- Parent Conversation ID: 374680d6-856a-4138-9979-f33b00b59dea

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_m1_1/SCOPE.md
- Survey findings in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md and /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_backend_survey_1/handoff.md

## Execution Protocol
Follow the orchestrator procedure:
1. Assess scope.
2. Run Iteration Loop (2B):
   - Spawn Explorers (or use survey findings) to specify technical design.
   - Spawn Worker with mandatory integrity warning to implement:
     - `rag/mereology.py`
     - Database migration / creation script `scripts/build_mereology_db.py` producing `data/graph/mereology_graph.sqlite3`
     - Integration tests `tests/test_mereology.py`
     - Run `.venv/bin/pytest tests/test_mereology.py` and `.venv/bin/pytest tests/`
   - Spawn Reviewers to check correctness, >80% coverage verification, and layout conformance.
   - Spawn Challengers to stress-test recursive edge cases (cycles, missing parents, bilateral organs).
   - Spawn Forensic Auditor (`teamwork_auditor`) for integrity check.
   - Record verdicts in `GATE_STATUS.md`.
3. When gate passes:
   - Mark milestone DONE in `progress.md` and handoff report.
   - Send completion message to parent (ID: 374680d6-856a-4138-9979-f33b00b59dea).
