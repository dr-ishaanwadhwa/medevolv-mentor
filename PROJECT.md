# Project: MedEvolv Mentor & Atlas Unified AI-Native Platform

## Architecture
The platform integrates `med-rag` (MedEvolv Mentor clinical knowledge engine) and `med-rag-atlas` (3D anatomy atlas) into a unified, AI-native production architecture:
1. **Asynchronous Gateway (`api/`)**: High-performance FastAPI backend delivering SSE streaming (`/api/chat/stream`) and spatial mereology resolution (`/api/spatial/resolve`). Replaces the monolithic Streamlit execution model.
2. **Knowledge Graph & Mereology (`rag/mereology.py`, `data/graph/`)**: Relational database (SQLite/PostgreSQL) with recursive upward traversal (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`) mapping clinical conditions to BodyParts3D meshes, lifting grounding from 2.31% toward >80% with correct parents only. Coronary arteries are `BRANCH_OF` the aorta, not `PART_OF` the ascending aorta; coverage is never padded with wrong parent meshes; systemic conditions (SLE, sepsis, diabetes) get no mesh and are reported as such.
3. **Active Recall & Verification Guardrails (`rag/fsrs.py`, `rag/guardrails.py`)**: FSRS-5 spaced-repetition scheduler with 3D mesh occlusion pin calculations, pointer-only citation enforcement `(Book, Ed, Ch, Page)` eliminating copyrighted prose, Indian national protocol badges (ICMR/NTEP), and DPDP 2025 compliance (18+ age gate, zero tracking).
4. **Unified Frontend Workspace (`apps/web`)**: Next.js 15 / React 19 PWA directly embedding the Three.js canvas in the React component tree (no iframes), maintaining 15 draw call GPU DataTexture rendering, Zustand bidirectional state synchronization, and IndexedDB offline geometry caching.
5. **E2E Testing Track**: Autonomous opaque-box verification suite validating all 20 inventoried features across Tiers 1–4, culminating in `TEST_READY.md`.

## Feature Inventory
Every feature identified during Step 0 Survey is mapped to a concrete implementation milestone.

| # | Feature ID | Feature Name | Description | Milestone | Source |
|---|---|---|---|---|---|
| 1 | R1.1 | Asynchronous FastAPI Gateway | High-performance async ASGI gateway replacing Streamlit in `api/main.py`. | M2 | `ATLAS_INTEGRATION_SPEC.md` §1 |
| 2 | R1.2 | SSE Chat Streaming Endpoint | `/api/chat/stream` delivering tokens and structured `SpatialAction` schemas. | M2 | `ATLAS_INTEGRATION_SPEC.md` §3 |
| 3 | R1.3 | Spatial Resolve Endpoint | `/api/spatial/resolve` returning citations, mereology tree, and conditions. | M2 | `ATLAS_INTEGRATION_SPEC.md` §3 |
| 4 | R1.4 | Spatial-Semantic Tool Agent | Emits structured spatial actions (`highlight`, `isolate`, `set_camera`, `dissect`, `reset`). | M2 | `critique.md` §3.3.2 |
| 5 | R1.5 | Client/Server PII Sanitization | Middleware redacting clinical patient identifiers before LLM processing. | M2 | `v2 research.md` §5.3 |
| 6 | R2.1 | Next.js 15 / React 19 Unified PWA | Monorepo client shell in `apps/web`; eliminates sandboxed iframe. | M4 | `ATLAS_INTEGRATION_SPEC.md` §1 |
| 7 | R2.2 | Native Three.js WebGL Canvas | Direct canvas embedding retaining GPU DataTexture across 2,234 meshes in 15 draw calls. | M4 | `ATLAS_INTEGRATION_SPEC.md` §2 |
| 8 | R2.3 | Zustand Global State Store | Reactive store (`useSpatialStore`) synchronizing camera, systems, and FMA selections. | M4 | `critique.md` §3.3.3 |
| 9 | R2.4 | Raycast Mesh Click Callback | Two-stage bounding-box picker dispatching tapped structure to clinical drawer. | M4 | `ATLAS_INTEGRATION_SPEC.md` §2 |
| 10 | R2.5 | Responsive Split / Sheet Layout | Resizable dual pane on desktop (≥768px); bottom sheet on mobile (<768px). | M4 | User Story 11 |
| 11 | R2.6 | IndexedDB Offline PWA Cache | Service worker and IndexedDB caching for 15 binary geometry chunks and FSRS decks. | M4 | User Story 6 |
| 12 | R3.1 | Unified Spatial-Clinical Schema | Consolidated schema linking FMA concepts, spatial relations, and BODHI conditions. | M1 | `critique.md` §3.4 |
| 13 | R3.2 | Recursive Mereological Traversal | Ascending traversal (`PART_OF`, `BRANCH_OF`) resolving sub-structures to visible meshes. | M1 | `ATLAS_INTEGRATION_SPEC.md` §4 |
| 14 | R3.3 | >80% Grounding Coverage | Elevates condition grounding from 2.31% to >80%, and structures to >95%. | M1 | `ATLAS_INTEGRATION_SPEC.md` §4 |
| 15 | R3.4 | Tripartite Concept Crosswalk | Structured bridge mapping `SNOMED_CT <-> FMA_ID <-> Textbook_Passage_Pointer`. | M1 | `critique.md` §2.3.3 |
| 16 | R4.1 | FSRS-5 Spaced-Repetition Engine | Free Spaced Repetition Scheduler v5 computing stability, difficulty, retrievability. | M3 | `v2 research.md` §3, 4.1 |
| 17 | R4.2 | 3D Mesh Occlusion Testing | Masks target structure and generates screen-space projected interactive pins. | M3 | User Story 7 |
| 18 | R4.3 | Pointer-Only Citation Guardrails | Strictly emits `(Book, Ed, Ch, Page)` pointers, omitting copyrighted prose. | M3 | `v2 research.md` §5.1 |
| 19 | R4.4 | Indian Protocol Grounding | Authoritative integration of ICMR, NTEP, MoHFW, WHO guidelines with UI badges. | M3 | User Story 9 |
| 20 | R4.5 | DPDP 2025 Minor Protection | Mandatory 18+ age verification gate, zero behavioral tracking scripts. | M3 | `v2 research.md` §5.3 |
| 21 | R5.1 | E2E Testing Framework & Suite | Opaque-box 4-tier test suite validating all 20 features, publishing `TEST_READY.md`. | E2E_TRACK | Architecture Spec |
| 22 | R5.2 | Final E2E Pass & Hardening | Implementation Track Final Milestone: 100% pass of E2E suite + Tier 5 adversarial hardening. | M5 | Project Pattern Spec |

## Milestones

| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | M1_Knowledge_Graph_Mereology | R3.1, R3.2, R3.3, R3.4 (Schema, mereological engine, recursive CTE traversal, >80% grounding) | none | PLANNED |
| M2 | M2_Backend_Gateway_Streamer | R1.1, R1.2, R1.3, R1.4, R1.5 (FastAPI app, `/api/chat/stream`, `/api/spatial/resolve`, PII filter) | M1 | PLANNED |
| M3 | M3_Recall_Guardrails | R4.1, R4.2, R4.3, R4.4, R4.5 (FSRS-5 engine, 3D occlusion pins, pointer citations, DPDP gate) | M1 | PLANNED |
| M4 | M4_Frontend_Workspace_3D | R2.1, R2.2, R2.3, R2.4, R2.5, R2.6 (Next.js 15 PWA in `apps/web`, Three.js 15 draw calls, Zustand, IndexedDB) | Interface Contracts | PLANNED |
| M5 | M5_Final_E2E_Hardening | R5.2 (Phase 1: 100% pass of Tiers 1-4 E2E tests; Phase 2: Tier 5 adversarial hardening) | M1, M2, M3, M4, E2E_TRACK | PLANNED |
| E2E | E2E_Testing_Track | R5.1 (Opaque-box test suite Tiers 1-4, test runner, test harness, `TEST_READY.md`) | Interface Contracts | PLANNED |

## Interface Contracts

### 1. Gateway ↔ Frontend (`/api/chat/stream`)
- **Protocol**: HTTP SSE (`text/event-stream`).
- **Request Body**:
  ```json
  {
    "messages": [{"role": "user", "content": "Explain aortic stenosis"}],
    "activeFmaIds": ["FMA7088"],
    "activeSystems": ["cardiac", "arterial"],
    "streamSpatialActions": true
  }
  ```
- **Events Emitted**:
  - `event: token\ndata: {"type": "token", "content": "..."}\n\n`
  - `event: spatial_action\ndata: {"type": "spatial_action", "action": "highlight", "conceptIds": ["FMA7101"], "isolate": false}\n\n`
  - `event: spatial_action\ndata: {"type": "spatial_action", "action": "set_camera", "preset": "thoracic_left_oblique", "targetFmaId": "FMA7101", "durationMs": 1000}\n\n`
  - `event: spatial_action\ndata: {"type": "spatial_action", "action": "dissect", "visibleSystems": ["cardiac", "arterial"], "peelSystems": ["skeletal"]}\n\n`
  - `event: done\ndata: {"finish_reason": "stop"}\n\n`

### 2. Frontend ↔ Gateway (`/api/spatial/resolve`)
- **Protocol**: HTTP POST (`application/json`).
- **Request Body**:
  ```json
  {
    "identifier": "FMA7101",
    "includeHierarchy": true,
    "includeCitations": true,
    "maxDepth": 3
  }
  ```
- **Response Body**:
  ```json
  {
    "identifier": "FMA7101",
    "fmaId": "FMA7101",
    "canonicalName": "Aortic valve",
    "latinName": "Valva aortae",
    "system": "cardiac",
    "meshPartIds": ["FJ2104"],
    "boundingBox": [[-12.0, 1140.0, -25.0], [15.0, 1175.0, 10.0]],
    "centroid": [1.5, 1157.5, -7.5],
    "mereology": {
      "parents": [{"fmaId": "FMA7088", "name": "Heart", "relation": "PART_OF"}],
      "children": [{"fmaId": "FMA7192", "name": "Right coronary cusp of aortic valve", "relation": "PART_OF"}]
    },
    "certifiedConditions": [
      {
        "conditionId": "COND:aortic_stenosis",
        "name": "Aortic valve stenosis",
        "relation": "INVOLVES_STRUCTURE",
        "guidelineBadges": ["ICMR"]
      }
    ],
    "citations": [
      {
        "book": "grays",
        "edition": "5th Edition",
        "chapter": "Chapter 4: Thorax",
        "page": "p. 542",
        "pointer": "(Gray's Anatomy, 5e, Ch 4, p. 542)",
        "verifiedFact": "The aortic valve consists of three semilunar cusps."
      }
    ],
    "socraticQuestions": ["What is the hallmark systolic murmur associated with aortic stenosis?"]
  }
  ```

### 3. Mereology Engine ↔ Gateway / Resolver (`rag/mereology.py`)
- Python API:
  - `resolve_structure(fma_or_name: str) -> Optional[ResolvedStructure]`
  - `climb_to_visible_mesh(fma_id: str, max_depth: int = 5) -> Tuple[str, int]` (returns `(visible_parent_fma_id, depth)`)
  - `resolve_condition(condition_label_or_id: str) -> List[ResolvedStructure]`
  - `get_mereology_tree(fma_id: str) -> Dict[str, List[Dict[str, str]]]`

- Anatomical correctness: relation types are not interchangeable. `PART_OF` is containment only; vessel branching is `BRANCH_OF` (coronary arteries are `BRANCH_OF` the aorta, not `PART_OF` the ascending aorta). `climb_to_visible_mesh` climbs only along relations true for the pair and returns "unmapped" rather than a wrong or distant parent. Coverage must not be padded with wrong parent meshes, and systemic conditions get no mesh (excluded from the denominator or reported as "systemic, no mesh").

### 4. FSRS Engine ↔ 3D Occlusion Generator (`rag/fsrs.py`)
- Python API:
  - `calculate_review(card: FSRSCard, rating: int, review_time: datetime) -> FSRSCard`
  - `generate_occlusion_card(fma_id: str, condition_id: Optional[str]) -> OcclusionCard`
  - Projected pin formula: `project(camera)` -> coordinates `(screenX, screenY)` for UI overlay pins 1..N.

## Code Layout

```
/Users/ishaanwadhwa/Projects/med-rag/
├── api/                               # Backend FastAPI Gateway
│   ├── __init__.py
│   ├── main.py                        # FastAPI application, CORS, lifecycle, routing
│   ├── config.py                      # Gateway configuration & DPDP settings
│   ├── models.py                      # Pydantic schemas (ChatStreamRequest, SpatialAction, etc.)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py                    # POST /api/chat/stream SSE streamer
│   │   ├── spatial.py                 # POST /api/spatial/resolve endpoint
│   │   └── health.py                  # GET /api/health
│   └── middleware/
│       ├── __init__.py
│       └── pii.py                     # DPDP client/server PII scrub middleware
├── rag/                               # Clinical RAG & Ontological Engines
│   ├── mereology.py                   # Recursive mereology engine (PART_OF, BRANCH_OF)
│   ├── fsrs.py                        # FSRS-5 spaced-repetition scheduler & occlusion logic
│   ├── guardrails.py                  # Pointer-only citation filter & Indian protocol badges
│   ├── atlas.py                       # Existing atlas bridge (refactored to use mereology)
│   └── ...
├── data/                              # Knowledge Graph & DB files
│   ├── graph/
│   │   ├── mereology_graph.sqlite3    # Unified SQLite mereology & crosswalk DB
│   │   └── atlas_crosswalk.jsonl
│   └── ontology/
│       └── clinical_ontology.jsonl
├── apps/                              # Unified Frontend Workspaces
│   └── web/                           # Next.js 15 / React 19 PWA
│       ├── package.json
│       ├── tsconfig.json
│       ├── next.config.mjs
│       ├── public/
│       │   ├── manifest.json          # PWA manifest
│       │   └── models/                # 15 BodyParts3D binary chunks & atlas.json
│       ├── src/
│       │   ├── app/
│       │   │   ├── layout.tsx         # Root layout with Age Gate & providers
│       │   │   └── page.tsx           # Dual-pane workspace
│       │   ├── components/
│       │   │   ├── canvas/
│       │   │   │   ├── AnatomyCanvas.tsx  # Native Three.js component
│       │   │   │   └── shaders.ts         # DataTexture vertex/fragment shader hooks
│       │   │   ├── chat/              # Socratic chat & SSE consumer
│       │   │   ├── clinical/          # Clinical condition drawer & citations
│       │   │   └── recall/            # FSRS 3D occlusion flashcards
│       │   └── store/
│       │       └── useSpatialStore.ts # Global Zustand store
├── tests/                             # Test Suite
│   ├── test_api.py                    # Gateway & SSE stream integration tests
│   ├── test_mereology.py              # Mereological traversal & coverage tests (>80%)
│   ├── test_fsrs.py                   # FSRS-5 calculations & occlusion card tests
│   ├── test_guardrails.py             # Pointer-only citation & DPDP tests
│   └── e2e/                           # E2E Test Suite (Tiers 1-4)
│       ├── conftest.py
│       ├── test_tier1_features.py     # Tier 1: Feature coverage (≥5 per feature)
│       ├── test_tier2_boundaries.py   # Tier 2: Boundary & corner cases
│       ├── test_tier3_pairwise.py     # Tier 3: Cross-feature combinations
│       └── test_tier4_scenarios.py    # Tier 4: Real-world clinical workflows
├── TEST_INFRA.md                      # E2E Test infrastructure specification
└── TEST_READY.md                      # Published when E2E test suite is complete
```
