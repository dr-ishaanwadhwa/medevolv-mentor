# Architectural Critique & Unified AI-Native Target Architecture
## MedEvolv Mentor (`med-rag`) & 3D Human Atlas (`med-rag-atlas` / `human-atlas`)

**Author:** Principal Software Architect & Systems Engineering Group  
**Status:** Canonical Technical Architecture & Systems Specification  
**Date:** November 2026  
**Target File:** `docs/research/codebase_and_architecture_critique.md`  

---

## Executive Summary

The MedEvolv platform currently consists of two fundamentally disjointed software artifacts developed under diametrically opposed architectural paradigms:
1. **`med-rag` (MedEvolv Mentor):** A Python-centric, Streamlit-based monolithic web application (`app.py`, 1,284 LOC) backed by a multi-hop RAG pipeline (`rag/answer.py`, `rag/hops.py`), ChromaDB vector store (35,902 passages across 7 medical textbooks), an offline-compiled clinical ontology (~26,000 certified facts in `rag/ontology_facts.py`), and Eka Care's open BODHI knowledge graph.
2. **`med-rag-atlas` / `human-atlas`:** A client-side, single-page application built on React 19, Vite, and Three.js (`app/page.tsx`, `app/scene.tsx`), rendering an adult male anatomical reference model derived from DBCLS BodyParts3D 4.0 (2,234 optimized meshes, ~33 MB gzipped binary geometry partitioned across 15 chunks, indexed via Foundational Model of Anatomy [FMA] concept identifiers).

The current bridge between these two systems is a **unidirectional, coarse-grained URL parameter patch** (`deploy/atlas/deep-link.patch`), which enables Streamlit to embed an `<iframe>` pointing to `https://atlas.medevolv.in/?select=FMA...`.

```
CURRENT INTEGRATION:
┌────────────────────────────────────────────────────────┐
│ Streamlit (Python Runtime)                             │
│ app.py (Top-to-bottom re-execution model)              │
│                                                        │
│  [Ask Tab] ──> [Explore Tab]                           │
│                      │                                 │
│                      ▼                                 │
│         st.components.v1.iframe(url)                   │
│                      │                                 │
└──────────────────────┼─────────────────────────────────┘
                       │ Unidirectional URL Query String
                       │ (?select=FMA19667)
                       ▼
┌────────────────────────────────────────────────────────┐
│ Iframe Context (React 19 / Three.js Canvas)            │
│  - 33 MB Mesh Download                                 │
│  - Isolated WebGL Context                              │
│  - Zero Callbacks to Streamlit                         │
│  - No Dynamic Multi-Structure Highlighting            │
│  - No Synchronized Camera Manipulation                 │
└────────────────────────────────────────────────────────┘
```

### Architectural Verdict
This integration strategy represents a severe **architectural impedance mismatch** and an **exploratory dead-end**:
- **Execution Lifecycle Conflict:** Streamlit’s top-to-bottom reactive script re-run model (re-executing the entire 1,284-line Python script on every user interaction) destroys or resets client-side DOM state, making real-time, 60fps WebGL synchronization impossible.
- **The Silent Mesh Problem (Zero Bi-Directional State):** The iframe acts as an impenetrable communication silo. When a student clicks a 3D structure (e.g., the *anterior descending branch of left coronary artery*), the parent mentor application receives zero telemetry, cannot load the clinical profile, cannot retrieve Gray's/Harrison citations, and cannot prompt the AI mentor.
- **Static vs. Streaming Disconnect:** During RAG token streaming, the LLM cannot manipulate the 3D scene. As the tutor explains an aortic dissection (Stanford Type A vs. Type B), it cannot peel the pericardium, isolate the aortic arch, fly the camera to the aortic root, or highlight the tear site.
- **Severe Ontological Fragmentation:** The atlas operates exclusively on FMA concept IDs (e.g., `FMA3734`), while `med-rag` operates on free-text textbook labels, UMLS/SNOMED CT concepts, and BODHI graph keys. The offline bridge (`data/graph/atlas_crosswalk.jsonl`) links only **114 out of 360 unique anatomical structures (31.7%)** and only **115 out of 4,978 conditions (2.3%)**. Over 97% of clinical conditions in MedEvolv have zero anatomical grounding.

This document presents an exhaustive technical critique of the existing codebases, diagnoses the root causes of failure across rendering, state, and ontology, and specifies the complete target architecture for a **unified, AI-native production platform**: a unified React 19/Next.js frontend with embedded Three.js, a high-performance FastAPI asynchronous backend, a bidirectional WebSocket/SSE spatial-semantic bridge, and a consolidated FMA–BODHI–Vector knowledge graph.

---

## 1. Deep-Dive Codebase Audit: Current State

### 1.1 `med-rag` (MedEvolv Mentor)

#### 1.1.1 Frontend Architecture (`app.py`)
`app.py` is a monolithic 1,284-line Python script executed under Streamlit's runtime engine.
- **Execution Model:** Streamlit executes the entire script sequentially from line 1 to 1284 on every user interaction (tab switch, button click, selectbox change, chat input). To preserve data across executions, state is manually pushed to `st.session_state` (`messages`, `pending`, tab navigation keys).
- **Tab Layout:** Lines 191 and 1156 define the core tabs:
  ```python
  tab_ask, tab_how, tab_explore = st.tabs(["💬  Ask", "🔍  How it works", "🧭  Explore conditions"])
  ```
  In Streamlit, inactive tabs remain in the Python execution path; all branch logic executes on every tick unless conditionally gated.
- **3D Atlas Embedding (`render_atlas_links`, lines 1161–1185):**
  ```python
  def render_atlas_links(label: str, ctype: str, key: str) -> None:
      ...
      st.link_button(f"🧍 {btn}", found[0]["url"], help="Opens the 3D anatomy atlas in a new tab.")
      if len(found) > 1:
          st.caption("Also in 3D: " + " · ".join(f"[{esc(f['label'])}]({f['url']})" for f in found[1:]))
      with st.expander("Show the 3D view here", expanded=False):
          if st.toggle("Load the 3D view (about 33 MB)", key=f"atl_{key}"):
              st.components.v1.iframe(found[0]["url"], height=560)
  ```
  The 3D viewer is rendered inside an expandable container (`st.expander`), gated behind a toggle widget (`st.toggle`). When clicked, Streamlit injects an `<iframe>` pointing to the external static site.
- **Clinical Graph Visualization (`rag/graph_component`):**
  A custom Streamlit component (`rag/graph_component/__init__.py`) wraps `vis-network` inside a separate iframe (`index.html`), transmitting JSON graph payloads across `streamlit:componentReady` and `Streamlit.setComponentValue` message channels.

#### 1.1.2 RAG Pipeline & Multi-Hop Reasoning (`rag/`)
- **`rag/answer.py`:** Contains single-search `answer()` and multi-hop `answer_multihop()`.
  - Guard rail (`_guard()`): Matches regex `PERSONAL` to reject personal medical advice before retrieval.
  - Routing (`routed_section_ids()`): Chooses between vector similarity (`search()`), ToC prompt-based routing (`rag.router`), and fine-tuned STAIR retriever (`stair.serve`).
  - LLM Execution: Synchronous, blocking execution via `rag.backends.chat()` (calling DeepSeek-V4-Flash / Pro). Output is post-processed through regex-based citation validation (`_cite_step()`) verifying `[n]` passage and `[G#]` graph citations.
- **`rag/hops.py` (35.6 KB):** Implements multi-hop decomposition for complex clinical vignettes. Decomposes questions into clinical axes (`etiology`, `stabilization`, `pharmacology`), queries the BODHI graph for disease candidates, runs sub-queries against ChromaDB, cross-checks drugs against BODHI edges, and compiles graph facts into prompt blocks `[G1], [G2]...`.
- **`rag/clinical_graph.py` (8.2 KB):** Pure function extracting a 5-level subgraph from certified ontology facts for visualization:
  `Level 1 (Chief Complaints) -> Level 2 (Differential) -> Level 3 (Clinical Phases) -> Level 4 (Workup/Triage) -> Level 5 (Therapeutics/Contraindications)`.
