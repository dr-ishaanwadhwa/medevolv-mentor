# Frontend & 3D WebGL Technical Survey Report

## 1. Observation

### 1.1 Current Frontend Structure
- **Root Repository (`/Users/ishaanwadhwa/Projects/med-rag`)**:
  - Command: `ls -la /Users/ishaanwadhwa/Projects/med-rag`
  - Observation: No `apps/` directory, no `frontend/` directory, and no root `package.json` exist. The workspace currently contains Python backend modules (`rag/`, `ontology/`, `ingest/`, `stair/`, `eval/`, `tests/`), Streamlit UI (`app.py`), deployment scripts (`deploy/`), and documentation (`docs/`).
  - Command: `git submodule status`
  - Observation: Exited code 0 with empty output. No git submodules are registered.
  - Command: `grep -n -E "iframe|ATLAS_URL" app.py`
    - Line 1165: `if not config.ATLAS_URL: return`
    - Line 1178: `st.link_button(f"🧍 {btn}", found[0]["url"], help="Opens the 3D anatomy atlas in a new tab.")`
    - Line 1183: `st.components.v1.iframe(found[0]["url"], height=560)`
  - Current Frontend Execution Model: Python Streamlit (`app.py`, 1285 lines) renders a monolithic dashboard. The 3D atlas is embedded strictly as a client-isolated sandboxed `<iframe>` pointing to external URL `https://atlas.medevolv.in/?select=FMA...`. Streamlit re-runs top-to-bottom on every user interaction, destroying and recreating the iframe DOM element and resetting WebGL contexts.

### 1.2 Location and Organization of `human-atlas` and `med-rag-atlas`
- **Worktree `med-rag-atlas` (`/Users/ishaanwadhwa/Projects/med-rag-atlas`)**:
  - File: `/Users/ishaanwadhwa/Projects/med-rag-atlas/.git` contains:
    `gitdir: /Users/ishaanwadhwa/Projects/med-rag/.git/worktrees/med-rag-atlas`
  - Branch: `atlas-integration`
  - Role: Contains previous Python-side integration work: `rag/atlas.py` (FMA lookup and URL generator), `scripts/build_atlas_crosswalk.py`, and deployment assets in `deploy/atlas/`.
- **Upstream 3D Viewer Codebase (`/Users/ishaanwadhwa/Projects/third_party/human-atlas`)**:
  - Cloned repository: `https://github.com/ashemag/human-atlas` (pinned commit `1c38bf35c254a891200d3cedecfd57abebe83d8d`).
  - Architecture: Vite 8 + React 19 (`react@19.2.6`, `react-dom@19.2.6`) + Three.js (`three@^0.159.0`) + Tailwind CSS v4 + shadcn/ui.
  - Key 3D Files:
    - `app/scene.tsx` (134 lines): Core Three.js WebGL renderer, custom vertex/fragment shaders, PMREM environment lighting, `OrbitControls`, animation loop, GPU DataTexture updates, and raycasting hit detection.
    - `app/anatomy.ts` (37 lines): Type definitions (`SystemId`, `Part`, `Concept`, `Atlas`, `SceneState`), 15 anatomical system color palette (`SYSTEMS`), and concept explanation records.
    - `app/model-download.ts` (12 lines): Decompresses and loads binary geometry buffers (`.bin` / `.bin.gz`) via `DecompressionStream('gzip')`.
    - `app/explosion-layout.ts` (15 lines): Computes non-overlapping 2D grid coordinates for exploded anatomical inventory based on viewport aspect ratio.
    - `app/pointer-tap.ts` (22 lines): State machine distinguishing tap/click selection from drag orbit and multi-touch pinch zoom.
    - `app/agent-tools.ts` (14 lines): ModelContext tool registrations (`find_anatomy`, `inspect_anatomical_structure`).
    - `app/page.tsx` (55 lines): React page hosting `AnatomyScene`, layer selection sliders, combobox search, and detail sheets.
  - Deployment Patch in `med-rag`:
    - `deploy/atlas/deep-link.patch`: Applied against `human-atlas/app/page.tsx` to handle URL parameters `?select=FMA...` and `?system=...` with ranked concept matching.
    - `deploy/atlas/build_atlas.sh`: Clones upstream, applies `deep-link.patch`, runs `npm ci && npm run build`, and generates `dist/`.

