# Dispatch Log

## 2026-11-13T08:58:42Z

Sender: ac4db067-eae1-4782-ad74-ebcfd8193682
Priority: MESSAGE_PRIORITY_HIGH

Implement the unified AI-native production platform integrating med-rag (MedEvolv Mentor) and med-rag-atlas per the canonical specification in docs/ATLAS_INTEGRATION_SPEC.md.

Working directory: /Users/ishaanwadhwa/Projects/med-rag
Integrity mode: development

## Requirements

### R1. Backend Application Gateway & SSE Spatial-Semantic Streamer
Migrate the RAG and clinical graph engine from Streamlit behind an asynchronous FastAPI backend (`api/`). Implement the `/api/chat/stream` endpoint delivering Server-Sent Events (SSE) that stream both conversational text tokens and structured spatial actions (`highlight_meshes`, `focus_camera`, `peel_layer`). Implement `/api/spatial/resolve` returning verified pointer-only citations `(Book, Ed, Ch, Page)` and mereologically resolved FMA concepts.

### R2. Unified Frontend Workspace & Native Three.js Integration
Scaffold the unified Next.js 15 / React 19 PWA (`apps/web`). Extract `human-atlas` Three.js canvas directly into the React component tree (eliminating the iframe), preserving GPU DataTexture rendering (15 draw calls). Implement the global Zustand state store synchronizing camera presets, active systems, selected FMA IDs, and raycast mesh click callbacks.

### R3. Unified Spatial-Clinical Knowledge Graph & Mereological Traversal
Upgrade the knowledge graph schema in SQLite / PostgreSQL to unify FMA concepts with BODHI clinical conditions. Implement recursive mereological traversal (`PART_OF`, `BRANCH_OF`) so clinical conditions resolve to visible parent meshes, raising anatomical grounding coverage to >80%.

### R4. Active Recall & Verification Guardrails
Implement FSRS-5 spaced-repetition logic with 3D mesh occlusion testing. Enforce strict pointer-only textbook citations `(Book, Edition, Chapter, Page)` paired with open Indian national protocols (ICMR/NTEP) and DPDP 2025 privacy compliance (18+ age gate, zero tracking).

## Acceptance Criteria

### Gateway & Spatial Stream
- [ ] FastAPI server runs with tests in `tests/test_api.py` verifying `/api/chat/stream` emits valid SSE tokens and `SpatialAction` schemas.
- [ ] `/api/spatial/resolve` resolves FMA IDs and conditions to certified citations without leaking raw copyrighted text.

### Frontend & WebGL Viewport
- [ ] Next.js PWA renders a dual-pane workspace with native Three.js WebGL canvas (no iframes).
- [ ] Zustand store synchronizes selection, camera, and layer state; raycaster mesh click dispatches to clinical drawer.
- [ ] Static geometry and FSRS decks cache in IndexedDB for offline capability.

### Knowledge Graph & Coverage
- [ ] Mereological traversal resolves sub-structures to parent meshes with condition grounding >80%.
- [ ] All tests pass cleanly under `.venv/bin/pytest tests/`.