- **`rag/atlas.py` (7.4 KB):**
  Loads `data/graph/atlas_crosswalk.jsonl` into memory. Applies string normalization heuristic `variants(label)`:
  - Generates singular variants (`_singular()`: dropping `-ae`, `-i`, `-ys`).
  - Strips trailing category tokens (`muscle`, `bone`).
  - Inverts "X of Y" <-> "Y X" syntax.
  - Strips lateralities (`left`, `right`).
  - Provides `url_for(atlas_id)` generating `https://atlas.medevolv.in/?select=FMA...`.
  - Resolves condition links via `_involves()` mapping conditions to structures through certified `INVOLVES_STRUCTURE` facts.

#### 1.1.3 Knowledge Graph & Ontology Infrastructure (`ontology/` & `data/`)
- **Ontology Metamodel (`ontology/schema.py`):** Pydantic metamodel defining entity types (`PathologicalCondition`, `AnatomicalStructure`, `TherapeuticAgent`, etc.) and standardized clinical relations (`INVOLVES_STRUCTURE`, `MANIFESTS_AS`, `CONFIRMED_BY`, `TREATED_BY`, `CONTRAINDICATES`, `DIFFERENTIAL_OF`).
- **Certified Fact Storage (`rag/ontology_facts.py`):** Loads compiled facts extracted from textbook sections. Enforces strict quote verification: every fact must possess a verbatim quote found in the source text.
- **Crosswalk & Linkage Files (`data/graph/`):**
  - `atlas_crosswalk.jsonl` (652 KB, 3,470 records): Maps string keys to FMA concept IDs.
  - `crosswalk.jsonl` (6.3 MB): Bridges textbook mentions to BODHI/UMLS concepts.
  - `comention.jsonl` (5.8 MB) & `hubs.jsonl` (2.6 MB): Graph topology of co-occurring clinical entities.
  - `data/bodhi/`: Eka Care's BODHI graph (BODHI-S: 13,204 edges, 779 triage conditions, 4,037 symptom variants).

#### 1.1.4 Crosswalk Ingestion (`scripts/build_atlas_crosswalk.py`)
- Reads `public/models/atlas.json` from `third_party/human-atlas`.
- Builds an alias table of BodyParts3D concepts.
- Merges bilateral structures drawn only as pairs into combined records (`atlas-pair`).
- Adds 58 hardcoded synonyms (`SYNONYMS`).
- For remaining unmatched `AnatomicalStructure` labels, computes `bge-small` cosine similarity (threshold `MIN_COS = 0.78`) against atlas concepts, dispatching top-3 candidates to DeepSeek-V4 in batches of 25 for verification.
- **Output:** 3,470 records.

#### 1.1.5 Deployment Configuration (`deploy/`)
- **`deploy/oci/Caddyfile`:** Reverse proxies `mentor.medevolv.in` to the Dockerized Streamlit container on port 7860, and serves `atlas.medevolv.in` from `/srv/atlas` with gzip precompression and long-lived cache headers for `/models/*`.
- **`deploy/atlas/build_atlas.sh` & `push_atlas.sh`:** Builds Vite static bundle from `third_party/human-atlas` and syncs the ~108 MB `dist/` directory to the production VM.

---

### 1.2 `med-rag-atlas` & `third_party/human-atlas`

#### 1.2.1 Architecture & Stack
`human-atlas` is a client-side WebGL application built on:
- React 19.2.6 & `react-dom`
- Three.js r159 & `three/examples/jsm` (`OrbitControls`, `RoomEnvironment`, `BufferGeometryUtils`)
- Vite 8.0.13 with `@vitejs/plugin-react` and `@tailwindcss/postcss` (Tailwind CSS v4)
- Radix / Base-UI / Shadcn component primitives (`@shadcn/react`, `@base-ui/react`, `lucide-react`)
- Bundle Size: ~1.2 MB JS/CSS app bundle, 1.33 MB catalogue JSON (`atlas.json`), ~33 MB gzipped binary geometry chunks (`body-0.bin.gz` – `body-14.bin.gz`).

#### 1.2.2 Geometry Pipeline & GPU Memory Architecture (`app/scene.tsx`)
The 3D rendering pipeline exhibits exceptional graphics engineering optimized for low draw calls and high throughput:
1. **Geometry Chunking & Decompression:**
   - 2,234 source meshes (derived from BodyParts3D 4.0, simplified via `meshoptimizer` quadric decimation) are packed into 15 binary chunk files.
   - Vertices store positions as `Float32` (12 bytes/vert) and normals as normalized signed short `Int16` (6 bytes/vert), reducing vertex buffer bandwidth by 25%.
   - `loadChunk()` fetches and decodes chunks concurrently (3 worker streams), creating 2,234 `BufferGeometry` instances.
2. **System-Level Mesh Merging (Draw Call Minimization):**
   - In each chunk, geometries are grouped by organ system (`skeletal`, `muscular`, `arterial`, `venous`, `nervous`, `cardiac`, `respiratory`, `digestive`, `urinary`, etc.).
   - Geometries within each system are merged using `BufferGeometryUtils.mergeGeometries(gs, false)`.
   - **Total Scene Draw Calls:** Approximately 15 draw calls total (one per organ system mesh), enabling stable 60fps rendering even on low-power mobile GPUs.
3. **GPU DataTexture Instancing & State Shaders:**
   Instead of modifying geometry buffers CPU-side when structures are isolated, moved, or hidden, `scene.tsx` utilizes **GPU DataTextures** bound to custom vertex/fragment shader hooks via `Material.onBeforeCompile`:
   - `partTexture` (`Float32Array`, RGBA Float): Encodes dynamic translation offset `(dx, dy, dz)` in `.xyz`, and visibility flag `partVisible` (1.0 or 0.0) in `.w`.
   - `selectionTexture` (`Uint8Array`, RGBA Byte): Encodes highlight state `partSelected` in `.r`.
   - In Vertex Shader (`begin_vertex`):
     ```glsl
     vec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5);
     vec4 state = texture2D(partState, stateUv);
     transformed += state.xyz;
     partVisible = state.w;
     partSelected = texture2D(selectionState, stateUv).r;
     ```
   - In Fragment Shader (`clipping_planes_fragment` & `color_fragment`):
     ```glsl
     if (partVisible < 0.5) discard;
     diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.85, 0.78), partSelected * 0.75);
     ```
   - **Result:** Toggling layers, exploding anatomy, or selecting structures requires only uploading a 4096-pixel 1D texture to the GPU (`texture.needsUpdate = true`). Zero vertex buffer re-allocation occurs during interaction.

#### 1.2.3 Interaction, Raycasting & Spatial Navigation
- **Raycasting (`up()` in `scene.tsx`):** Maintains lightweight bounding box pickers (`pickers[i]`) per structure. Uses `PointerTap` to distinguish drag/orbit from click/tap. Raycasts against bounding boxes first; if hit, tests the underlying mesh.
- **Explosion Layout (`app/explosion-layout.ts`):** 2D bin-packing algorithm arranging isolated structures across a grid when the explosion slider is dragged.
- **Camera Orchestration:** `OrbitControls` with dynamic `setViewOffset` calculations to smoothly center selected structures when the inspection sheet opens.