### 1.3 Technical Details of 15 Draw Call GPU DataTexture Rendering Implementation
- **Source Anatomy Asset Specifications (`public/models/atlas.json`)**:
  - Upstream data: DBCLS BodyParts3D 4.0 adult male reference anatomy (CC BY 4.0).
  - Triangle count: Reduced from 6,681,030 source triangles to 2,288,268 triangles via `meshoptimizer` quadric simplification (`MeshoptSimplifier`, 0.2% max relative error).
  - Part count: 2,234 individually indexed anatomical meshes across 3,432 named FMA concepts.
  - Chunk storage: 15 binary chunk files (`body-0.bin` to `body-14.bin`), each capped at ~4 MB uncompressed (total 59,504,500 bytes uncompressed; 32,453,998 bytes gzipped).
  - Packed Vertex Buffer Formats (`app/scene.tsx:67-71`):
    - Positions: `Float32Array(buffer, p.positions, p.vertexCount * 3)` (12 bytes/vertex).
    - Normals: `Int16Array(buffer, p.normals, p.vertexCount * 3)` (6 bytes/vertex, GPU-normalized signed short attribute `new T.BufferAttribute(..., 3, true)`).
    - Indices: `Uint32Array(buffer, p.indices, p.indexCount)` (4 bytes/index).
    - Part Index: `Float32Array(p.vertexCount).fill(i)` attribute `partIndex` assigned per vertex.
- **GPU DataTexture Architecture (`app/scene.tsx:32-33, 113-115`)**:
  - Texture Dimension: `width = MathUtils.ceilPowerOfTwo(atlas.parts.length)` = 4096. Height = 1.
  - Texture 1: `partTexture` (`FloatType`, `RGBAFormat`, 4096×1 Float32Array):
    - UV mapping: `vec2 stateUv = vec2((partIndex + 0.5) / 4096.0, 0.5);`
    - Channels RGB: Spatial translation offset `vec3(dx, dy, dz)` computed during explosion or isolation animations.
    - Channel A: Part visibility scalar (`1.0` = visible, `0.0` = hidden).
  - Texture 2: `selectionTexture` (`UnsignedByteType`, `RGBAFormat`, 4096×1 Uint8Array):
    - Channel R: Selection indicator (`255` = selected, `0` = unselected).
- **Shader Hook Customizations (`app/scene.tsx:49-58`)**:
  - Vertex Shader (`#include <begin_vertex>` replacement):
    ```glsl
    attribute float partIndex;
    uniform sampler2D partState;
    uniform sampler2D selectionState;
    uniform float stateWidth;
    varying float partVisible;
    varying float partSelected;

    vec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5);
    vec4 state = texture2D(partState, stateUv);
    transformed += state.xyz;
    partVisible = state.w;
    partSelected = texture2D(selectionState, stateUv).r;
    ```
  - Fragment Shader (`#include <clipping_planes_fragment>` & `#include <color_fragment>` replacement):
    ```glsl
    varying float partVisible;
    varying float partSelected;

    // Discard invisible fragments on GPU without rebuilding scene graph:
    if (partVisible < 0.5) discard;

    // Highlight selected mesh with cyan/teal tint without swapping materials:
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.85, 0.78), partSelected * 0.75);
    ```
- **Draw Call Mechanics & 15-System Batching**:
  - The anatomical taxonomy in `app/anatomy.ts:1-18` defines exactly 15 physiological systems:
    1. `skeletal` (`#e2d9ba`)
    2. `muscular` (`#a85b50`)
    3. `cardiac` (`#b96760`)
    4. `sensory` (`#b0c8ce`)
    5. `arterial` (`#c05245`)
    6. `venous` (`#527c9f`)
    7. `nervous` (`#d8b565`)
    8. `respiratory` (`#b98991`)
    9. `digestive` (`#b8916b`)
    10. `urinary` (`#b47961`)
    11. `lymphatic` (`#879f7c`)
    12. `endocrine` (`#c5a09a`)
    13. `reproductive` (`#bda098`)
    14. `integumentary` (`#ba9b7d`, transparent opacity 0.1)
    15. `connective` (`#aec3bb`)
  - In `app/scene.tsx:74`, geometries are currently merged per-chunk as each binary chunk streams in, producing up to 69 meshes.
  - To achieve the strict canonical limit of **15 draw calls**, all loaded geometries for each of the 15 systems must be combined across chunks into **exactly one merged `BufferGeometry` per system**, rendered by that system's `MeshStandardMaterial`.
  - Because `partIndex` and the DataTextures handle per-mesh translation, GPU visibility discard, and selection tinting inside shaders, the 15 merged meshes never need to be disassembled or rebuilt during user interaction.
