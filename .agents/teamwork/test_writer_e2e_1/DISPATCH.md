# Task Assignment: E2E Test Suite Writer

## Mission
Design and implement the complete opaque-box 4-tier E2E test suite in `tests/e2e/` per `TEST_INFRA.md` and `PROJECT.md`.

## Identity & Working Directory
- TypeName: teamwork_test_writer
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/test_writer_e2e_1/
- Exclusive File Ownership:
  - `tests/e2e/conftest.py`
  - `tests/e2e/test_tier1_features.py`
  - `tests/e2e/test_tier2_boundaries.py`
  - `tests/e2e/test_tier3_pairwise.py`
  - `tests/e2e/test_tier4_scenarios.py`
  - `TEST_READY.md` (when suite passes)

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/TEST_INFRA.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md

## Detailed Requirements
1. **Infrastructure (`tests/e2e/conftest.py`)**:
   - Provide Starlette/FastAPI TestClient fixtures (`client`).
   - Mock LLM generation backends to return deterministic SSE chunks and spatial actions when testing `/api/chat/stream`.
   - Setup in-memory / test SQLite mereology fixtures.
2. **Tier 1 - Feature Coverage (`tests/e2e/test_tier1_features.py`)**:
   - Cover all 20 inventoried features from `PROJECT.md § Feature Inventory` (R1.1–R1.5, R2.1–R2.6, R3.1–R3.4, R4.1–R4.5).
   - ≥5 self-contained tests per feature = **≥100 tests**.
3. **Tier 2 - Boundary & Corner Cases (`tests/e2e/test_tier2_boundaries.py`)**:
   - Test boundaries: empty messages, max depth limits, unknown FMA IDs, microscopic organs, bilateral structures, missing citation pointers, rapid requests, extreme FSRS retention parameters (e.g. 0.99 vs 0.70), PII redaction edge cases.
   - ≥5 tests per feature = **≥100 tests**.
4. **Tier 3 - Cross-Feature Combinations (`tests/e2e/test_tier3_pairwise.py`)**:
   - Test feature interactions (e.g. Chat SSE emitting SpatialAction -> SpatialResolve on selected FMA -> FSRS occlusion card generation; DPDP 18+ gate + PII redaction on ChatStream; Mereological climb + Pointer citation generation; etc.).
   - **≥20 tests**.
5. **Tier 4 - Real-World Application Scenarios (`tests/e2e/test_tier4_scenarios.py`)**:
   - Implement the 10 real-world clinical application scenarios defined in `TEST_INFRA.md` (Acute Coronary Syndrome, Socratic Teaching, TB Regimen, Offline Deck Review, etc.).
   - **≥10 tests**.
6. **Total Target**: ≥230 tests.
7. **Execution**: Run `.venv/bin/pytest tests/e2e/ -v`.
   - When implementation targets are ready or mocked as needed for opaque-box testing, verify clean pass.
   - Publish `/Users/ishaanwadhwa/Projects/med-rag/TEST_READY.md`.

## Expected Output
Handoff report at `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/test_writer_e2e_1/handoff.md`.


## 2026-11-13T09:11:48Z
You are teamwork_test_writer for the E2E Testing Track of the MedEvolv Mentor & Atlas platform.
Your identity: teamwork_test_writer
Your working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/test_writer_e2e_1/

MANDATORY FIRST STEP: Read /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.
Also read /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md, /Users/ishaanwadhwa/Projects/med-rag/TEST_INFRA.md, and /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/test_writer_e2e_1/DISPATCH.md.

Exclusive file ownership:
- tests/e2e/conftest.py
- tests/e2e/test_tier1_features.py
- tests/e2e/test_tier2_boundaries.py
- tests/e2e/test_tier3_pairwise.py
- tests/e2e/test_tier4_scenarios.py
- TEST_READY.md (when suite passes)

Task:
1. Implement test infrastructure in tests/e2e/conftest.py (FastAPI TestClient fixture, mock LLM streaming generator, mock DB fixtures).
2. Implement Tier 1 Feature Coverage tests in tests/e2e/test_tier1_features.py (≥5 tests for each of the 20 features in PROJECT.md § Feature Inventory = ≥100 tests).
3. Implement Tier 2 Boundary & Corner tests in tests/e2e/test_tier2_boundaries.py (≥5 boundary tests per feature = ≥100 tests).
4. Implement Tier 3 Pairwise Cross-Feature tests in tests/e2e/test_tier3_pairwise.py (≥20 tests).
5. Implement Tier 4 Real-World Application tests in tests/e2e/test_tier4_scenarios.py (≥10 realistic clinical workflows).
Total test suite size: ≥230 tests.
6. Execute the test suite using .venv/bin/pytest tests/e2e/ -v.
7. Publish /Users/ishaanwadhwa/Projects/med-rag/TEST_READY.md following the template in TEST_INFRA.md.
8. Write your handoff report to:
   /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/test_writer_e2e_1/handoff.md
9. Send a message to the orchestrator (ID: 374680d6-856a-4138-9979-f33b00b59dea) when complete.