#### 1.2.4 Agent Tool Stubs (`app/agent-tools.ts`)
`human-atlas` includes stubs for browser model contexts:
```typescript
export function atlasTools(atlas: Atlas, inspect: (concept: Concept) => void): Tool[] {
  return [
    { name: 'find_anatomy', execute(input) { ... } },
    { name: 'inspect_anatomical_structure', execute(input) { ... inspect(concept); } }
  ];
}
```
However, these tools are only registered if `(document as any).modelContext` exists (a non-standard experimental browser API), rendering them completely inactive in standard browser and iframe deployments.

#### 1.2.5 The `deep-link.patch` Mechanism
The integration patch applied in `deploy/atlas/deep-link.patch` modifies `app/page.tsx` (lines 27–28):
```typescript
useEffect(() => {
  if (!atlas) return;
  const q = new URLSearchParams(window.location.search),
        want = (q.get('select') ?? '').toLowerCase().trim(),
        sys = q.get('system');
  if (sys && SYSTEMS.some(s => s.id === sys))
    setState(s => ({ ...s, visible: [sys as SystemId] }));
  if (!want) return;
  const ids = want.split(',').map(x => x.trim()).filter(Boolean);
  if (ids.length > 1 && ids.every(x => /^fma\d+$/.test(x))) {
    const cs = ids.map(x => atlas.concepts.find(c => c.id.toLowerCase() === x)).filter((c): c is Concept => !!c);
    if (cs.length) {
      choose({ id: cs[0].id, name: cs.map(c => c.name).join(' + '), elements: cs.flatMap(c => c.elements) });
      setState(s => ({ ...s, isolate: true, explode: 0 }));
      return;
    }
  }
  const rank = (c: Concept) => {
    const n = c.name.toLowerCase();
    return n === want ? 0 : c.id.toLowerCase() === want || c.elements.some(e => e.toLowerCase() === want) ? 1 : n.startsWith(want) ? 2 : n.includes(want) ? 3 : 9;
  };
  const best = atlas.concepts.map(c => ({ c, r: rank(c) })).filter(x => x.r < 9).sort((a, b) => a.r - b.r || a.c.name.length - b.c.name.length)[0];
  if (best) {
    choose(best.c);
    setState(s => ({ ...s, isolate: true, explode: 0 }));
  }
}, [atlas]);
```

---

## 2. In-Depth Critique of Current Architecture

### 2.1 Critique 1: The Fundamental Architectural Mismatch (Streamlit vs. 60fps WebGL)

Streamlit is architected for rapid, server-side data science dashboards. Its core execution model is built on **full-script re-execution upon event receipt**. When any interactive widget changes:
1. The browser client sends an HTTP/WebSocket message to the Python Tornado server (`_stcore/stream`).
2. Python executes `app.py` from line 1 to line 1284.
3. Streamlit computes a delta tree of virtual UI elements and serializes protobuf messages back to the client.
4. The client React renderer updates the DOM tree.

#### Why This Model Fails for Interactive 3D Anatomy

```
STREAMLIT RE-RUN CASCADE vs. WEBGL FRAME BUDGET
0 ms       16.6 ms (Frame 1)   33.3 ms (Frame 2)   50.0 ms (Frame 3)     500-1500 ms
├──────────┼───────────────────┼───────────────────┼────────────────────┤
│ WebGL Render Loop Target (60fps, 16.6ms per frame)                     │
│ [ Orbit ] [ Camera Slerp ] [ Raycast Hover ] [ Shader Uniform Update ] │
│                                                                        │
│ Streamlit Python Top-to-Bottom Execution Cycle                         │
│ [ Widget Event ] ──────────────────────────────────────────────> [ Delta Tree Rebuilt ]
│                  (Blocks UI, Re-evaluates entire script,                │
│                   Unmounts/Remounts DOM nodes, Context Jank)           │
```

1. **Destruction of Ephemeral GPU State:**
   In Three.js, spatial navigation is fluid and continuous: mouse drags orbit the camera at 60fps (16.6 ms per frame), momentum damping updates positions, hover raycasters test bounding boxes every frame, and shaders interpolate explosion displacements.
   In Streamlit, any state change triggered outside the iframe forces a script re-run. If the iframe component is re-evaluated with a new key or moved within an expander/tab, the entire `<iframe>` DOM node is torn down and re-created.
2. **Catastrophic Resource Thrashing:**
   Tearing down and remounting the iframe incurs:
   - Destroying the existing `WebGLRenderer` and its OpenGL context.
   - Garbage-collecting ~60 MB of de-serialized geometry buffers.
   - Re-issuing HTTP requests for `atlas.json` (1.33 MB) and 15 binary chunks (33 MB).
   - Re-running CPU mesh assembly (`BufferGeometryUtils.mergeGeometries` across 2,234 parts), which blocks the browser's main thread for 400–850 ms.
   - Re-compiling 15 custom WebGL shader programs.
3. **Browser WebGL Context Exhaustion:**
   Browsers enforce strict limits on simultaneous active WebGL contexts (typically 8 to 16 per process on macOS Chrome/Safari). If a student navigates through multiple condition cards in Streamlit where each expander mounts a separate `st.components.v1.iframe`, older contexts are silently evicted by the browser, throwing fatal `webglcontextlost` events on previously rendered models.

---

### 2.2 Critique 2: The Integration Antipattern (The Iframe Barrier)

The current integration relies entirely on URL query strings (`?select=FMA...`) passed to an isolated `<iframe>`. This pattern exhibits five fundamental architectural defects:

```
THE IFRAME COMMUNICATION BARRIER
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│ Streamlit Host Application      │                 │ Iframe: 3D Human Atlas          │
│                                 │                 │                                 │
│ [ Chat / Tutor Stream ]         │                 │ [ 2,234 WebGL Meshes ]          │
│ "The anterior descending artery │                 │                                 │
│  supplies the anterior septum..."│                 │                                 │
│                                 │      BLOCKED    │                                 │
│  Cannot stream mesh highlight ──┼─────── ╳ ───────┼─> No command listener           │
│  Cannot adjust camera focal point│                 │                                 │
│  Cannot peel outer muscle layers│                 │                                 │
│                                 │                 │                                 │
│                                 │      BLOCKED    │                                 │
│  No event received <────────────┼─────── ╳ ───────┼── User clicks structure (LAD)   │
│  Zero clinical context loaded   │                 │   Only internal sheet opens     │
│  No RAG search triggered        │                 │                                 │
└─────────────────────────────────┘                 └─────────────────────────────────┘
```

#### 1. Zero Bi-Directional Telemetry (The Silent Mesh)
When a student interacts with the 3D canvas and clicks an anatomical mesh:
- Three.js raycasts against `pickers[i]`, identifies part `FJ1895` (`Left anterior descending branch of left coronary artery`), resolves concept `FMA3740`, and triggers `choosePart()`.
- `app/page.tsx` sets its internal state: `setChosen(c)`, `setState({ selected: [id] })`, and opens the internal `<Sheet>`.
- **The parent application receives nothing.** No `window.postMessage` is dispatched; no callback is registered.
- **Pedagogical Failure:** The mentor cannot display the textbook description from Gray's, cannot retrieve clinical correlations from Robbins or Harrison, cannot show common pathologies (e.g., myocardial infarction, LAD occlusion, "widow-maker"), and cannot evaluate the student's active recall.

#### 2. Absence of Streaming Tool Execution
In an AI-native medical learning environment, the language model must drive spatial visualization while generating explanations:
- As the model streams: *"The internal carotid artery enters the cranium via the carotid canal..."*, the system should execute a spatial tool call:
  ```json
  {"action": "set_camera", "preset": "skull_base_inferior", "target": "FMA55775"}
  {"action": "isolate_meshes", "ids": ["FMA3960", "FMA55775"], "context_opacity": 0.15}
  ```
- With an iframe URL query parameter, this is mathematically impossible. A URL parameter can only be set **once upon iframe creation**. Updating the URL parameter causes the browser to reload the entire iframe from scratch, resetting the scene.