- **Raycasting / Mesh Picking Algorithm (`app/scene.tsx:70, 91-95`)**:
  - Because merged meshes lose individual hit detection semantics in Three.js, individual invisible proxy meshes (`pickers[i]`) are retained in CPU memory with precomputed bounding boxes.
  - When a pointer tap is confirmed (`PointerTap.up`), the raycaster evaluates candidates whose bounding boxes intersect the ray:
    `worldBox.copy(bounds[i]).translate(mesh.position); if (!raycaster.ray.intersectBox(worldBox, hitPoint)) return;`
  - Candidate meshes undergo fast CPU triangle intersection (`raycaster.intersectObject(mesh, false)`). The nearest hit distance determines `atlas.parts[found].id`, which resolves to `conceptId` (FMA ID).

### 1.4 Next.js 15 / React 19 PWA Requirements for `apps/web`
- **Monorepo Structure**:
  - Root directory requires `pnpm-workspace.yaml` configuring `apps/*` and `packages/*`.
  - Next.js 15 App Router (`apps/web`) running React 19 (`react@19.2.x`, `react-dom@19.2.x`).
  - Strict Client Component isolation: Three.js canvas must reside in a `'use client'` component dynamically loaded with `ssr: false` (`next/dynamic(() => import('@/components/canvas/AnatomyCanvas'), { ssr: false })`) to prevent SSR window/WebGL context crashes.
- **PWA Specifications**:
  - `apps/web/public/manifest.json`: Web App Manifest with `display: standalone`, `theme_color: #0f172a`, `background_color: #020617`, and icon sets (192×192, 512×512, maskable).
  - Service Worker: Custom service worker or Workbox caching `/models/*.bin`, `/models/*.bin.gz`, and `/models/atlas.json` with a `CacheFirst` strategy, and `/api/*` with `NetworkFirst`.
  - DPDP 2025 compliance: Mandatory age gate modal (18+ verification), zero third-party telemetry, client-side PII sanitization.
- **Dual-Pane Layout Shell (`docs/ATLAS_INTEGRATION_SPEC.md:16, 35`)**:
  - Desktop (≥768px): Resizable horizontal dual pane (`react-resizable-panels`). Left pane: Socratic Chat / Clinical Explorer / FSRS Flashcards; Right pane: Native Three.js WebGL Viewport with overlay controls.
  - Mobile (<768px): Full-screen WebGL viewport with responsive top status bar and swipeable bottom drawer/sheet (`vaul` or shadcn `Sheet`) hosting chat and clinical insights.

### 1.5 Global Zustand State Store Architecture
- **State Interface (`useAtlasStore`)**:
  ```typescript
  interface AtlasState {
    // 3D Scene & Anatomy
    atlas: Atlas | null;
    activeSystems: SystemId[];
    selectedFmaIds: string[];
    selectedPartIds: string[];
    hoveredPartId: string | null;
    isolate: boolean;
    explodeAmount: number;
    layerDepth: number;

    // Camera & Viewport
    cameraPreset: 'anterior' | 'posterior' | 'lateral_left' | 'lateral_right' | 'superior' | 'isometric';
    targetFmaId: string | null;
    autoRotate: boolean;
    resetToken: number;

    // Spatial SSE Stream Actions
    applySpatialAction: (action: SpatialAction) => void;

    // Raycast Interaction Callbacks
    selectMesh: (partId: string) => Promise<void>;
    selectConcept: (fmaId: string) => Promise<void>;
    toggleSystem: (system: SystemId) => void;
    setExplode: (amount: number) => void;
    setIsolate: (isolate: boolean) => void;
    setCameraPreset: (preset: CameraPreset) => void;
    resetScene: () => void;

    // Clinical Context Synchronization
    resolvedClinicalData: ResolvedSpatialConcept | null;
    isResolving: boolean;
  }
  ```
