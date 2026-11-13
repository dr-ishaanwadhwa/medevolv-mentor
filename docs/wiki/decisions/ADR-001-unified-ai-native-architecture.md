# ADR-001: Unified AI-Native Architecture for Mentor and 3D Atlas

## Context
On 2026-11-13, as of `dr-ishaanwadhwa/medevolv-mentor@2ab61ea`, `med-rag` used a Streamlit Python monolith (`app.py`), and `med-rag-atlas` was an isolated static React/Three.js site embedded via `st.components.v1.iframe` using URL parameters (`?select=FMA...`). This created a unidirectional communication barrier, caused WebGL context thrashing during Streamlit script re-runs, and prevented real-time spatial tool calling during RAG streaming.

## Decision
On 2026-11-13, the team decided to deprecate Streamlit from the production path and merge both systems into a single monorepo production build:
1. **Frontend:** React 19 / Next.js 15 PWA (`apps/web`) with Three.js embedded directly in the DOM tree, sharing a Zustand global state store.
2. **Backend:** Asynchronous FastAPI server (`api/`) providing Server-Sent Events (SSE) streaming for simultaneous conversational tokens and structured spatial actions (`SpatialAction`).
3. **Data Layer:** PostgreSQL / SQLite unifying FMA concepts, spatial mereology (`PART_OF`, `BRANCH_OF`), and BODHI certified clinical facts.
4. **Active Recall:** FSRS-5 spaced repetition with 3D mesh occlusion testing and pointer-only textbook citations `(Book, Edition, Chapter, Page)` paired with open Indian protocols (ICMR/NTEP).

## Consequences
- **Positive:** Enables bi-directional telemetry (mesh clicks prompt the mentor; mentor explanations manipulate 3D camera/highlights in real time); eliminates WebGL reloads; expands anatomical grounding of conditions from 2.3% to >80%; ensures DPDP 2025 compliance.
- **Trade-offs:** Requires maintaining a TypeScript/React frontend alongside Python RAG services; requires local caching of 33 MB BodyParts3D geometry via IndexedDB.

## Related Pages
- [Spatial-Semantic Bridge](../subsystems/spatial-semantic-bridge.md)
- [Mereological Ontology Graph](../subsystems/mereological-ontology-graph.md)
- [Engineering Principles](../standards/engineering-principles.md)