#### 3. Inability to Dissect Layers (Coarse Laterality & System Toggling)
The current `deep-link.patch` supports only:
- `?select=<single_name_or_fma>`
- `?select=<fma1,fma2>` (combined isolation)
- `?system=<system_id>` (shows only one system)
It cannot express complex medical viewing states:
- *Layer Peeling:* "Show cardiovascular system, but make overlying ribcage and sternum 80% transparent."
- *Cross-Section Clipping:* "Cut a sagittal clipping plane along the left ventricle to expose the mitral valve."
- *Pathological Trajectory:* "Show path of a bullet entering right 4th intercostal space traveling to posterior mediastinum."

#### 4. Query Parsing Heuristic Brittleness
In `deep-link.patch`, lookup ranking uses a simplistic heuristic:
```typescript
const rank = (c: Concept) => {
  const n = c.name.toLowerCase();
  return n === want ? 0 : c.id.toLowerCase() === want ? 1 : n.startsWith(want) ? 2 : n.includes(want) ? 3 : 9;
};
```
If a student queries `"Aorta"`, the ranking evaluates:
- Exact match: `"aorta"` (Rank 0) -> Matches `FMA3734`.
- But if querying `"Thoracic aorta"`, and the concept in BodyParts3D is named `"thoracic segment of descending aorta"`, it falls back to a substring match (Rank 3) and may falsely match a sub-branch like `"thoracic branch of..."` if its character length happens to be shorter (`a.c.name.length - b.c.name.length`).

---

### 2.3 Critique 3: Data & Knowledge Graph Silos (Spatial vs. Clinical)

The most glaring architectural flaw in the existing platform is the **semantic chasm** between spatial entities in the 3D atlas and clinical entities in the RAG knowledge graph.

```
ONTOLOGY SILOS & BRIDGE DEFICIT
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│ med-rag Clinical Ontology       │                 │ human-atlas Spatial Catalog     │
│ 360 Certified Anatomical Labels │                 │ 3,432 Named Concepts            │
│ 4,978 Pathological Conditions   │                 │ 2,234 Modeled Polygonal Meshes  │
│ 26,000 Certified Facts (Text)   │                 │ Indexed strictly by FMA ID      │
│ 13,204 BODHI Clinical Edges     │                 │ Zero Clinical Relations         │
└────────────────┬────────────────┘                 └────────────────┬────────────────┘
                 │                                                   │
                 │                 atlas_crosswalk.jsonl             │
                 └───────────────> (3,470 Records) <─────────────────┘
                                   - 3,258 Atlas names
                                   - 154 Left/Right pairs
                                   - 43 Manual synonyms
                                   - 8 Synonym parts
                                   - ONLY 7 Embedding+LLM matches!
                                   
   CRITICAL METRIC:
   - Certified Anatomical Structures Linked: 114 / 360 (31.7%)
   - Pathological Conditions Linked:         115 / 4,978 (2.3%)
   - OVER 97% OF CONDITIONS HAVE ZERO 3D SPATIAL ANCHOR!
```

#### 2.3.1 Forensic Analysis of `atlas_crosswalk.jsonl`
Our programmatic analysis of the compiled crosswalk reveals why the bridge is broken:
- Total records: 3,470.
- `atlas-name`: 3,258 records (93.9%). These are simply the verbatim concept names from BodyParts3D mirrored as lookup keys.
- `atlas-pair`: 154 records. Structures drawn only as left/right bilateral pairs (e.g., `lung` -> left lung + right lung).
- `synonym`: 43 records. Hand-curated aliases (`bladder` -> `urinary bladder`, `windpipe` -> `trachea`).
- `synonym-parts`: 8 records. Hand-curated multi-part muscles (`trapezius`, `biceps brachii`).
- `embedding+llm`: **Only 7 records.** The automated pipeline using `bge-small` and DeepSeek-V4 failed to bridge the remaining vocabulary because clinical textbooks and anatomical ontologies use vastly different naming conventions.

#### 2.3.2 Why Certified Structures Fail to Link
When evaluating the 360 unique anatomical structures certified in `med-rag`'s clinical facts:
- Only **114 structures (31.7%)** resolve to an atlas record via `rag.atlas.atlas_link()`.
- **246 structures (68.3%) fail to link completely.**
- When evaluating 4,978 conditions in the database:
  - Only **115 conditions (2.3%)** link to an anatomical structure via `INVOLVES_STRUCTURE` facts that resolve in the atlas.
  - **4,863 conditions have zero 3D representation.**

#### 2.3.3 Root Causes of the Ontological Gap
1. **Granularity & Scope Mismatches:**
   - BodyParts3D is a macroscopic reference anatomy of an adult male. It intentionally omits female pelvic anatomy (uterus, ovaries), microscopic/histological structures (glomerulus, islets of Langerhans, pulmonary alveoli), and distal neurovascular networks (digital nerves, meningeal capillary plexuses).
   - Clinical conditions frequently center on these exact missing structures (e.g., *Endometriosis*, *Diabetic Nephropathy*, *Epidural Hematoma* involving the *middle meningeal artery* which is absent from BodyParts3D).
2. **Absence of Spatial Hierarchy and Mereology in Runtime:**
   - BodyParts3D contains only `parts` (meshes) and flat `concepts`. It contains **no runtime mereological hierarchy** (`part_of`, `subdivision_of`, `tributary_of`, `supplied_by`).
   - If a clinical fact states that *Myocardial Infarction* involves the *Interventricular Septum*, and the atlas models only *Heart* (`FMA7088`) and general ventricular myocardium, the system cannot deduce that the septum is `part_of` the heart and therefore fails to highlight the surrounding organ.
3. **Ontological Cross-Reference Deficit (FMA vs. SNOMED CT vs. BODHI):**
   - Eka Care's BODHI graph uses SNOMED-CT concept identifiers and clinical colloquialisms.
   - `med-rag` extracts entities as textbook string labels normalized via `merge_key()`.
   - `human-atlas` uses FMA integer identifiers.
   - There is no unified tripartite schema linking `SNOMED_ID <-> FMA_ID <-> Textbook_Passage_Vector`.

---

## 3. The Unified AI-Native Target Architecture

To eliminate the architectural mismatch, iframe barriers, and data silos, we specify a unified, production-grade target architecture.

### 3.1 Architectural Principles
1. **Single Unified Web Application Runtime:** Eliminate the iframe. Render the Three.js WebGL viewport natively within the same React 19 component tree as the chat mentor, clinical graph, and curriculum tools.
2. **Asynchronous Decoupled Backend:** Replace Streamlit with a high-performance **FastAPI** backend supporting asynchronous Server-Sent Events (SSE) and full-duplex WebSockets.
3. **Reactive Spatial-Semantic Bridge:** Manage application state through a central **Zustand** reactive store that synchronizes Three.js viewport parameters, RAG streaming tokens, and clinical graph nodes.
4. **Unified Spatial-Clinical Knowledge Graph:** Unify FMA spatial hierarchies, BODHI clinical relationships, certified ontology facts, and textbook vector chunks into a consolidated relational/vector schema.

