# MedEvolv Mentor Wiki

Living repository of tribal knowledge, architectural decisions, and subsystem specifications.

## Architectural Decision Records (ADRs)
- [ADR-001: Unified AI-Native Architecture](decisions/ADR-001-unified-ai-native-architecture.md) — Decision on 2026-11-13 to deprecate Streamlit and build a unified Next.js 15 PWA + FastAPI monorepo with embedded Three.js WebGL canvas.
- [ADR-002: Next release scope](decisions/ADR-002-next-release-scope.md) — Proposed 2026-11-15: post-demo release order (Reset, credits, tooltips, then flowcharts and videos, landing, female atlas), gated on the user's v2-freeze decision.
- [ADR-003: Female study model](decisions/ADR-003-female-study-model.md) — Accepted 2026-11-17 (user choice): the human-atlas-enhanced female study model v3 (male-derived, reshaped, plus HRA female organs) replaces the HRA organs-only set as the default female atlas, labelled "Female (study model)" with per-part origin.

## Subsystems
- [Spatial-Semantic Bridge](subsystems/spatial-semantic-bridge.md) — Bi-directional event bus streaming text tokens + spatial actions and handling 3D mesh click callbacks.
- [Mereological Ontology Graph](subsystems/mereological-ontology-graph.md) — Hierarchical mereology engine (`PART_OF`, `BRANCH_OF`) expanding anatomical condition coverage to >80%.

## Engineering Standards
- [Engineering Principles](standards/engineering-principles.md) — Core development tenets: No Workarounds, Pointer-Only Citations, and High-Level Seam Testing.

## Research
- [Next-release code audit](research/2026-11-15-next-release-code-audit.md) — Read-only audit at `e0eec26` of the landing route, diagrams, videos slot, tooltip coverage, the Reset-view bug and atlas data format.
- [YouTube related videos](research/2026-11-15-youtube-related-videos.md) — Data API v3 quota (about 100 uncached searches/day), policy limits (30-day storage, attribution), no scraping, ontology for related topics.
- [Female 3D anatomy models](research/2026-11-15-female-anatomy-3d-models.md) — HRA Visible Human Female v1.5 (CC BY 4.0, 202 MB GLB) is the best open option; partial skeleton and muscle; conversion plan.
- [slorksmo/Human-Atlas models](research/2026-11-16-slorksmo-human-atlas.md) — Checked 2026-11-16: male = same BodyParts3D as ours (no gain); female = HRA VH_F v1.10, 1,220 parts / 36.6 MB gzip incl. 180 male bones fitted + 76 donor muscles, HRAF ids (no FMA). Recommendation: keep current models.
- [human-atlas-enhanced](research/2026-11-16-human-atlas-enhanced.md) — Checked 2026-11-16: active MIT fork; same BodyParts3D male + HRA v1.5 female (888 parts) as ours; its "female study model" is 2,181 morphed male meshes + 64 HRA parts (experimental). "Enhanced" = viewer/app features, not data. Recommendation: ignore models; optionally port small viewer pieces (cursor zoom, hide/restore, search groups, explode).

## Product specs
- [Next release PRD (2026-11-15)](../prd/2026-11-15-next-release-prd.md) — Draft requirements for the landing page, flowchart maker, YouTube videos, tooltips, Reset view fix and female atlas, with review log.

## Problems
- [Flags stale after deploy](problems/flags-stale-after-deploy.md) — First request after every deploy renders with all feature flags off (build-time ISR HTML); reload fixes; proper fix pending.
- [Flowchart validator: word rules vs meaning](problems/diagram-validator-lexical-limits.md) — Four red-team rounds 2026-11-16/17; 4 meaning flips still pass at e88176b; diagrams turned off live; entailment check proposed.
