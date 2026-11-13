# Scope: E2E Testing Track

## Architecture
Opaque-box test suite executing against FastAPI TestClient, internal mereology/FSRS engines, and frontend contracts.

## Feature Inventory (Testing Scope)
Validates all 20 features:
- Tier 1: 20 features × ≥5 tests = ≥100 tests
- Tier 2: 20 features × ≥5 boundary tests = ≥100 tests
- Tier 3: ≥20 cross-feature tests
- Tier 4: ≥10 real-world clinical application scenarios
Total test target: ≥230 tests.

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| E2E.1 | Test Infra & Fixtures | `tests/e2e/conftest.py` setup | none | PLANNED |
| E2E.2 | Tier 1 Feature Tests | `tests/e2e/test_tier1_features.py` | E2E.1 | PLANNED |
| E2E.3 | Tier 2 Boundary Tests | `tests/e2e/test_tier2_boundaries.py` | E2E.1 | PLANNED |
| E2E.4 | Tier 3 Pairwise Tests | `tests/e2e/test_tier3_pairwise.py` | E2E.2, E2E.3 | PLANNED |
| E2E.5 | Tier 4 Scenarios & TEST_READY | `tests/e2e/test_tier4_scenarios.py` & `TEST_READY.md` | E2E.2, E2E.3, E2E.4 | PLANNED |

## Interface Contracts
- Tests must import from `api.main`, `rag.mereology`, `rag.fsrs`, `rag.guardrails`.
- Mock external LLM endpoints and ChromaDB if needed so tests run rapidly and deterministically without network dependencies.
- Output: `TEST_READY.md` at project root with exact test counts and execution command.