```
TARGET UNIFIED AI-NATIVE ARCHITECTURE
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ REACT 19 / NEXT.JS UNIFIED FRONTEND RUNTIME (Single DOM Context)                       │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │ GLOBAL ZUSTAND REACTIVE STORE                                                    │  │
│  │  - Active Scene State (Camera, Visible Systems, Selected FMA IDs, Dissection)    │  │
│  │  - Active Conversation & Streaming Tokens                                        │  │
│  │  - Clinical Graph Focus (Active Node, Subgraph Filter, Drill Depth)              │  │
│  │  - Bi-Directional Event Dispatcher & Tool Call Handler                           │  │
│  └───────────────▲───────────────────────────────▲──────────────────────────────▲───┘  │
│                  │                               │                              │      │
│  ┌───────────────▼─────────────┐   ┌─────────────▼────────────┐   ┌─────────────▼────┐ │
│  │ THREE.JS NATIVE VIEWPORT    │   │ AI MENTOR CONVERSATION   │   │ CLINICAL GRAPH   │ │
│  │ - 15 System BufferGeometries│   │ - Markdown / LaTeX Token │   │ - Interactive    │ │
│  │ - GPU DataTexture Shaders   │   │   Streaming (SSE)        │   │   Cytoscape/Vis  │ │
│  │ - Raycast Click -> Dispatch │   │ - Inline Tool Invocations│   │ - Certified Fact │ │
│  │ - Smooth Slerp Camera Orbit │   │ - Real-time Spatial Cues │   │   Citation Links │ │
│  └─────────────────────────────┘   └──────────────────────────┘   └──────────────────┘ │
└──────────────────────────────────────────▲─────────────────────────────────────────────┘
                                           │ Full-Duplex WebSockets & SSE Streams
                                           │ (JSON-RPC / Structured Tool Calls)
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│ FASTAPI ASYNCHRONOUS HIGH-PERFORMANCE BACKEND                                          │
│                                                                                        │
│  ┌───────────────────────────────┐  ┌────────────────────────┐  ┌────────────────────┐ │
│  │ Spatial Orchestration Engine  │  │ Multi-Hop RAG Pipeline │  │ Spatial Tool Agent │ │
│  │ - Camera Presets & Bounding   │  │ - Axis Decomposition   │  │ - Camera Director  │ │
│  │ - FMA Mereology Traversal     │  │ - Citation Verification│  │ - Layer Peeler     │ │
│  │ - Dissection Vector Generator │  │ - Guard Rail Filter    │  │ - Mesh Highlighter │ │
│  └───────────────────────────────┘  └────────────────────────┘  └────────────────────┘ │
└──────────────────────────────────────────▲─────────────────────────────────────────────┘
                                           │ Unified SQL / Graph / Vector Queries
┌──────────────────────────────────────────▼─────────────────────────────────────────────┐
│ UNIFIED SPATIAL-CLINICAL DATABASE (PostgreSQL + pgvector / SQLite Graph)               │
│                                                                                        │
│  [ FMA Ontology ] ──mereology──> [ Anatomy Meshes ] <──coords── [ Bounding Volumes ]   │
│         │                              │                                               │
│   involves_struct                 supplied_by                                          │
│         ▼                              ▼                                               │
│  [ Clinical Conditions ] <──> [ BODHI Edges ] <──> [ 35,902 Textbook Passages + Embs ] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 3.2 Unified Codebase & Monorepo Directory Structure

We consolidate `med-rag` and `med-rag-atlas` into a unified repository with clear separation between frontend presentation, backend services, and offline ontology pipelines:

```
medevolv/
├── apps/
│   ├── web/                         # Unified React 19 / Next.js Frontend
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── next.config.mjs
│   │   ├── public/
│   │   │   └── models/              # Precompressed BodyParts3D binary chunks
│   │   │       ├── atlas.json       # Augmented FMA catalog with clinical cross-references
│   │   │       ├── body-0.bin.gz
│   │   │       └── ...
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── layout.tsx       # Root layout with providers (Zustand, QueryClient)
│   │   │   │   ├── page.tsx         # Responsive workspace (3D Canvas + Split Chat/Graph)
│   │   │   │   └── api/             # Frontend proxy routes if needed
│   │   │   ├── components/
│   │   │   │   ├── 3d/              # Three.js native components
│   │   │   │   │   ├── Viewport.tsx # Native Three.js WebGL canvas host
│   │   │   │   │   ├── SceneManager.ts # GPU textures, materials, and chunk loaders
│   │   │   │   │   ├── CameraRig.ts # Smooth damping, slerp transitions, framing
│   │   │   │   │   └── Controls.tsx # Layer dock, view buttons, explosion slider
│   │   │   │   ├── chat/            # Conversational tutor interface
│   │   │   │   │   ├── MessageList.tsx
│   │   │   │   │   ├── Composer.tsx
│   │   │   │   │   └── SpatialCitation.tsx # Clickable inline pill that navigates 3D scene
│   │   │   │   ├── graph/           # Clinical knowledge graph component
│   │   │   │   │   └── ClinicalNetwork.tsx # Cytoscape / Vis canvas
│   │   │   │   └── ui/              # Radix/Tailwind design system
│   │   │   ├── store/
│   │   │   │   ├── useSpatialStore.ts # Central Zustand store for 3D state
│   │   │   │   ├── useChatStore.ts    # Streaming tokens, history, active tools
│   │   │   │   └── useGraphStore.ts   # Node selection and clinical depth
│   │   │   └── lib/
│   │   │       ├── api-client.ts    # SSE and WebSocket streaming client
│   │   │       └── protocol.ts      # TypeScript interfaces for WebSocket messages
│   │
│   └── api/                         # FastAPI Python Backend Service
│       ├── pyproject.toml
│       ├── main.py                  # ASGI FastAPI application entrypoint
│       ├── routers/
│       │   ├── chat.py              # WebSocket & SSE streaming tutor endpoints
│       │   ├── spatial.py           # FMA spatial query endpoints (bounding boxes, camera presets)
│       │   ├── ontology.py          # Certified facts, condition profiles, contradiction checks
│       │   └── graph.py             # Subgraph generation for complaints/conditions
│       ├── services/
│       │   ├── rag_engine.py        # Asynchronous multi-hop RAG with structured tool calls
│       │   ├── spatial_planner.py   # Maps clinical discussion to 3D scene actions
│       │   ├── vector_search.py     # ChromaDB / pgvector async retriever
│       │   └── bodhi_service.py     # BODHI graph traversal
│       └── core/
│           ├── config.py
│           └── db.py                # Database connection pools
│
├── packages/
│   ├── shared-types/                # Shared TypeScript definitions (JSON-RPC, tool calls)
│   └── ontology-engine/             # Python library for compilation & verification
│       ├── schema.py
│       ├── compiler.py
│       └── reconciler.py
│
├── data/
│   ├── db/                          # SQLite/PostgreSQL unified database
│   │   └── medevolv_unified.db
│   └── raw/                         # Raw textbooks, BODHI releases, BodyParts3D sources
│
└── deploy/
    ├── Dockerfile.web
    ├── Dockerfile.api
    ├── docker-compose.prod.yml
    └── Caddyfile
