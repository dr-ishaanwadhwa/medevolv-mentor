# Task Assignment: Milestone 1 Worker (Knowledge Graph & Mereology)

## Mission
Implement the unified spatial-clinical knowledge graph and mereological traversal engine (R3.1, R3.2, R3.3, R3.4).

## Identity & Working Directory
- TypeName: teamwork_worker
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1_1/
- Exclusive File Ownership:
  - `rag/mereology.py`
  - `scripts/build_mereology_db.py`
  - `tests/test_mereology.py`
  - `data/graph/mereology_graph.sqlite3`

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_backend_survey_1/handoff.md

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Requirements
1. **Schema & Database (`scripts/build_mereology_db.py`)**:
   - Create SQLite database `data/graph/mereology_graph.sqlite3` (with matching PostgreSQL DDL script/support).
   - Ingest FMA concepts from `third_party/human-atlas/public/models/atlas.json` and `data/graph/atlas_crosswalk.jsonl` into `spatial_concepts` (fma_id, canonical_name, latin_name, system_id, mesh_part_ids, bounding_box, centroid).
   - Ingest/generate hierarchical mereological relations into `spatial_relations` (subject_fma_id, predicate, object_fma_id, source_citation) covering `PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`, `DRAINED_BY`. Build mereology hierarchy for anatomical systems (e.g. coronary artery branches -> coronary arteries -> aorta/heart; heart chambers/valves -> heart; lobes/bronchi -> lungs; glomeruli/nephrons -> kidneys; lobes/segments -> brain/liver; etc.).
   - Ingest 4,978 certified conditions from `data/ontology/clinical_ontology.jsonl` into `clinical_concepts` and `spatial_clinical_crosswalk`.
   - Connect clinical conditions to anatomical structures via direct facts and mereological expansion.
2. **Recursive Mereological Engine (`rag/mereology.py`)**:
   - Implement `resolve_structure(fma_or_name: str) -> Optional[ResolvedStructure]`
   - Implement `climb_to_visible_mesh(fma_id: str, max_depth: int = 5) -> Tuple[str, int]` using recursive CTE upward traversal in SQLite.
   - Implement `resolve_condition(condition_label_or_id: str) -> List[ResolvedStructure]`
   - Implement `get_mereology_tree(fma_id: str) -> Dict[str, Any]` (parents and children)
   - Implement `compute_grounding_metrics() -> Dict[str, float]`
   - **Target**: Condition anatomical grounding coverage must rise from 2.31% to **>80%** (and certified structures to >95%).
3. **Tests (`tests/test_mereology.py`)**:
   - Write comprehensive unit and integration tests verifying schema, recursive CTE, cycles handling, bilateral structures, microscopic entities fallback, and grounding coverage >80%.
   - Run `.venv/bin/pytest tests/test_mereology.py` and `.venv/bin/pytest tests/`.
   - Ensure all 143 existing tests pass with 0 regressions.

## Expected Output
Handoff report at `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1_1/handoff.md` with test output and verification commands.

## 2026-11-13T09:11:40Z
You are teamwork_worker for Milestone 1 (Knowledge Graph & Mereology) of the MedEvolv Mentor & Atlas platform.
Your identity: teamwork_worker
Your working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1_1/

MANDATORY FIRST STEP: Read /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.
Also read /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md and /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1_1/DISPATCH.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Exclusive file ownership:
- rag/mereology.py
- scripts/build_mereology_db.py
- tests/test_mereology.py
- data/graph/mereology_graph.sqlite3

Task:
1. Create SQLite database data/graph/mereology_graph.sqlite3 (and scripts/build_mereology_db.py) ingesting spatial_concepts, spatial_relations (PART_OF, BRANCH_OF, SUPPLIED_BY, DRAINED_BY), clinical_concepts (from clinical_ontology.jsonl), and spatial_clinical_crosswalk.
2. Implement rag/mereology.py with recursive CTE upward traversal resolving granular entities to visible BodyParts3D parent meshes.
3. Verify condition grounding coverage increases from 2.31% to >80% (and certified structures to >95%).
4. Write tests in tests/test_mereology.py and execute them:
   .venv/bin/pytest tests/test_mereology.py
   .venv/bin/pytest tests/
   Ensure all 143 existing tests pass with 0 regressions.
5. Write your handoff report to:
   /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m1_1/handoff.md
6. Send a message to the orchestrator (ID: 374680d6-856a-4138-9979-f33b00b59dea) when complete.
