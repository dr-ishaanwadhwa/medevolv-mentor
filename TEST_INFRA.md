# E2E Test Infra: MedEvolv Mentor & Atlas Unified Platform

## Test Philosophy
- Opaque-box, requirement-driven: Derived strictly from `ORIGINAL_REQUEST.md` and user-facing specifications, with zero coupling to implementation internals.
- Verification Methodology: Category-Partition Equivalence Class Testing + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Workload Testing.
- Progressive testability: Lower-tier tests use simple verification channels (HTTP status, schema validation, exit codes) before higher-tier end-to-end user workflows.

## Feature Inventory & Test Matrix
20 core functional features across R1–R4.

| # | Feature ID | Feature Name | Source | Tier 1 (Coverage) | Tier 2 (Boundary) | Tier 3 (Pairwise) |
|---|---|---|---|:---:|:---:|:---:|
| 1 | R1.1 | FastAPI Gateway | `ATLAS_INTEGRATION_SPEC.md` §1 | ≥5 | ≥5 | ✓ |
| 2 | R1.2 | `/api/chat/stream` SSE Stream | `ATLAS_INTEGRATION_SPEC.md` §3 | ≥5 | ≥5 | ✓ |
| 3 | R1.3 | `/api/spatial/resolve` Endpoint | `ATLAS_INTEGRATION_SPEC.md` §3 | ≥5 | ≥5 | ✓ |
| 4 | R1.4 | SpatialAction Tool Agent | `critique.md` §3.3.2 | ≥5 | ≥5 | ✓ |
| 5 | R1.5 | Client/Server PII Sanitization | `v2 research.md` §5.3 | ≥5 | ≥5 | ✓ |
| 6 | R2.1 | Next.js 15 Unified PWA | `ATLAS_INTEGRATION_SPEC.md` §1 | ≥5 | ≥5 | ✓ |
| 7 | R2.2 | Native Three.js WebGL Canvas | `ATLAS_INTEGRATION_SPEC.md` §2 | ≥5 | ≥5 | ✓ |
| 8 | R2.3 | Zustand Global State Store | `critique.md` §3.3.3 | ≥5 | ≥5 | ✓ |
| 9 | R2.4 | Raycast Mesh Click Callback | `ATLAS_INTEGRATION_SPEC.md` §2 | ≥5 | ≥5 | ✓ |
| 10 | R2.5 | Responsive Split/Sheet Layout | User Story 11 | ≥5 | ≥5 | ✓ |
| 11 | R2.6 | IndexedDB Offline PWA Cache | User Story 6 | ≥5 | ≥5 | ✓ |
| 12 | R3.1 | Unified Spatial-Clinical Schema | `critique.md` §3.4 | ≥5 | ≥5 | ✓ |
| 13 | R3.2 | Recursive Mereology Traversal | `ATLAS_INTEGRATION_SPEC.md` §4 | ≥5 | ≥5 | ✓ |
| 14 | R3.3 | >80% Grounding Coverage | `ATLAS_INTEGRATION_SPEC.md` §4 | ≥5 | ≥5 | ✓ |
| 15 | R3.4 | Tripartite Concept Crosswalk | `critique.md` §2.3.3 | ≥5 | ≥5 | ✓ |
| 16 | R4.1 | FSRS-5 Spaced Repetition Engine | `v2 research.md` §3, 4.1 | ≥5 | ≥5 | ✓ |
| 17 | R4.2 | 3D Mesh Occlusion Testing | User Story 7 | ≥5 | ≥5 | ✓ |
| 18 | R4.3 | Pointer-Only Citation Guardrail | `v2 research.md` §5.1 | ≥5 | ≥5 | ✓ |
| 19 | R4.4 | Indian Protocol Grounding | User Story 9 | ≥5 | ≥5 | ✓ |
| 20 | R4.5 | DPDP 2025 Minor Protection | `v2 research.md` §5.3 | ≥5 | ≥5 | ✓ |