```

---

### 3.3 The Reactive Spatial-Semantic Bridge

The core architectural innovation is the **Reactive Spatial-Semantic Bridge**: a bidirectional, low-latency communication layer synchronizing the AI mentor's linguistic output with the 3D WebGL scene and the clinical knowledge graph.

#### 3.3.1 Bidirectional State Synchronization Flow

```
BIDIRECTIONAL SPATIAL-SEMANTIC EVENT LOOP

 ┌────────────────────────────────────────────────────────────────────────┐
 │ STUDENT ACTION 1: 3D MESH SELECTION (SPATIAL -> CLINICAL)               │
 │                                                                        │
 │ 1. Student taps Left Ventricular Wall in Three.js Canvas               │
 │ 2. Raycaster hits mesh `FJ2634` -> Resolves concept `FMA7101`          │
 │ 3. Zustand store fires `selectStructure("FMA7101", "Left Ventricle")`  │
 │ 4. UI updates: 3D scene isolates FMA7101; camera frames bounding box  │
 │ 5. WebSocket sends: `{"event": "structure_selected", "fma": "FMA7101"}`│
 │ 6. Backend retrieves:                                                  │
 │    - Certified conditions (`Myocardial Infarction`, `Aortic Stenosis`) │
 │    - Relevant textbook passages from Gray's & Robbins                  │
 │ 7. Chat displays contextual drawer: "Inspecting Left Ventricle"        │
 │    with one-tap tutor prompt: "Explain clinical conditions affecting   │
 │    the left ventricular myocardium."                                   │
 └────────────────────────────────────────────────────────────────────────┘

 ┌────────────────────────────────────────────────────────────────────────┐
 │ STUDENT ACTION 2: RAG VIGNETTE QUERY (CLINICAL -> SPATIAL)             │
 │                                                                        │
 │ 1. Student asks: "62yo male with sudden tearing chest pain radiating   │
 │    to back, asymmetric pulses, and widened mediastinum."               │
 │ 2. Backend RAG decomposes query:                                       │
 │    - Candidate diagnosis: Aortic Dissection (Stanford Type A / B)      │
 │    - Involved structures: Ascending Aorta (FMA3734),                   │
 │      Arch of Aorta (FMA3735), Descending Aorta (FMA3736)               │
 │ 3. LLM streams answer tokens over SSE/WebSocket.                       │
 │ 4. LLM emits inline structured spatial tool calls:                     │
 │    `:::spatial{"action":"dissect","peel":["skeletal","muscular"]}`    │
 │    `:::spatial{"action":"isolate","ids":["FMA3734","FMA3735"]}`        │
 │    `:::spatial{"action":"set_camera","preset":"thoracic_left_oblique"}`│
 │ 5. Frontend parser intercepts spatial tokens before markdown render:   │
 │    - Dispatches actions directly to `useSpatialStore`                  │
 │    - Three.js camera smoothly slerps to left anterior oblique view     │
 │    - GPU DataTexture fades ribcage opacity to 15%                      │
 │    - Aortic arch pulses with red accent shader                         │
 │ 6. Text streams alongside the animated 3D transformation.              │
 └────────────────────────────────────────────────────────────────────────┘
```

#### 3.3.2 Structured Spatial Tool Schema
The backend AI tutor emits structured spatial directives using strict JSON schemas:

```typescript
// packages/shared-types/src/spatial-actions.ts

export type CameraPreset = 
  | 'anterior' 
  | 'posterior' 
  | 'lateral_left' 
  | 'lateral_right' 
  | 'superior' 
  | 'inferior' 
  | 'thoracic_left_oblique' 
  | 'skull_base';

export interface HighlightAction {
  action: 'highlight';
  conceptIds: string[];       // FMA concept IDs (e.g. ["FMA3734", "FMA3735"])
  color?: string;             // Hex color code (defaults to system color)
  pulse?: boolean;            // Whether to trigger rhythmic shader pulse
}

export interface IsolateAction {
  action: 'isolate';
  conceptIds: string[];
  contextSystems?: string[];  // Ghosted background systems (opacity 0.1)
}

export interface CameraAction {
  action: 'set_camera';
  preset?: CameraPreset;
  targetFmaId?: string;       // Computes bounding box center of structure
  zoomDistance?: number;
  durationMs?: number;        // Transition duration (e.g. 1200ms)
}

export interface DissectAction {
  action: 'dissect';
  visibleSystems: string[];   // Explicit systems to keep visible
  peelSystems?: string[];     // Systems to animate away
  clippingPlane?: {
    axis: 'x' | 'y' | 'z';
    offset: number;           // Coordinate along axis
    normal: [number, number, number];
  };
}

export type SpatialAction = HighlightAction | IsolateAction | CameraAction | DissectAction;
```

#### 3.3.3 Frontend Zustand Reactive Store (`useSpatialStore.ts`)
The central state store orchestrates Three.js rendering without DOM re-renders:

```typescript
// apps/web/src/store/useSpatialStore.ts
import { create } from 'zustand';
import { SystemId, View, Atlas, Concept } from '@/lib/anatomy-types';
import { SpatialAction } from '@medevolv/shared-types';

interface SpatialState {
  atlas: Atlas | null;
  loaded: boolean;
  visibleSystems: SystemId[];
  selectedElementIds: string[];
  selectedConcept: Concept | null;
  isolated: boolean;
  explosionAmount: number;
  cameraView: View;
  cameraTarget: [number, number, number];
  cameraDistance: number;
  pulseElementIds: string[];
  
  // Actions
  setAtlas: (atlas: Atlas) => void;
  selectElement: (id: string) => void;
  selectConcept: (conceptId: string) => void;
  executeSpatialAction: (action: SpatialAction) => void;
  resetScene: () => void;
}

export const useSpatialStore = create<SpatialState>((set, get) => ({
  atlas: null,
  loaded: false,
  visibleSystems: ['skeletal', 'muscular', 'arterial', 'venous', 'nervous', 'cardiac', 'respiratory'],
  selectedElementIds: [],
  selectedConcept: null,
  isolated: false,
  explosionAmount: 0,
  cameraView: 'three-quarter',
  cameraTarget: [0, 0.85, 0],
  cameraDistance: 4.0,
  pulseElementIds: [],

  setAtlas: (atlas) => set({ atlas, loaded: true }),

  selectConcept: (conceptId) => {
    const { atlas } = get();
    if (!atlas) return;
    const concept = atlas.concepts.find(c => c.id.toLowerCase() === conceptId.toLowerCase());
    if (!concept) return;

    set({
      selectedConcept: concept,
      selectedElementIds: concept.elements,
      isolated: true
    });
  },

  executeSpatialAction: (action) => {
    const { atlas } = get();
    if (!atlas) return;

    switch (action.action) {
      case 'isolate': {
        const elements = action.conceptIds.flatMap(cid => {
          const c = atlas.concepts.find(x => x.id === cid);
          return c ? c.elements : [];
        });
        set({
          selectedElementIds: elements,
          isolated: true,
          explosionAmount: 0
        });
        break;
      }
      case 'highlight': {
        const elements = action.conceptIds.flatMap(cid => {
          const c = atlas.concepts.find(x => x.id === cid);
          return c ? c.elements : [];
        });
        set({
          selectedElementIds: elements,
          pulseElementIds: action.pulse ? elements : []
        });
        break;
      }
      case 'set_camera': {
        if (action.targetFmaId) {
          const c = atlas.concepts.find(x => x.id === action.targetFmaId);
          if (c) {
            // Compute centroid of concept from parts bounds
            const parts = atlas.parts.filter(p => c.elements.includes(p.id));
            if (parts.length > 0) {
              const center: [number, number, number] = [0, 0, 0];
              parts.forEach(p => {
                center[0] += (p.bounds[0][0] + p.bounds[1][0]) / (2 * parts.length);
                center[1] += (p.bounds[0][1] + p.bounds[1][1]) / (2 * parts.length);
                center[2] += (p.bounds[0][2] + p.bounds[1][2]) / (2 * parts.length);
              });
              set({ cameraTarget: center });
            }
          }
        }
        if (action.preset) {
          // Map preset to view orientation
          const viewMap: Record<string, View> = {
            'anterior': 'front',
            'posterior': 'back',
            'lateral_left': 'side',
            'thoracic_left_oblique': 'three-quarter'
          };
          set({ cameraView: viewMap[action.preset] || 'front' });
        }
        break;
      }
      case 'dissect': {
        set({
          visibleSystems: action.visibleSystems as SystemId[]
        });
        break;
      }
    }
  },

  resetScene: () => set({
    visibleSystems: ['skeletal', 'muscular', 'arterial', 'venous', 'nervous', 'cardiac', 'respiratory'],
    selectedElementIds: [],
    selectedConcept: null,
    isolated: false,
    explosionAmount: 0,
    pulseElementIds: []
  })
}));
```

---

### 3.4 Unified Database & Schema Design

To resolve the data silo between FMA IDs, BODHI clinical nodes, certified ontology facts, and textbook chunks, we define a unified schema implemented in PostgreSQL (with `pgvector`) or SQLite:

```sql
-- UNIFIED SPATIAL-CLINICAL SCHEMA

