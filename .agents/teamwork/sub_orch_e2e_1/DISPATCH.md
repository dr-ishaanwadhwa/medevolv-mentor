# Task Assignment: E2E Testing Orchestrator

## Mission
You are the E2E Testing Orchestrator for the MedEvolv Mentor & Atlas unified platform.
Your mission is to manage the E2E Testing Track per `TEST_INFRA.md` and `PROJECT.md`.
Deliver the complete opaque-box 4-tier test suite in `tests/e2e/`, execute it, verify 100% test pass, and publish `TEST_READY.md` at the project root.

## Identity & Working Directory
- TypeName: sub-orchestrator
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_e2e_1/
- Parent Conversation ID: 374680d6-856a-4138-9979-f33b00b59dea

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/TEST_INFRA.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_e2e_1/SCOPE.md

## Scope & Deliverables
1. Build test infrastructure in `tests/e2e/conftest.py` (FastAPI TestClient, mock environment, fixtures).
2. Create Tier 1 Feature Coverage tests in `tests/e2e/test_tier1_features.py` (≥5 tests for each of the 20 features = ≥100 tests).
3. Create Tier 2 Boundary & Corner cases in `tests/e2e/test_tier2_boundaries.py` (≥5 tests for each feature = ≥100 tests).
4. Create Tier 3 Cross-Feature Combinations in `tests/e2e/test_tier3_pairwise.py` (≥20 tests).
5. Create Tier 4 Real-World Application Scenarios in `tests/e2e/test_tier4_scenarios.py` (≥10 realistic workflows).
6. Verify all test files compile and pass using workers/reviewers.
7. Publish `/Users/ishaanwadhwa/Projects/med-rag/TEST_READY.md`.

## Execution Protocol
Follow the orchestrator procedure:
- You are a sub-orchestrator.
- Assess your scope and run the iteration loop (or decompose into tier sub-tasks):
  - Dispatch teamwork_test_writer or teamwork_worker to write test files and run pytest.
  - Dispatch teamwork_reviewer to verify coverage and independence.
  - Dispatch teamwork_auditor for integrity check.
- When all tests pass cleanly, write `TEST_READY.md` and handoff report in your working directory.
- Send completion message to parent (ID: 374680d6-856a-4138-9979-f33b00b59dea).