## Test Architecture
- **Location**: `tests/e2e/`
- **Runner**: Pytest test harness (`.venv/bin/pytest tests/e2e/ -v`) + Playwright/Node test scripts (`pnpm test:e2e`).
- **Pass/Fail Semantics**: 100% test pass required (exit code 0). Zero flakiness or skipped tests.
- **Directory Layout**:
  - `tests/e2e/conftest.py`: Test fixtures, test client, mock data, and test environments.
  - `tests/e2e/test_tier1_features.py`: Feature coverage (≥5 tests per feature = ≥100 tests).
  - `tests/e2e/test_tier2_boundaries.py`: Boundary and corner cases (≥5 tests per feature = ≥100 tests).
  - `tests/e2e/test_tier3_pairwise.py`: Pairwise cross-feature interactions (≥20 tests).
  - `tests/e2e/test_tier4_scenarios.py`: Realistic end-user workflows (≥10 clinical application tests).

## Real-World Application Scenarios (Tier 4)
| # | Scenario | Features Exercised | Clinical Workflow | Complexity |
|---|---|---|---|---|
| 1 | Acute Coronary Syndrome Case | R1.2, R1.3, R1.4, R3.2, R4.3, R4.4 | Student asks about LAD occlusion in STEMI -> chat streams explanation + highlights LAD branch (`FMA3740`), sets camera to thoracic left oblique, resolves mereology up to Left Coronary Artery and Heart, cites Harrison/Robbins pointers and ICMR cardiology guidelines. | High |
| 2 | Raycast-to-Socratic Recall Loop | R2.4, R1.3, R4.1, R4.2 | Student taps left kidney in 3D viewport -> raycaster emits click event -> resolves citations & conditions -> triggers FSRS-5 3D occlusion flashcard with numbered screen pins -> student grades recall as 'Good' -> updates interval. | High |
| 3 | Tuberculosis Diagnostic Workup | R1.2, R4.3, R4.4, R3.2, R1.4 | Query on pulmonary TB -> isolates respiratory system, sets clipping plane, resolves NTEP fixed-dose therapy with guideline badge, disambiguates from Western textbook duration. | High |
| 4 | Offline Transit Study Mode | R2.6, R4.1, R4.2 | PWA launched offline -> loads 15 binary chunks from IndexedDB -> renders 3D viewport at 60 FPS (15 draw calls) -> completes FSRS review deck without network access. | High |
| 5 | DPDP 2025 Compliance & Minor Gate | R4.5, R1.5, R1.2 | Under-18 learner attempt -> triggers mandatory parental consent gate -> disables behavioral profiling; user submits query with patient hospital MRN -> PII sanitizer strips patient name before LLM processing. | Medium |
| 6 | Copyright Fair-Dealing Boundary | R1.2, R1.3, R4.3 | Query directly asking for verbatim textbook quote -> response generates synthesized clinical prose, attaches certified pointer `(Gray's, 5e, Ch 4, p. 542)`, completely omitting copyrighted text. | Medium |
| 7 | Granular Mereological Fallback | R3.2, R3.3, R1.3, R2.3 | Query regarding microscopic entity (*Podocyte* or *Macula Densa*) -> climbs mereology tree to *Renal Glomerulus* -> *Kidney*, highlights Kidney mesh in viewport with microscopic disclaimer. | Medium |
| 8 | Multi-System Dissection Sequence | R1.4, R2.2, R2.3 | Mentor initiates anatomical dissection: peels skeletal and muscular systems to reveal thoracic viscera, verifies 15 draw call budget is maintained across DataTexture visibility updates. | High |
| 9 | Socratic Teaching Session | R1.2, R1.3, R4.1 | Mentor guides learner through differential diagnosis for acute shortness of breath; interleaves camera presets and Socratic follow-up questions without text lag. | High |
| 10 | Emergency Clinical Safety Refusal | R1.2, R1.5 | User enters "I am having severe chest pain right now" -> safety regex triggers immediate refusal and emergency medical directive before retrieval or LLM inference. | Low |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥5 test cases per feature (20 features × 5 = 100 test cases).
- **Tier 2 (Boundary & Corner Cases)**: ≥5 test cases per feature (20 features × 5 = 100 test cases).
- **Tier 3 (Cross-Feature Combinations)**: ≥20 pairwise test cases.
- **Tier 4 (Real-World Scenarios)**: ≥10 realistic application scenarios.
- **Minimum Test Suite Size**: **≥230 test cases**.
- **Exit Criteria**: 100% pass rate under `.venv/bin/pytest tests/e2e/`. Publishes `TEST_READY.md`.
