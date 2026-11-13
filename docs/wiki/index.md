# MedEvolv Mentor Wiki

Living repository of tribal knowledge, architectural decisions, and subsystem specifications.

## Architectural Decision Records (ADRs)
- [ADR-001: Unified AI-Native Architecture](decisions/ADR-001-unified-ai-native-architecture.md) — Decision on 2026-11-13 to deprecate Streamlit and build a unified Next.js 15 PWA + FastAPI monorepo with embedded Three.js WebGL canvas.

## Subsystems
- [Spatial-Semantic Bridge](subsystems/spatial-semantic-bridge.md) — Bi-directional event bus streaming text tokens + spatial actions and handling 3D mesh click callbacks.
- [Mereological Ontology Graph](subsystems/mereological-ontology-graph.md) — Hierarchical mereology engine (`PART_OF`, `BRANCH_OF`) expanding anatomical condition coverage to >80%.

## Engineering Standards
- [Engineering Principles](standards/engineering-principles.md) — Core development tenets: No Workarounds, Pointer-Only Citations, and High-Level Seam Testing.