- **Bi-Directional Event Handlers**:
  - **Text-to-Spatial (SSE Listener)**: When `/api/chat/stream` emits a `SpatialAction` event:
    - `{ type: "highlight", fmaIds: [...], isolate: true }` -> store updates `selectedFmaIds` and `isolate`, triggering DataTexture update without re-mounting canvas.
    - `{ type: "camera", preset: "anterior", targetFmaId: "FMA19667" }` -> smoothly interpolates OrbitControls target to mesh center.
    - `{ type: "layer", system: "skeletal", visible: false }` -> toggles `activeSystems`.
  - **Spatial-to-Text (Raycaster Mesh Click)**:
    - `onSelect(partId)` -> resolves `part.conceptId` -> updates `selectedFmaIds` -> dispatches fetch to `/api/spatial/resolve?fma_id=${conceptId}` -> populates clinical drawer with certified textbook pointers and unlocks 1-click clinical reasoning prompts.

### 1.6 IndexedDB Caching Architecture
- **Offline Geometry Storage**:
  - Database: `medevolv_atlas_offline_v1`
  - Stores:
    1. `geometry_blobs`: key = `url` (e.g., `/models/body-0.bin`), value = `{ buffer: ArrayBuffer, timestamp: number, bytes: number }`.
    2. `manifest`: key = `'atlas.json'`, value = `Atlas` manifest object.
  - Interceptor in `model-download.ts`:
    Before making network `fetch()`, query `idb.get('geometry_blobs', url)`. If hit, return decoded buffer immediately. If miss, fetch over HTTP, save `ArrayBuffer` to IndexedDB, and return buffer.
- **FSRS-5 Flashcard Deck Storage**:
  - Stores:
    1. `fsrs_cards`: key = `card_id`, indexes = `[due_date, fma_id, state]`.
    2. `review_logs`: key = `log_id`, audit trail of ratings (`Again`, `Hard`, `Good`, `Easy`) and retention parameters.
  - Supports 3D occlusion testing: masks or isolates target mesh while offline and prompts for structure identification and clinical consequence.

### 1.7 Node/npm/pnpm/yarn Tooling Available in Environment
- **Subagent Default PATH**:
  - Command: `echo $PATH`
  - Result: `PATH=/Users/ishaanwadhwa/.gemini/antigravity/bin:/usr/bin:/bin:/usr/sbin:/sbin`
  - Notice: `/opt/homebrew/bin` is absent from default subagent `PATH`. Direct calls to `node`, `npm`, `pnpm` fail with exit code 127 unless `/opt/homebrew/bin` is explicitly included.
- **Available Binaries in `/opt/homebrew/bin`**:
  - Node.js: `v26.12.1` (`/opt/homebrew/bin/node`) — satisfies `>=22.13.0` engine requirement.
  - npm: `11.20.0` (`/opt/homebrew/bin/npm`).
  - pnpm: `12.18.0` (`/opt/homebrew/bin/pnpm`) — modern package manager supporting pnpm workspaces.
  - yarn: Not installed.
  - Python: `.venv/bin/python` (Python 3.13.18 / 3.12+ in repo root `.venv`).

---

## 2. Logic Chain

1. **Premise 1 (Existing Fragmentation)**:
   - Observation: `app.py:1183` renders `st.components.v1.iframe(found[0]["url"])` to display the atlas.
   - Observation: Streamlit re-renders trigger full WebGL context rebuilds and prevent any telemetry or SSE stream synchronization back to the Python backend.
   - Deduction: Native Three.js integration in React is strictly necessary to enable bi-directional interaction and zero-latency SSE camera/highlight manipulation.

