# Task Assignment: Milestone 4 Worker (Frontend Workspace & 3D WebGL)

## Mission
Scaffold the unified Next.js 15 / React 19 PWA (`apps/web`), embed the native Three.js canvas directly into the React tree (eliminating the iframe), preserve the 15 draw call GPU DataTexture rendering, implement the Zustand state store, raycast mesh picking, and IndexedDB caching (R2.1, R2.2, R2.3, R2.4, R2.5, R2.6).

## Identity & Working Directory
- TypeName: teamwork_worker
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m4_1/
- Exclusive File Ownership:
  - `apps/web/` (all files within)
  - `pnpm-workspace.yaml` (at repo root if monorepo)

## Mandatory Inputs (Read First)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_frontend_survey_1/handoff.md
- Source assets in `/Users/ishaanwadhwa/Projects/third_party/human-atlas/`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Detailed Requirements
1. **Tooling & Environment**:
   - Node.js 26 and pnpm 12 are in `/opt/homebrew/bin`. Always ensure `export PATH="/opt/homebrew/bin:$PATH"` before executing `pnpm` or `node`.
2. **Scaffold Next.js 15 / React 19 PWA in `apps/web`**:
   - Initialize Next.js 15 App Router app with React 19, TypeScript, Tailwind CSS, Lucide icons, Zustand.
   - Configure `public/manifest.json` for PWA standalone display.
   - Configure Age Gate modal for DPDP 2025 (18+ verification) and zero tracking.
3. **Native Three.js WebGL Canvas (`apps/web/src/components/canvas/AnatomyCanvas.tsx`)**:
   - Port 3D viewer logic from `third_party/human-atlas/app/scene.tsx`.
   - Copy or symlink 3D model assets (`atlas.json` and 15 `body-*.bin.gz` chunks) into `apps/web/public/models/`.
   - Implement system-level geometry merging (`BufferGeometryUtils.mergeGeometries`) ensuring **exactly 15 draw calls** across the 15 anatomical systems.
   - Retain GPU DataTextures (`partTexture` 4096×1 Float32Array, `selectionTexture` 4096×1 Uint8Array) and shader hooks (`#include <begin_vertex>`, `#include <clipping_planes_fragment>`, `#include <color_fragment>`).
   - Use dynamic import with `ssr: false` for client canvas component.
4. **Zustand State Store (`apps/web/src/store/useSpatialStore.ts`)**:
   - Implement state: `activeSystems`, `selectedFmaIds`, `cameraPreset`, `isolate`, `explodeAmount`, `resolvedClinicalData`.
   - Implement actions: `applySpatialAction` (handles SSE `highlight`, `set_camera`, `dissect`, `reset`), `selectMesh`, `toggleSystem`.
5. **Raycast Mesh Picking**:
   - Implement two-stage bounding box + mesh triangle raycasting.
   - When mesh is tapped, resolve FMA ID, update Zustand store, and trigger fetch to `/api/spatial/resolve`.
6. **IndexedDB Offline Caching**:
   - Implement cache in `model-download.ts`: check IndexedDB for geometry chunks before fetching over network.
7. **Dual-Pane / Drawer Layout**:
   - Desktop (≥768px): Dual pane (Chat & Clinical Drawer left, 3D Canvas right).
   - Mobile (<768px): Full-screen 3D Canvas with swipeable bottom drawer.
8. **Build Verification**:
   - Run `pnpm build` in `apps/web` and verify clean build with 0 errors.

## Expected Output
Handoff report at `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/worker_m4_1/handoff.md`.
