# Task Assignment: Milestone 4 Sub-Orchestrator (Frontend Workspace & 3D WebGL)

## Mission
You are the Sub-Orchestrator for Milestone 4: Unified Frontend Workspace & Native Three.js Integration.
Your mission is to execute the iteration loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor) to deliver R2.1, R2.2, R2.3, R2.4, R2.5, and R2.6:
- Next.js 15 / React 19 PWA scaffolded in `apps/web` (no iframes).
- Native Three.js WebGL canvas embedded directly in the React DOM tree, preserving 15 draw call GPU DataTexture rendering (`partTexture`, `selectionTexture`, shader hooks).
- Global Zustand state store (`useSpatialStore`) synchronizing camera presets, active systems, selected FMA IDs, and raycast mesh click callbacks.
- Dual-pane layout on desktop (≥768px) and responsive bottom drawer on mobile (<768px).
- Offline IndexedDB caching for 15 binary geometry chunks and FSRS card decks.
- Build and test verification (`pnpm build` in `apps/web`).

## Identity & Working Directory
- TypeName: sub-orchestrator
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_m4_1/
- Parent Conversation ID: 374680d6-856a-4138-9979-f33b00b59dea

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/sub_orch_m4_1/SCOPE.md
- Survey findings in /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md and /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_frontend_survey_1/handoff.md
- Upstream 3D viewer source in `/Users/ishaanwadhwa/Projects/third_party/human-atlas/`

## Execution Protocol
Follow the orchestrator procedure:
1. Assess scope.
2. Run Iteration Loop (2B):
   - Notice: Use `/opt/homebrew/bin` in PATH for Node.js (`v26.12.1`) and pnpm (`12.18.0`).
   - Spawn Worker with mandatory integrity warning to:
     - Scaffold Next.js 15 / React 19 PWA in `apps/web`
     - Port `AnatomyScene` from `third_party/human-atlas` into native React component `apps/web/src/components/canvas/AnatomyCanvas.tsx`
     - Implement 15-system merged `BufferGeometry` ensuring exactly 15 draw calls
     - Implement Zustand store `apps/web/src/store/useSpatialStore.ts`
     - Implement Raycasting tap detection and `/api/spatial/resolve` hook
     - Implement IndexedDB geometry caching in `model-download.ts`
     - Run `pnpm build` and verify 0 TypeScript/build errors.
   - Spawn Reviewers to check WebGL draw calls, SSR safety (`use client`, `ssr: false`), and Zustand actions.
   - Spawn Challenger to verify WebGL context resilience and raycast callback correctness.
   - Spawn Forensic Auditor (`teamwork_auditor`) for integrity check.
   - Record verdicts in `GATE_STATUS.md`.
3. When gate passes:
   - Mark milestone DONE in `progress.md` and handoff report.
   - Send completion message to parent (ID: 374680d6-856a-4138-9979-f33b00b59dea).
