# Subsystem: Spatial-Semantic Bridge

## Overview
On 2026-11-13, the team established the Spatial-Semantic Bridge specification to provide low-latency, bi-directional coordination between conversational medical RAG and the Three.js 3D WebGL anatomical viewport.

## Mechanism
1. **Server-to-Client (Text-to-Spatial):**
   - As of `dr-ishaanwadhwa/medevolv-mentor@2ab61ea`, the backend streamed text tokens only.
   - Under the unified design, `/api/chat/stream` emits Server-Sent Events containing interleaved text tokens and typed `SpatialAction` schemas (`highlight`, `camera`, `layer`, `reset`).
   - The React client intercepts these actions and drives the Three.js viewport without re-mounting or reloading geometry.
2. **Client-to-Server (Spatial-to-Text):**
   - Raycaster click events on 3D meshes resolve FMA identifiers in the client Zustand store.
   - The client dispatches `/api/spatial/resolve` to load certified textbook citations, related clinical conditions, and high-yield Socratic inquiry pills in the clinical drawer.

## Related Pages
- [ADR-001: Unified AI-Native Architecture](../decisions/ADR-001-unified-ai-native-architecture.md)
- [Mereological Ontology Graph](mereological-ontology-graph.md)