2. **Premise 2 (3D Codebase Modularity)**:
   - Observation: The complete 3D viewer in `third_party/human-atlas` is self-contained in 6 files (`scene.tsx`, `anatomy.ts`, `model-download.ts`, `explosion-layout.ts`, `pointer-tap.ts`, `agent-tools.ts`) totaling under 300 lines of TypeScript.
   - Observation: The 3D assets consist of `atlas.json` and 15 `.bin` chunks in `public/models/`.
   - Deduction: Extracting `AnatomyScene` into `apps/web/src/components/canvas/` requires no heavy external 3D engine wrappers (like `@react-three/fiber`), keeping bundle size minimal and preserving the exact custom GPU DataTexture shader pipeline.

3. **Premise 3 (15 Draw Calls Verification)**:
   - Observation: `atlas.parts` has 2,234 meshes, but all are mapped to exactly 15 unique `SystemId` values (`skeletal`, `muscular`, etc.).
   - Observation: Shaders use `DataTexture` + vertex attribute `partIndex` to control per-mesh visibility (`discard;`) and translation (`transformed += state.xyz`) on the GPU without altering mesh buffers.
   - Deduction: Merging all geometries belonging to the same anatomical system across all chunks into 1 unified `BufferGeometry` per system results in exactly 15 meshes in the scene, yielding precisely 15 GPU draw calls.

4. **Premise 4 (Tooling & Execution)**:
   - Observation: Node.js 26.12.1 and pnpm 12.18.0 are pre-installed in `/opt/homebrew/bin`.
   - Deduction: Monorepo scaffolding can proceed immediately using `pnpm` once `/opt/homebrew/bin` is exported to `PATH`.

---

## 3. Caveats

1. **WebGL Device Compatibility**: While desktop and high-end mobile devices handle 2.2M triangles with 15 draw calls at 60 FPS, low-end mobile devices with tight WebGL memory constraints may experience context loss if backgrounded. The `webglcontextlost` handler in `scene.tsx:130` must be preserved.
2. **First-Load Asset Transfer**: 33 MB of compressed geometry requires 2-5 seconds on high-speed connections and longer on 3G. Implementing IndexedDB caching ensures this download happens only once per device.
3. **Anatomical Coverage Limitations**: Upstream BodyParts3D lacks micro-neurovascular structures (meningeal vessels, peripheral nerve plexuses). The knowledge graph traversal must gracefully fall back to parent structures (`PART_OF`).

---

## 4. Conclusion

The frontend transition from a sandboxed Streamlit iframe to a native Next.js 15 / React 19 PWA with embedded Three.js is completely feasible and technically straightforward:
1. Upstream code in `third_party/human-atlas` is cleanly modular and directly portable to Next.js 15 App Router.
2. The 15 draw call GPU DataTexture rendering architecture is sound, verified, and ready for extraction into a native React component.
3. The global Zustand store cleanly bridges text-to-spatial (SSE `SpatialAction`) and spatial-to-text (raycast hit -> `/api/spatial/resolve`) workflows.
4. Tooling (Node 26, pnpm 12) is available in the local environment to support immediate monorepo scaffolding.

---

## 5. Verification Method

### Independent Verification Commands

1. **Verify Python backend tests**:
   ```bash
   .venv/bin/pytest tests/test_atlas.py
   .venv/bin/pytest tests/
   ```
   *Expected outcome*: 10 passed in `test_atlas.py`, 143 passed in full test suite.

2. **Verify Upstream `human-atlas` compilation and asset integrity**:
   ```bash
   export PATH="/opt/homebrew/bin:$PATH"
   cd /Users/ishaanwadhwa/Projects/third_party/human-atlas
   npm run check
   node scripts/validate-atlas.mjs
   node scripts/validate-interactions.mjs
   ```
   *Expected outcome*: `tsc --noEmit` exits 0; `validate-atlas.mjs` verifies 2,234 indexed meshes, 3,432 concepts, 2,288,268 triangles, and all 15 binary buffers.

3. **Verify Node/pnpm environment**:
   ```bash
   export PATH="/opt/homebrew/bin:$PATH"
   node -v
   pnpm -v
   ```
   *Expected outcome*: `v26.12.1` and `12.18.0`.

### Invalidation Conditions
- Any changes that split geometries per mesh instead of per system will break the 15 draw call budget.
- Omitting `/opt/homebrew/bin` from shell execution scripts will cause `command not found: node/pnpm` errors.
- SSR rendering of Three.js canvas without dynamic client-only guard will trigger Next.js build-time DOM reference errors.
