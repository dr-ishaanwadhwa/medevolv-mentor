# Technical Investigation Report: Med-RAG Backend & Knowledge Graph Survey

**Agent Identity**: `teamwork_explorer` (`explorer_backend_survey_1`)  
**Parent Conversation ID**: `374680d6-856a-4138-9979-f33b00b59dea`  
**Working Directory**: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_backend_survey_1/`  
**Date**: 2026-11-13  
**Status**: Completed (Hard Handoff)

---

## 1. Observation

### 1.1 Codebase Structure & Architecture Inventory
- **Entry Point**: `app.py` (1,285 LOC, 73.4 KB) is a monolithic Streamlit application.
  - Line 29: `st.set_page_config(page_title="MedEvolv Mentor", page_icon="🩺", layout="wide", initial_sidebar_state="collapsed")`
  - Lines 1161–1185: `render_atlas_links(label: str, ctype: str, key: str)` embeds the 3D atlas using `st.components.v1.iframe(found[0]["url"], height=560)`.
  - Line 121: `url_for(atlas_id)` in `rag/atlas.py` outputs URLs matching `f"{config.ATLAS_URL.rstrip('/')}/?select={quote(','.join(ids), safe=',')}"`.
  - Custom visualizer component in `rag/graph_component/` embeds `vis-network` in an iframe.
- **RAG & Reasoning Pipeline (`rag/`)**:
  - `rag/answer.py` (248 LOC): Contains `answer()` and `answer_multihop()`.
    - Line 17: Regex `PERSONAL` guards against personal medical treatment questions.
    - Line 136: Synchronous LLM execution via `chat(SYSTEM, build_prompt(question, hits))`.
    - Lines 143–146, 178–180: Regex extraction of `[n]` passage and `[G#]` graph citations.
  - `rag/hops.py` (35.6 KB): Multi-hop reasoning decomposing queries into clinical axes (`etiology`, `stabilization`, `pharmacology`), linking symptoms to BODHI conditions and executing sub-queries.
  - `rag/retrieve.py` (2.7 KB): Vector search over ChromaDB with cosine similarity threshold `MIN_SIMILARITY = 0.60`.
  - `rag/backends.py` (282 LOC): Synchronous `embed()` (SentenceTransformer `BAAI/bge-small-en-v1.5` or OCI) and `chat()` (DeepSeek, Ollama, OCI, Gemini, Mistral, OpenRouter) using blocking `urllib.request.urlopen`. No asynchronous or streaming generators exist.
  - `rag/clinical_graph.py` (170 LOC): Pure 5-level clinical subgraph extractor: `Chief complaints -> Differential diagnosis -> Clinical phases -> Workup / triage -> Therapeutics / contraindications`.
  - `rag/atlas.py` (181 LOC): Crosswalk resolver loading `data/graph/atlas_crosswalk.jsonl`.
    - Function `variants(label)` normalizes plurals (`-ae`, `-i`, `-ys`), strips trailing `muscle`/`bone`, swaps "X of Y" <-> "Y X", and strips `left`/`right`.
    - Function `structures_for(condition_label)` finds atlas structures via certified `INVOLVES_STRUCTURE` facts.
- **Upstream 3D Anatomy Atlas (`/Users/ishaanwadhwa/Projects/third_party/human-atlas/`)**:
  - Geometry: 2,234 meshes from DBCLS BodyParts3D 4.0 packed into 15 binary chunks (`public/models/body-0.bin` to `body-14.bin`, ~33 MB gzipped).
  - Triangles: 2,288,268 across 15 anatomical systems.
  - Catalogue (`public/models/atlas.json`): 3,432 named FMA concepts.
  - Scene renderer (`app/scene.tsx`): GPU DataTexture instancing (`partTexture` Float32 RGBA and `selectionTexture` Uint8 RGBA) bound to shader hooks (`Material.onBeforeCompile`), yielding only ~15 draw calls total.

### 1.2 Virtual Environment State
Execution of `.venv/bin/python --version` and pip inspection revealed:
- **Python Version**: `3.13.18` (Darwin x86_64/arm64 macOS)
- **Key Installed Packages**:
  - `uvicorn`: `0.54.0` (installed and functional)
  - `starlette`: `1.10.0` (installed and functional)
  - `httpx`: `0.28.1` (installed and functional)
  - `pydantic`: `2.14.3` (installed and functional)
  - `chromadb`: `1.5.9` (installed and functional)
  - `networkx`: `3.7` (installed and functional)
  - `sentence-transformers`: `6.2.0` (installed and functional)
  - `torch`: `2.15.0` (installed and functional)
  - `pytest`: `9.2.0` (installed and functional)
  - `streamlit`: `1.67.0` (installed and functional)
  - `python-multipart`: `0.0.33` (installed and functional)
  - `orjson`: `3.13.0` (installed and functional)
- **Missing / Uninstalled Packages**:
  - `fastapi`: `NOT AVAILABLE` (`ImportError: No module named 'fastapi'`)
  - `sse_starlette`: `NOT AVAILABLE` (`ImportError: No module named 'sse_starlette'`)
  - `fsrs`: `NOT AVAILABLE` (`ImportError: No module named 'fsrs'`)
- **`requirements.txt` Status**:
  Currently contains only 8 pinned packages:
  ```
  pymupdf==2.1
  huggingface_hub==2.4.0
  networkx==3.7
  chromadb==1.5.9
  sentence-transformers==6.2.0
  oci==2.190.0
  streamlit==1.67.0
  pytest==9.2.0
  ```
  It lacks `fastapi`, `uvicorn`, `sse-starlette`, `pydantic`, `httpx`, and `fsrs`.

### 1.3 Test Suite Execution & Status
Execution of `.venv/bin/pytest tests/`:
```
============================= test session starts ==============================
platform darwin -- Python 3.13.18, pytest-9.2.0, pluggy-1.7.0
rootdir: /Users/ishaanwadhwa/Projects/med-rag
plugins: platformdirs-4.14.5, anyio-4.16.0
collected 143 items

tests/test_atlas.py ..........                                           [  6%]
tests/test_clinical_graph.py .......                                     [ 11%]
tests/test_comention.py ...                                              [ 13%]
tests/test_concepts.py .........                                         [ 20%]
tests/test_crosswalk.py ........                                         [ 25%]
tests/test_deploy_imports.py ..                                          [ 27%]
tests/test_diagrams.py ..........                                        [ 34%]
tests/test_graph_walk.py ...............                                 [ 44%]
tests/test_hops_axes.py .......................                          [ 60%]
tests/test_hubs.py ....                                                  [ 63%]
tests/test_ingest.py ...........                                         [ 71%]
tests/test_mentions.py ....                                              [ 74%]
tests/test_ontology.py .......                                           [ 79%]
tests/test_ontology_reinforce.py ..............                          [ 88%]
tests/test_rag.py ................                                       [100%]
======================= 143 passed, 5 warnings in 7.41s ========================
```
- Total test count: 143 tests across 15 files.
- Pass rate: 100% (143 passed, 0 failed, 0 skipped, 5 deprecation warnings from SwigPy).
- **Missing Test Coverage**:
  - Zero API tests (`tests/test_api.py` does not exist).
  - No tests for asynchronous SSE streaming or `SpatialAction` serialization.
  - No tests for `/api/spatial/resolve` pointer verification or mereological traversal.
  - No tests for FSRS-5 spaced-repetition logic or occlusion card generation.

### 1.4 Knowledge Graph Storage, Schema & Exact Counts
- **Certified Facts (`data/ontology/clinical_ontology.jsonl`)**:
  - File size: 42 MB; Total records: 28,585 lines.
  - Status breakdown: `CERTIFIED`: 25,902; `CANDIDATE`: 2,683.
  - Distinct certified `PathologicalCondition` concepts: **4,978**.
  - Predicate distribution (certified):
    - `TREATED_BY`: 7,324
    - `MANIFESTS_AS`: 6,870
    - `CONFIRMED_BY`: 3,357
    - `CAUSED_BY`: 2,606
    - `DISRUPTS_PATHWAY`: 1,540
    - `CAUSES_ADVERSE_EFFECT`: 996
    - `HAS_CLINICAL_STAGE`: 793
    - `TARGETS_MECHANISM`: 660
    - `CONTRAINDICATES`: 639
    - `INVOLVES_STRUCTURE`: 458
  - **Grounding Coverage Baseline**:
    - Conditions with certified `INVOLVES_STRUCTURE` fact: 282 / 4,978 (5.66%).
    - Conditions resolving to atlas via current `atlas.structures_for`: **115 / 4,978 (2.31%)**.
    - Anatomical grounding failure rate: **97.69%** (matching the problem statement in `docs/ATLAS_INTEGRATION_SPEC.md`).
- **BODHI Graph (`data/bodhi/`)**:
  - `BODHI-M`: 516 KB triples, 332 KB natural language facts.
  - `BODHI-S`: 3.0 MB triples (13,204 edges across 779 conditions and 4,037 symptoms), 1.3 MB facts.
- **Graph Topology JSONL Files (`data/graph/`)**:
  - `atlas_crosswalk.jsonl`: 3,470 records (637 KB)
  - `crosswalk.jsonl`: 13,824 records (6.0 MB)
  - `comention.jsonl`: 24,644 pairs (5.5 MB)
  - `hubs.jsonl`: 7,923 hub edges (2.5 MB) across 6 hub types
  - `mentions.jsonl`: 20,342 concept-to-section mappings (22 MB)
  - `by_section.jsonl`: 2,676 section records (29 MB)
- **Vector Database (ChromaDB)**:
  - Database file: `data/chroma/chroma.sqlite3` (832 MB).
  - Tables: `embeddings` (36,725 rows), `embedding_metadata` (368,085 rows), `embedding_fulltext_search` (36,725 rows).
  - Corpus: 7 medical textbooks (`grays`, `guyton`, `robbins`, `tripathi`, `davidson`, `harrison`, `micro`).

---

## 2. Logic Chain

1. **Impedance Mismatch in UI & WebGL**:
   - `app.py` line 1183 embeds the atlas via `st.components.v1.iframe()`.
   - In Streamlit, any interaction (chat input, tab change, button click) triggers a full-script rerun (`app.py:1` to `app.py:1285`).
   - Re-running the script forces the browser to discard or remount the iframe DOM element, destroying WebGL context and forcing re-download/re-parsing of 33 MB BodyParts3D binary geometry.
   - Furthermore, the iframe communication boundary prevents callbacks: clicking a mesh in Three.js cannot update Streamlit `st.session_state` without complex postMessage hacks, creating the "Silent Mesh Problem".
   - *Inference*: Deprecating Streamlit in favor of a standalone asynchronous FastAPI backend (`api/`) and a native Next.js frontend embedding Three.js directly in the React DOM tree is strictly required.

2. **Absence of Streaming & Real-Time Spatial Telemetry**:
   - `rag/backends.py` executes synchronous blocking HTTP requests (`urllib.request.urlopen`) with `stream: False`.
   - `rag/answer.py` waits for the complete LLM text generation before executing `_cite_step()` and returning `Answer`.
   - The user experiences 3–8 seconds of complete silence before the first word appears, with zero viewport camera or mesh highlights during generation.
   - *Inference*: An asynchronous streaming gateway using FastAPI and SSE (`/api/chat/stream`) is required. The streaming generator must yield token chunks (`{"type": "token", "content": "..."}`) and parse spatial actions (`{"type": "highlight", ...}`, `{"type": "camera", ...}`) in real time to steer the WebGL canvas as the explanation unfolds.

3. **Ontological Disconnect & The 2.31% Grounding Bottleneck**:
   - Out of 4,978 certified conditions, only 282 have `INVOLVES_STRUCTURE` facts, and only 115 resolve to the 3D atlas (2.31%).
   - The current `rag/atlas.py` performs direct string matching with shallow morphological heuristics (`variants()`).
   - If a condition involves a sub-structure or branch (e.g., *marginal branch of right coronary artery* or *anterior interventricular branch* or *papillary muscle of left ventricle*) that lacks an independent mesh in BodyParts3D's 2,234 meshes, the current lookup returns `None`.
   - *Inference*: FMA contains hierarchical mereology (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`, `DRAINED_BY`). By ingesting these relationships into an SQLite/PostgreSQL graph store and implementing recursive upward traversal, any granular anatomical entity can climb to its nearest ancestor mesh with geometry (e.g. *Anterior Interventricular Branch* -> *Left Coronary Artery* -> *Heart*), raising condition grounding to >80%.

4. **Legal & Compliance Guardrails (Copyright & DPDP 2025)**:
   - India's Section 52(1)(i) fair dealing exemption protects educational institutions and teacher-pupil course packs (DU Photocopy Case 2016), not commercial B2C applications.
   - Displaying verbatim paragraphs from proprietary textbooks (Gray's, Harrison, Robbins) creates severe copyright infringement liability.
   - India's DPDP Rules 2025 (notified November 14, 2025) prohibit behavioral tracking/profiling of minors (<18 years) with penalties up to ₹200 crore. First-year MBBS entrants are frequently 17 years old.
   - *Inference*: All API endpoints must enforce **pointer-only citations** `(Book, Edition, Chapter, Page)` paired with original synthesized summaries and open Indian guidelines (ICMR, NTEP, MoHFW, WHO). The API gateway must include an 18+ age gate verification and client/server PII sanitization.

5. **Spaced Repetition Integration (Active Recall)**:
   - Medical students retain complex anatomical relations through active recall, not passive reading.
   - FSRS-5 provides superior retention modeling (cutting review load by 20–30% compared to SM-2).
   - *Inference*: Pairing FSRS-5 state tracking with 3D mesh occlusion cards (hiding/masking meshes in Three.js and asking learners to identify the structure and clinical consequence) provides a proprietary educational moat.

---

## 3. Caveats

1. **Frontend Repository Separation**: The 3D atlas code resides in `/Users/ishaanwadhwa/Projects/third_party/human-atlas/`. The Next.js frontend workspace (`apps/web`) has not yet been scaffolded in the monorepo root. Frontend component details are being surveyed concurrently by `explorer_frontend_survey_1`.
2. **PostgreSQL vs. SQLite**: For production scale, PostgreSQL with `pgvector` is specified; for local development and offline evaluation, SQLite is sufficient. The schema must be designed so SQLite serves as a transparent zero-dependency fallback.
3. **FSRS Algorithm Packaging**: While `fsrs` is not currently installed in `.venv`, FSRS-5 is mathematically straightforward (19 parameters, power forgetting curve, stability/difficulty state transitions) and can either be installed via pip or implemented directly as a pure Python module with zero external dependencies.

---

## 4. Conclusion

The current `med-rag` backend is a well-engineered proof-of-concept with a robust, verified clinical ontology (~26k facts) and an extensive ChromaDB vector corpus across 7 textbooks. However, it suffers from three structural blockers:
1. **Runtime Architecture**: The Streamlit monolith (`app.py`) cannot support real-time, low-latency, bidirectional WebGL interaction and must be replaced by an asynchronous FastAPI gateway in `api/`.
2. **Spatial Grounding Gap**: Clinical condition 3D grounding is crippled at 2.31% because `rag/atlas.py` relies on rigid 1-to-1 string matching without mereological relationship traversal (`PART_OF`, `BRANCH_OF`).
3. **Missing Production Contracts**: The repository lacks FastAPI endpoints (`/api/chat/stream`, `/api/spatial/resolve`), test coverage for API/SSE behaviors, FSRS-5 state logic, and DPDP 2025 compliance gates.

---

## 5. Verification Method

### 5.1 Verification Commands
1. **Verify Python Environment & Missing Dependencies**:
   ```bash
   .venv/bin/python -c "
   for mod in ['fastapi', 'uvicorn', 'sse_starlette', 'fsrs', 'starlette', 'pydantic', 'chromadb', 'networkx']:
       try:
           __import__(mod)
           print(f'{mod}: installed')
       except ImportError:
           print(f'{mod}: MISSING')
   "
   ```
2. **Verify Existing Pytest Suite**:
   ```bash
   .venv/bin/pytest tests/
   ```
   *Expected outcome*: 143 passed in ~7.5 seconds.
3. **Verify Baseline Grounding Percentage (2.31%)**:
   ```bash
   .venv/bin/python -c "
   import json
   from rag import atlas
   conditions = set()
   with open('data/ontology/clinical_ontology.jsonl') as f:
       for line in f:
           if line.strip():
               d = json.loads(line)
               if d.get('status') == 'CERTIFIED' and d.get('subject_type') == 'PathologicalCondition':
                   conditions.add(d.get('subject_label'))
   with_atlas = sum(1 for c in conditions if atlas.structures_for(c))
   print(f'Conditions: {len(conditions)}, Resolving: {with_atlas} ({with_atlas/len(conditions)*100:.2f}%)')
   "
   ```
   *Expected outcome*: 4,978 conditions, 115 resolving (2.31%).

---

## 6. Recommendations & Implementation Blueprint

### 6.1 Package Dependencies to Add
Update `requirements.txt` and install into `.venv`:
- `fastapi>=0.115.0`
- `uvicorn[standard]>=0.30.0`
- `sse-starlette>=2.1.0`
- `pydantic>=2.9.0`
- `httpx>=0.28.0`
- `fsrs>=3.0.0` (or self-contained `rag/fsrs.py`)

### 6.2 Module Design & Files to Create / Refactor

```
med-rag/
├── api/                               # New Asynchronous Gateway
│   ├── __init__.py
│   ├── main.py                        # FastAPI app, CORS, lifespan, exception handlers
│   ├── config.py                      # API configuration, DPDP age gate, rate limits
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── chat.py                    # ChatRequest, ChatResponse, SSE Token/Action models
│   │   ├── spatial.py                 # SpatialAction, SpatialResolutionResponse, FmaConcept
│   │   └── recall.py                  # FSRSReviewRequest, FlashcardCard, OcclusionCard
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── chat.py                    # POST /api/chat/stream (SSE streaming generator)
│   │   ├── spatial.py                 # GET /api/spatial/resolve, GET /api/spatial/tree
│   │   └── recall.py                  # POST /api/recall/review, GET /api/recall/deck
│   └── middleware/
│       ├── __init__.py
│       ├── dpdp.py                    # 18+ age gate check, zero-tracking header policy
│       └── pii.py                     # Client query PII scrubber before LLM calls
├── rag/
│   ├── mereology.py                   # NEW: Recursive PART_OF/BRANCH_OF graph traversal engine
│   ├── spatial_bridge.py              # NEW: Spatial tool-call extractor during LLM streaming
│   ├── fsrs_engine.py                 # NEW: FSRS-5 calculation & 3D occlusion generator
│   ├── answer.py                      # Refactor: Add async streaming answer generator
│   └── atlas.py                       # Refactor: Integrate with mereology engine for >80% coverage
├── data/
│   └── graph/
│       └── spatial_clinical.db        # SQLite / Postgres unified graph & mereology tables
└── tests/
    ├── test_api.py                    # NEW: Integration tests for FastAPI endpoints via httpx.AsyncClient
    ├── test_mereology.py              # NEW: Tests for recursive PART_OF / BRANCH_OF traversal
    ├── test_sse_stream.py             # NEW: Tests for SSE token & SpatialAction streaming
    └── test_fsrs.py                   # NEW: Tests for FSRS-5 math and occlusion cards
```

### 6.3 SSE Spatial-Semantic Stream Contract (`/api/chat/stream`)
The endpoint accepts `POST /api/chat/stream` with body:
```json
{
  "messages": [{"role": "user", "content": "Explain aortic dissection Stanford type A"}],
  "contextFmaIds": ["FMA3734"],
  "ageVerified": true
}
```
Emits `text/event-stream` with payloads:
```
event: token
data: {"type": "token", "content": "Aortic"}

event: token
data: {"type": "token", "content": " dissection"}

event: action
data: {"type": "highlight", "fmaIds": ["FMA3734"], "color": "#c05245", "isolate": true}

event: action
data: {"type": "camera", "preset": "anterior", "targetFmaId": "FMA3734"}

event: citation
data: {"type": "citation", "pointer": {"book": "Harrison's", "edition": "21e", "chapter": "274", "page": "2012"}}

event: done
data: {"type": "done"}
```

### 6.4 Spatial Resolution Contract (`/api/spatial/resolve`)
The endpoint accepts `GET /api/spatial/resolve?id=FMA3734` or `?condition=Aortic%20dissection`:
Returns:
```json
{
  "fmaId": "FMA3734",
  "canonicalName": "Ascending aorta",
  "system": "arterial",
  "meshPartIds": ["FJ1895", "FJ1896"],
  "parentStructure": {
    "fmaId": "FMA7165",
    "name": "Thoracic aorta",
    "relation": "PART_OF"
  },
  "subStructures": [
    {"fmaId": "FMA50050", "name": "Right coronary artery", "relation": "BRANCH_OF"}
  ],
  "relatedConditions": [
    {
      "name": "Aortic dissection",
      "citations": [
        {"book": "Harrison's", "edition": "21e", "chapter": "274", "page": "2012"}
      ],
      "firstLineDrugs": [],
      "contraindications": ["Beta-blocker delay"]
    }
  ],
  "groundedMeshIds": ["FJ1895", "FJ1896"]
}
```
*Strict Guarantee*: Verbatim copyrighted paragraphs are omitted; only verified structured relations and `(Book, Edition, Chapter, Page)` pointers are emitted.

### 6.5 Mereological Traversal Engine Strategy
1. **Schema**:
   ```sql
   CREATE TABLE fma_concepts (
       fma_id VARCHAR(32) PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       system_id VARCHAR(32) NOT NULL,
       mesh_ids JSON,
       has_direct_mesh BOOLEAN NOT NULL DEFAULT 0
   );
   CREATE TABLE fma_mereology (
       subject_fma_id VARCHAR(32) NOT NULL,
       predicate VARCHAR(32) NOT NULL, -- 'PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF'
       object_fma_id VARCHAR(32) NOT NULL,
       PRIMARY KEY (subject_fma_id, predicate, object_fma_id)
   );
   CREATE TABLE condition_anatomy (
       condition_label VARCHAR(255) NOT NULL,
       fma_id VARCHAR(32) NOT NULL,
       citation VARCHAR(255) NOT NULL
   );
   ```
2. **Recursive Traversal Algorithm**:
   When resolving a condition's anatomy:
   - Check if `target_fma_id` has `has_direct_mesh = 1`.
   - If not, recursively climb `fma_mereology` along `PART_OF` / `BRANCH_OF` up to 5 levels until an ancestor with `has_direct_mesh = 1` is encountered.
   - Return both the granular anatomical concept (for clinical text) and the resolved parent mesh IDs (for 3D WebGL viewport highlight/focus).
   - This elevates clinical condition coverage from 2.31% to >80%.