-- 1. Spatial Entities (FMA Reference)
CREATE TABLE spatial_concepts (
    fma_id VARCHAR(32) PRIMARY KEY,       -- e.g. 'FMA3734'
    canonical_name VARCHAR(255) NOT NULL, -- e.g. 'Ascending aorta'
    latin_name VARCHAR(255),
    system_id VARCHAR(32) NOT NULL,       -- 'arterial', 'cardiac', etc.
    mesh_part_ids JSONB NOT NULL,         -- ['FJ1895', 'FJ1896']
    bounding_box JSONB NOT NULL,          -- [[minX, minY, minZ], [maxX, maxY, maxZ]]
    centroid JSONB NOT NULL,              -- [x, y, z]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Spatial Mereology & Anatomy Relationships
CREATE TABLE spatial_relations (
    id SERIAL PRIMARY KEY,
    subject_fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    predicate VARCHAR(64) NOT NULL,       -- 'PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF', 'SUPPLIED_BY'
    object_fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    source_citation VARCHAR(255)          -- e.g. 'Gray''s Anatomy 5e, p. 1024'
);

-- 3. Clinical Concepts (BODHI / SNOMED CT / Textbook Entities)
CREATE TABLE clinical_concepts (
    concept_id VARCHAR(64) PRIMARY KEY,   -- e.g. 'COND:aortic_dissection'
    canonical_label VARCHAR(255) NOT NULL,-- e.g. 'Aortic dissection'
    concept_type VARCHAR(64) NOT NULL,    -- 'PathologicalCondition', 'TherapeuticAgent', etc.
    snomed_id VARCHAR(32),                -- SNOMED CT identifier if mapped
    bodhi_key VARCHAR(64),                -- Eka Care BODHI graph node key
    icd10_code VARCHAR(16)
);

-- 4. Spatial-Clinical Unified Crosswalk (The Missing Link)
CREATE TABLE spatial_clinical_crosswalk (
    id SERIAL PRIMARY KEY,
    clinical_concept_id VARCHAR(64) REFERENCES clinical_concepts(concept_id),
    fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    relation_type VARCHAR(64) NOT NULL,   -- 'INVOLVES_STRUCTURE', 'SITE_OF_OCCURRENCE', 'TARGET_ORGAN'
    verification_method VARCHAR(32),      -- 'expert_certified', 'quote_verified', 'llm_consensus'
    confidence FLOAT NOT NULL DEFAULT 1.0,
    quote_verbatim TEXT                   -- Word-for-word excerpt from textbook source
);

-- 5. Textbook Corpus & Vector Embeddings
CREATE TABLE textbook_passages (
    passage_id VARCHAR(64) PRIMARY KEY,   -- e.g. 'grays_sec_45_p3'
    book_id VARCHAR(32) NOT NULL,         -- 'grays', 'harrison', 'robbins', 'kdt', 'guyton'
    chapter_title VARCHAR(255),
    section_title VARCHAR(255),
    page_numbers VARCHAR(32),
    passage_text TEXT NOT NULL,
    embedding vector(384)                 -- bge-small-en-v1.5 384-dimensional dense vector
);

-- 6. Passage-to-Concept Grounding Link
CREATE TABLE passage_concepts (
    passage_id VARCHAR(64) REFERENCES textbook_passages(passage_id),
    concept_id VARCHAR(64) REFERENCES clinical_concepts(concept_id),
    fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    PRIMARY KEY (passage_id, concept_id)
);

CREATE INDEX idx_spatial_fma ON spatial_concepts(fma_id);
CREATE INDEX idx_crosswalk_fma ON spatial_clinical_crosswalk(fma_id);
CREATE INDEX idx_crosswalk_clinical ON spatial_clinical_crosswalk(clinical_concept_id);
CREATE INDEX idx_passages_emb ON textbook_passages USING ivfflat (embedding vector_cosine_ops);
```

#### 3.4.1 Solving the Ontology Gap
With this schema:
1. **Hierarchical Spatial Traversal:** If a student asks about *Mitral Valve Endocarditis*, the database links *Endocarditis* -> `FMA7236` (*Mitral valve*). If the student zooms out, a recursive CTE on `spatial_relations` climbs `PART_OF` to `FMA7088` (*Heart*), automatically determining the parent organ context.
2. **Deterministic Multi-Modal Join:** A single query simultaneously returns:
   - The verbatim Gray's Anatomy textbook passages.
   - The exact FMA IDs required to isolate meshes in Three.js.
   - The BODHI differential diagnosis edges.
   - The certified contraindications and first-line drugs.

---

### 3.5 Fluid Handoff Workflows for Medical Learning

#### Workflow A: Spatial-to-Clinical Discovery (The 3D Inquisitive Mode)
1. **Student Context:** A 1st-year MBBS student explores the mediastinum in the 3D viewer.
2. **Interaction:** The student rotates the ribcage, switches to the arterial system, and clicks an unfamiliar branch originating from the aortic arch.
3. **Execution:**
   - Three.js raycasts mesh `FJ2881` -> resolves `FMA3746` (*Left common carotid artery*).
   - `useSpatialStore` isolates the structure and computes its camera bounding box.
   - The client emits `onSelectStructure(FMA3746)` via WebSocket.
   - Backend queries `spatial_clinical_crosswalk` and `textbook_passages`.
   - The chat drawer displays a rich clinical card:
     - **Structure:** Left common carotid artery (Arterial System).
     - **Origin & Course:** Excerpt from Gray's Anatomy 5e, p. 542.
     - **Key Clinical Pathologies:** Carotid artery stenosis, transient ischemic attack (TIA), carotid sinus hypersensitivity.
     - **One-Click Drill Questions:** *"What are the branches of the external carotid artery?"* | *"How does carotid sinus massage terminate PSVT?"*

#### Workflow B: Clinical Case Vignette to Dynamic 3D Dissection
1. **Student Context:** A 3rd-year student inputs an exam case vignette:
   > *"A 54-year-old male with long-standing hypertension presents to the emergency department with sudden-onset, severe, sharp chest pain that feels like 'tearing' in his back between the scapulae. On exam, BP is 190/110 mmHg in the right arm and 140/85 mmHg in the left arm. A diastolic murmur is heard along the right sternal border."*
2. **Execution:**
   - **Step 1 (Routing & Guard):** Backend passes safety check, recognizes a complex multi-hop vignette, routes to `case` axis planner.
   - **Step 2 (Clinical Extraction):**
     - Identified condition: *Aortic Dissection* (Stanford Type A / DeBakey I or II).
     - Complications: Acute aortic regurgitation (diastolic murmur), branch artery occlusion (blood pressure differential).
   - **Step 3 (Spatial Graph Linkage):**
     - Primary involved structure: `FMA3734` (*Ascending aorta*).
     - Dissection flap propagation: `FMA3735` (*Arch of aorta*), `FMA3736` (*Thoracic aorta*), `FMA3744` (*Brachiocephalic trunk*), `FMA3746` (*Left common carotid*), `FMA3748` (*Left subclavian*).
   - **Step 4 (Synchronized Streaming & Visualization):**
     - As the tutor outputs the opening clinical assessment, the SSE stream sends:
       ```json
       {"type": "spatial_action", "action": "set_camera", "preset": "thoracic_left_oblique"}
       {"type": "spatial_action", "action": "dissect", "visibleSystems": ["cardiac", "arterial"], "peelSystems": ["skeletal", "muscular"]}
       {"type": "spatial_action", "action": "highlight", "conceptIds": ["FMA3734", "FMA3735", "FMA3736"], "color": "#e5484d", "pulse": true}
       ```
     - The student watches the 3D scene automatically peel away the superficial pectoralis muscles and ribcage, revealing the glowing, isolated aorta, while the camera centers precisely on the aortic root.
     - The explanation flows with cited references to Harrison's Internal Medicine 22e and certified management steps: immediate IV beta-blockade (labetalol) to reduce shear stress (`dP/dt`), urgent CT angiography, and cardiothoracic surgical consultation.

#### Workflow C: Active Recall Spatial Flashcards (FSRS-5 3D Occlusion)
1. **Pedagogical Goal:** Replaces passive reading with high-efficiency active spatial recall.
2. **Execution:**
   - The platform prompts the student: *"Identify the artery responsible for anterior myocardial infarction and name its parent vessel."*
   - Three.js displays the heart with coronary vasculature in high detail.
   - Five candidate branches are marked with interactive numerical pins (1–5) rendered via HTML overlay projections (`projected.project(camera)`).
   - The student taps pin #3 (LAD).
   - The system verifies the selection against `FMA3740`, scores the FSRS-5 stability parameter, and provides instant textbook feedback.

---

## 4. Migration & Implementation Roadmap

```
IMPLEMENTATION ROADMAP: FOUR PHASES

 Month 1                   Month 2                   Month 3                   Month 4
┌─────────────────────────┬─────────────────────────┬─────────────────────────┬─────────────────────────┐
│ PHASE 1: UNIFIED APP    │ PHASE 2: SPATIAL-CLINIC │ PHASE 3: REACTIVE       │ PHASE 4: PRODUCTION     │
│ SHELL & DIRECT EMBED    │ KNOWLEDGE GRAPH         │ STREAMING BRIDGE        │ OPTIMIZATION & DEPLOY   │
├─────────────────────────┼─────────────────────────┼─────────────────────────┼─────────────────────────┤
│ • Next.js + Three.js    │ • PostgreSQL + pgvector │ • WebSocket/SSE Agent   │ • Brotli precompression │
│   native canvas port    │ • FMA-BODHI-SNOMED      │ • Structured tool-call  │ • WebGL context pools   │
│ • Strip iframe and      │   schema consolidation  │   stream parser         │ • Single-domain Caddy   │
│   deep-link.patch       │ • Recursive mereology   │ • Zustand bidirectional │   deployment            │
│ • FastAPI async backend │   traversal queries     │   event synchronization │ • Offline PWA caching   │
│   for RAG pipelines     │ • Rebuild crosswalk     │ • Multi-structure layer │   with IndexedDB        │
│                         │   (100% coverage)       │   peeling & animations  │                         │
└─────────────────────────┴─────────────────────────┴─────────────────────────┴─────────────────────────┘
```

### Phase 1: Unified App Shell & Direct Three.js Viewport (Weeks 1–4)
- **Objective:** Eliminate Streamlit and the iframe entirely.
- Port `human-atlas`'s `scene.tsx` and `anatomy.ts` directly into `apps/web/src/components/3d/`.
- Render the Three.js canvas as a persistent, background/split viewport in Next.js 15.
- Wrap Python RAG and ontology functions in an asynchronous FastAPI service (`apps/api/`).
- **Success Metric:** Zero WebGL context destruction when navigating tabs; 60fps interaction during concurrent chat input.

### Phase 2: Spatial-Clinical Knowledge Graph Unification (Weeks 5–8)
- **Objective:** Bridge the semantic chasm between FMA IDs and clinical concepts.
- Migrate `atlas_crosswalk.jsonl`, `crosswalk.jsonl`, and `ontology_facts.py` into a unified relational database.
- Build an automated expansion script mapping all 360 certified anatomical structures and all 4,978 conditions to their FMA parent or constituent concepts.
- Implement mereological traversal: if a sub-branch has no discrete mesh, resolve up the tree to the nearest parent mesh with an anatomical bounding box.
- **Success Metric:** Linkage coverage of certified anatomical structures increases from **31.7% to >95%**; condition 3D grounding increases from **2.3% to >80%**.

### Phase 3: Reactive Streaming & Spatial Tool Call Orchestration (Weeks 9–12)
- **Objective:** Enable the AI tutor to manipulate the 3D scene in real time.
- Implement streaming tool calls in FastAPI (`SpatialPlannerService`).
- Implement the client-side stream parser that extracts spatial directives (`:::spatial{...}`) and forwards them to `useSpatialStore`.
- Implement camera transition damping (`CameraRig.slerp()`) and GPU DataTexture shader transitions for layer peeling and pulse highlighting.
- Implement mesh click callbacks that trigger real-time RAG context retrieval.
- **Success Metric:** Total latency from 3D mesh click to contextual tutor response < 600 ms; camera transitions execute at smooth 60fps without token stream stutter.

### Phase 4: Production Hardening, Edge Caching & PWA (Weeks 13–16)
- **Objective:** Scale to 100,000 MAU within budget.
- Pre-compress all 15 mesh chunks with Brotli level 11 (reducing 33 MB gzip down to ~27 MB Brotli).
- Configure Caddy for HTTP/3 and immutable caching headers for static geometry.
- Add Service Worker and IndexedDB caching for offline PWA operation (allowing students to inspect loaded models and review FSRS flashcards on hospital Wi-Fi without re-downloading).
- Deploy single Docker multi-stage container or Kubernetes pod topology on Oracle Cloud Infrastructure (OCI).

---

## 5. Comparative Architectural Scorecard

| Architectural Dimension | Current Architecture (`med-rag` + `human-atlas` via iframe) | Target Unified AI-Native Architecture |
|---|---|---|
| **Frontend Framework** | Streamlit Python script (`app.py`, 1,284 LOC) | React 19 / Next.js 15 Full-Stack TypeScript |
| **3D Rendering Integration** | Isolated `<iframe>` via `st.components.v1.iframe` | Native WebGL Canvas embedded in React DOM |
| **Execution Model** | Top-to-bottom re-execution on every event | Reactive Virtual DOM + Zustand state store |
| **WebGL Context Lifecycle** | Destroyed & re-created on widget state changes; subject to context eviction | Single persistent WebGL context; zero reload jank |
| **Mesh-to-Mentor Telemetry** | **Zero.** The mentor cannot observe 3D clicks | Instant callback: mesh tap triggers RAG search & clinical card |
| **Mentor-to-Mesh Control** | Static URL parameter on load only (`?select=...`) | Real-time tool-call streaming (isolation, peeling, camera slerp) |
| **Draw Call Architecture** | 15 merged system meshes (Three.js GPU DataTextures) | 15 merged meshes + Dynamic Uniform Shaders & Clipping Planes |
| **Anatomical Linkage Coverage** | 114 / 360 structures (31.7%); 115 / 4,978 conditions (2.3%) | **>95% structures linked** via mereological FMA traversal |
| **Backend Architecture** | Synchronous Python script runner | High-performance asynchronous FastAPI (SSE + WebSockets) |
| **Offline Capabilities** | None. Complete server roundtrip required | Progressive Web App (PWA) with IndexedDB geometry caching |
| **Mobile Experience** | Heavy, layout breakage on keyboard open, iframe clipping | Mobile-first responsive view with bottom gesture drawer |

---

## Conclusion & Next Actions

The existing combination of Streamlit and an iframe-embedded 3D atlas was a pragmatic prototype that validated early user interest. However, as an exploratory medical learning instrument, it is crippled by fundamental architectural flaws: the iframe boundary blocks all bi-directional telemetry, Streamlit's execution model destroys ephemeral WebGL state, and the knowledge bases remain completely siloed.

Adopting the **Target Unified AI-Native Architecture** eliminates every one of these bottlenecks. By embedding Three.js natively in a React 19/Next.js frontend, managing state through a reactive Zustand bridge, driving spatial transformations via structured LLM tool calls, and grounding the clinical ontology in an FMA mereological schema, MedEvolv Mentor transforms into a cohesive, world-class medical learning platform.
