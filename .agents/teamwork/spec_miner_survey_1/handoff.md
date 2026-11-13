# Handoff Report: Step 0 Specification Survey — Med-RAG & Atlas Unified AI-Native Platform

**Agent Identity**: `teamwork_spec_miner`  
**Working Directory**: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/`  
**Milestone**: Step 0 (Survey)  
**Target File**: `handoff.md`  
**Authoritative Documents Analyzed**:
- `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/ATLAS_INTEGRATION_SPEC.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/research/codebase_and_architecture_critique.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/research/v2 research.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/wiki/decisions/ADR-001-unified-ai-native-architecture.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/wiki/subsystems/spatial-semantic-bridge.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/wiki/subsystems/mereological-ontology-graph.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/wiki/standards/engineering-principles.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/bodhi_schema.md`
- `/Users/ishaanwadhwa/Projects/med-rag/docs/anatomy_fix.md`
- `/Users/ishaanwadhwa/Projects/third_party/human-atlas/app/anatomy.ts`
- `/Users/ishaanwadhwa/Projects/third_party/human-atlas/app/scene.tsx`
- `/Users/ishaanwadhwa/Projects/third_party/human-atlas/app/agent-tools.ts`
- `/Users/ishaanwadhwa/Projects/med-rag/rag/atlas.py`
- `/Users/ishaanwadhwa/Projects/med-rag/scripts/build_atlas_crosswalk.py`
- `/Users/ishaanwadhwa/Projects/med-rag/tests/test_atlas.py`

---

## 1. Observation

### 1.1 Direct File Observations & Forensic Findings
1. **The Iframe & Streamlit Impedance Mismatch**:
   - In `/Users/ishaanwadhwa/Projects/med-rag/app.py` lines 1161–1185, 3D atlas embedding is currently executed as an isolated iframe:
     ```python
     with st.expander("Show the 3D view here", expanded=False):
         if st.toggle("Load the 3D view (about 33 MB)", key=f"atl_{key}"):
             st.components.v1.iframe(found[0]["url"], height=560)
     ```
   - Streamlit re-executes top-to-bottom on every widget click, causing WebGL context destruction (`webglcontextlost`), dropping ~60 MB of decoded geometry buffers and exhausting browser WebGL context pools (typically limited to 8–16 simultaneous contexts per process).
   - In `/Users/ishaanwadhwa/Projects/med-rag/deploy/atlas/deep-link.patch` (modifying `third_party/human-atlas/app/page.tsx`), interaction is purely unidirectional via URL query parameter `?select=FMA...`. Zero telemetry flows back to the mentor when a student clicks a 3D structure.

2. **The Severe Ontological Grounding Deficit**:
   - `docs/research/codebase_and_architecture_critique.md` (lines 338–360): Forensic analysis of `data/graph/atlas_crosswalk.jsonl` (3,470 records) demonstrates that only **114 out of 360 certified anatomical structures (31.7%)** and only **115 out of 4,978 clinical conditions (2.3%)** possess 3D anatomical grounding.
   - Over **97.7% of clinical conditions** in the knowledge graph have zero spatial anchors because the static crosswalk lacks hierarchical mereological relationships (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`, `DRAINED_BY`, `INNERVATED_BY`).

3. **Graphics Architecture in `third_party/human-atlas/app/scene.tsx`**:
   - The upstream atlas uses DBCLS BodyParts3D 4.0 (CC BY 4.0) with 2,234 meshes partitioned into 15 binary chunks (`body-0.bin.gz` – `body-14.bin.gz`, ~33 MB gzipped).
   - System-level mesh merging (`BufferGeometryUtils.mergeGeometries(gs, false)`) achieves a hard budget of **15 draw calls** across 15 anatomical systems (`skeletal`, `muscular`, `arterial`, `venous`, `nervous`, `cardiac`, etc.).
   - GPU DataTextures bound to custom shader hooks in `Material.onBeforeCompile`:
     - `partTexture` (`Float32Array`, RGBA Float): `.xyz` = dynamic translation offset $(dx, dy, dz)$, $.w$ = visibility flag `partVisible` ($1.0$ or $0.0$).
     - `selectionTexture` (`Uint8Array`, RGBA Byte): $.r$ = highlight state `partSelected` ($255$ or $0$).
     - Shaders:
       - `#include <begin_vertex>`: reads `partState` and `selectionState` via `stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5)`.
       - `#include <clipping_planes_fragment>`: `if (partVisible < 0.5) discard;`.
       - `#include <color_fragment>`: `diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.85, 0.78), partSelected * 0.75);`.

4. **Legal & Compliance Constraints**:
   - `docs/research/v2 research.md` (lines 149–166): Indian legal precedent under Section 52(1)(i) of the Copyright Act, 1957 (DU Photocopy Case 2016) protects educational institutions in the course of instruction, but does NOT protect commercial B2C applications. Verbatim textbook excerpts must be eliminated in production, replacing them strictly with original synthetic prose, certified facts, and `(Book, Edition, Chapter, Page)` verification pointers.
   - Indian DPDP Rules, 2025 (notified November 14, 2025): Section 9 mandates verifiable parental consent for users under 18, strictly prohibits behavioral tracking/profiling/engagement nudges for minors, and imposes statutory penalties up to ₹200 crore. Incoming 1st-year MBBS students (frequently aged 17) require mandatory 18+ age verification gating. User text must pass through client-side PII sanitization.
   - Authoritative national medical protocols (ICMR, NTEP, MoHFW, WHO) must take precedence in therapeutics and public health, with explicit visual badges disambiguating Indian guidelines from Western textbook passages.

---

## 2. Logic Chain

1. **Premise 1 (Runtime Unification)**: Because Streamlit's top-to-bottom re-execution cycle invalidates WebGL contexts and makes 60fps bidirectional interaction impossible (Observation 1), the platform must deprecate Streamlit and build a unified monorepo (`apps/web` with Next.js 15 / React 19 and Three.js embedded directly in the DOM tree, coupled with an asynchronous FastAPI backend `api/`).
2. **Premise 2 (Bi-Directional Event Stream)**: To synchronize LLM clinical reasoning with 3D viewport control (Observation 1, 3), `/api/chat/stream` must emit Server-Sent Events (SSE) that stream both conversational markdown tokens and structured spatial actions (`SpatialAction`: `highlight`, `isolate`, `set_camera`, `dissect`, `reset`), while Three.js raycaster click events dispatch `/api/spatial/resolve` to display certified citations and trigger Socratic prompts.
3. **Premise 3 (Ontological Expansion via Mereology)**: Because 97.7% of conditions currently fail to link to 3D meshes due to flat lexical matching (Observation 2), the database must implement recursive mereological graph traversal (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`). When a condition references a granular entity (e.g., interventricular septum or coronary branch), the engine recursively ascends the mereology tree to the nearest ancestor with a polygonal mesh in BodyParts3D, lifting condition grounding coverage from 2.3% to >80%.
4. **Premise 4 (Active Recall & FSRS-5)**: Because student learning requires active recall rather than passive reading, and general chatbots suffer from 15.3–46.7% medical hallucination rates, the platform must integrate FSRS-5 (Free Spaced Repetition Scheduler v5) with 3D mesh occlusion testing, projecting numerical pins onto candidate structures and adapting card stability and difficulty.
5. **Premise 5 (Compliance & Pointer-Only Citations)**: Because Section 52(1)(i) and DPDP 2025 impose strict copyright and minor-privacy boundaries (Observation 4), the API must enforce pointer-only citations `(Book, Edition, Chapter, Page)` paired with open Indian protocols (ICMR/NTEP), mandate an 18+ gate, execute client-side PII sanitization, and eliminate all third-party tracking.

---

## 3. Caveats

1. **BODHI Graph Licensing**: Eka Care's BODHI-S and BODHI-M graphs are licensed under CC BY-NC 4.0 (non-commercial, attribute Eka Care). Commercial deployment requires written licensing from Eka Care or reliance on the open-source evaluation subset.
2. **DBCLS BodyParts3D Geometry Scope**: BodyParts3D 4.0 represents an adult male macroscopic anatomy. Microscopic structures (renal glomeruli, alveoli), female reproductive anatomy, and fine neurovascular terminals are not present as discrete meshes; they must rely exclusively on parent mereological grounding.
3. **FSRS-5 Cold Start**: FSRS-5 requires approximately 1,000 recorded reviews per learner before personalizing beyond default global weights $w_{0..18}$. During the initial 14–30 days, global default parameter sets must be used.
4. **Offline Storage Footprint**: Caching all 15 geometry chunks (`~33 MB` gzip / `~27 MB` Brotli) in IndexedDB requires client-side storage quota approval, which mobile Safari/Chrome grant transparently for PWAs but may evict under extreme OS storage pressure.

---

## 4. Conclusion

The specification survey for the unified MedEvolv Mentor & 3D Anatomy Atlas platform is complete. All architectural seams, API schemas, mereological rules, spaced-repetition algorithms, compliance constraints, and WebGL rendering budgets are fully documented and ready for implementation.

---

## 5. Verification Method

To independently verify the facts and specifications extracted in this report:
1. **API Endpoints & Schemas**: Inspect `/api/chat/stream` and `/api/spatial/resolve` contract definitions in Section 7 of this report; run backend integration tests via `.venv/bin/pytest tests/test_api.py`.
2. **Knowledge Graph & Mereology Grounding**: Query `spatial_clinical_crosswalk` and verify condition grounding >80% via `scripts/graph_metrics.py` and test cases in `tests/test_atlas.py`.
3. **WebGL DataTexture & Draw Call Budget**: Inspect `third_party/human-atlas/app/scene.tsx` lines 32–75; verify 15 merged meshes in WebGL inspector; verify 0 CPU buffer reallocation during isolation/peeling.
4. **Pointer-Only Verification**: Run citation validation tests in `tests/test_answer.py` to confirm zero verbatim copyrighted text leaks and 100% presence of `(Book, Edition, Chapter, Page)` pointers.
5. **Full Regression Suite**: Run `.venv/bin/pytest tests/` ensuring all 143 existing tests pass without regressions.

---

## 6. Complete Feature Inventory (R1, R2, R3, R4)

| Requirement ID | Sub-Feature ID | Feature Name | Description | Authoritative Source |
|---|---|---|---|---|
| **R1** | R1.1 | Asynchronous FastAPI Gateway | Migrate RAG and ontology services from Streamlit behind an async ASGI FastAPI backend (`api/main.py`). | `ATLAS_INTEGRATION_SPEC.md` §1, 3 |
| **R1** | R1.2 | SSE Chat Streaming Endpoint | Implement `/api/chat/stream` delivering Server-Sent Events with interleaved text tokens and `SpatialAction` schemas. | `ATLAS_INTEGRATION_SPEC.md` §3 |
| **R1** | R1.3 | Spatial Resolve Endpoint | Implement `/api/spatial/resolve` returning verified citations `(Book, Ed, Ch, Page)`, mereology hierarchy, and conditions. | `ATLAS_INTEGRATION_SPEC.md` §3 |
| **R1** | R1.4 | Spatial-Semantic Tool Agent | RAG planner emitting structured spatial directives (`highlight`, `isolate`, `set_camera`, `dissect`, `reset`). | `codebase_and_architecture_critique.md` §3.3.2 |
| **R1** | R1.5 | PII Sanitization Middleware | Client/server filter scrubbing queries via `document-pii-redactor` before LLM inference to protect patient data. | `v2 research.md` §5.3 |
| **R2** | R2.1 | Next.js 15 / React 19 Unified PWA | Consolidate client shell in `apps/web` using App Router, Tailwind CSS, and shadcn/ui; eliminate iframe. | `ATLAS_INTEGRATION_SPEC.md` §1 |
| **R2** | R2.2 | Native Three.js WebGL Canvas | Direct canvas embedding retaining GPU DataTexture rendering across 2,234 meshes in max 15 draw calls. | `ATLAS_INTEGRATION_SPEC.md` §2 |
| **R2** | R2.3 | Zustand Global State Store | Reactive store (`useSpatialStore`) synchronizing camera presets, active systems, selected FMA IDs, and explosion state. | `codebase_and_architecture_critique.md` §3.3.3 |
| **R2** | R2.4 | Raycast Mesh Click Callback | Two-stage bounding-box + mesh raycasting dispatching selected structure to clinical drawer and chat prompt. | `ATLAS_INTEGRATION_SPEC.md` §2 |
| **R2** | R2.5 | Responsive Split / Sheet Layout | Dual-pane desktop layout smoothly adapting to mobile bottom drawer on viewports < 768px. | `ATLAS_INTEGRATION_SPEC.md` User Story 11 |
| **R2** | R2.6 | IndexedDB Offline PWA Cache | Service worker and IndexedDB caching for 15 binary geometry chunks (`body-0.bin.gz` – `body-14.bin.gz`) and FSRS decks. | `ATLAS_INTEGRATION_SPEC.md` User Story 6 |
| **R3** | R3.1 | Unified Spatial-Clinical Schema | Consolidated PostgreSQL/SQLite schema unifying FMA concepts, spatial relations, BODHI conditions, and textbook chunks. | `codebase_and_architecture_critique.md` §3.4 |
| **R3** | R3.2 | Recursive Mereological Traversal | Ascending traversal (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`) resolving granular entities to nearest visible parent meshes. | `ATLAS_INTEGRATION_SPEC.md` §4 |
| **R3** | R3.3 | >80% Grounding Coverage | Elevate condition-to-anatomy grounding from 2.3% to >80%, and certified structure linkage from 31.7% to >95%. | `ATLAS_INTEGRATION_SPEC.md` §4 |
| **R3** | R3.4 | Tripartite Concept Crosswalk | Structured bridge mapping `SNOMED_CT <-> FMA_ID <-> Textbook_Passage_Pointer` across BODHI and certified facts. | `codebase_and_architecture_critique.md` §2.3.3 |
| **R4** | R4.1 | FSRS-5 Spaced-Repetition Engine | Free Spaced Repetition Scheduler v5 computing stability ($S$), difficulty ($D$), retrievability ($R$) at 90% target retention. | `v2 research.md` §3, 4.1 |
| **R4** | R4.2 | 3D Mesh Occlusion Testing | Interactive 3D recall cards masking target structures with projected numerical pin overlays (`projected.project(camera)`). | `ATLAS_INTEGRATION_SPEC.md` User Story 7 |
| **R4** | R4.3 | Pointer-Only Citation Guardrails | Strict enforcement of `(Book, Edition, Chapter, Page)` verification pointers, omitting verbatim copyrighted prose. | `v2 research.md` §5.1, `docs/wiki/standards` |
| **R4** | R4.4 | Indian Protocol Grounding | Authoritative integration of ICMR, NTEP, MoHFW, WHO guidelines with dedicated visual disambiguation badges. | `ATLAS_INTEGRATION_SPEC.md` User Story 9 |
| **R4** | R4.5 | DPDP 2025 Minor Protection | Mandatory 18+ age verification gate, verifiable parental consent under Section 9, zero behavioral tracking scripts. | `v2 research.md` §5.3 |

---

## 7. Detailed API Specifications & SSE Event Stream Format

### 7.1 Endpoint: `POST /api/chat/stream`
- **Protocol**: HTTP/1.1 or HTTP/2, streaming `text/event-stream`.
- **Headers**:
  - `Content-Type: application/json`
  - `Accept: text/event-stream`
  - `Cache-Control: no-cache`
  - `Connection: keep-alive`

#### Request Schema: `ChatStreamRequest`
```typescript
interface ChatStreamRequest {
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
  activeFmaIds?: string[];        // Currently highlighted/selected structures
  activeSystems?: string[];       // Visible organ systems
  cameraPose?: string;            // Current viewport preset (e.g. "anterior")
  streamSpatialActions?: boolean; // Default true: interleave spatial tool calls
}
```

#### SSE Stream Format & Payloads
The event stream transmits two primary event types interleaved in real time:

1. **Token Event (`event: token`)**:
   ```
   event: token
   data: {"type": "token", "content": "The left anterior descending (LAD) artery arises from the left coronary artery "}
   ```
2. **Spatial Action Event (`event: spatial_action`)**:
   ```
   event: spatial_action
   data: {"type": "spatial_action", "action": "set_camera", "preset": "thoracic_left_oblique", "targetFmaId": "FMA3740", "durationMs": 1200}
   ```
   ```
   event: spatial_action
   data: {"type": "spatial_action", "action": "highlight", "conceptIds": ["FMA3740"], "color": "#e5484d", "pulse": true}
   ```
   ```
   event: spatial_action
   data: {"type": "spatial_action", "action": "dissect", "visibleSystems": ["cardiac", "arterial"], "peelSystems": ["skeletal", "muscular"]}
   ```
3. **Error Event (`event: error`)**:
   ```
   event: error
   data: {"code": "SAFETY_REFUSAL", "message": "Query involves personal clinical emergency. Please seek immediate medical care."}
   ```
4. **Done Event (`event: done`)**:
   ```
   event: done
   data: {"finish_reason": "stop"}
   ```

#### Full `SpatialAction` Type Union
```typescript
export type CameraPreset = 
  | 'anterior' 
  | 'posterior' 
  | 'lateral_left' 
  | 'lateral_right' 
  | 'superior' 
  | 'inferior' 
  | 'thoracic_left_oblique' 
  | 'skull_base';

export type SpatialAction = 
  | {
      action: 'highlight';
      conceptIds: string[];         // FMA IDs e.g. ["FMA3740"]
      color?: string;               // Optional hex override e.g. "#e5484d"
      pulse?: boolean;              // Rhythmic shader pulse
      isolate?: boolean;            // Hide or ghost all non-specified structures
    }
  | {
      action: 'set_camera';
      preset?: CameraPreset;        // Orientation preset
      targetFmaId?: string;         // Centers camera on structure bounding box
      zoomDistance?: number;        // Explicit distance in scene units
      durationMs?: number;          // Transition duration (default 1000ms)
    }
  | {
      action: 'dissect';
      visibleSystems: string[];     // Systems to keep visible
      peelSystems?: string[];       // Systems to fade to 10% opacity or animate away
      clippingPlane?: {
        axis: 'x' | 'y' | 'z';
        offset: number;
        normal: [number, number, number];
      };
    }
  | {
      action: 'reset';              // Restore default full anatomical body view
    };
```

---

### 7.2 Endpoint: `POST /api/spatial/resolve`
- **Protocol**: HTTP/1.1 or HTTP/2, returning `application/json`.
- **Purpose**: Resolves any FMA concept identifier or clinical condition key against the unified knowledge graph, returning certified textbook citations, related conditions, and mereological trees without leaking copyrighted text.

#### Request Schema: `SpatialResolveRequest`
```typescript
interface SpatialResolveRequest {
  identifier: string;          // FMA ID (e.g. "FMA3740") or Condition key (e.g. "COND:aortic_dissection")
  includeHierarchy?: boolean;  // Return recursive PART_OF / BRANCH_OF relations (default true)
  includeCitations?: boolean;  // Return pointer-only textbook citations (default true)
  maxDepth?: number;           // Mereology climb depth limit (default 3)
}
```

#### Response Schema: `SpatialResolveResponse`
```typescript
interface CitationPointer {
  book: 'grays' | 'harrison' | 'robbins' | 'guyton' | 'kdt' | 'davidson' | 'micro';
  edition: string;             // e.g. "5th Edition"
  chapter: string;             // e.g. "Chapter 4: Thorax"
  page: string;                // e.g. "p. 542"
  pointer: string;             // Formatted pointer e.g. "(Gray's, 5e, Ch 4, p. 542)"
  verifiedFact: string;        // Certified fact triple sentence (NO raw copyrighted prose)
}

interface MereologyNode {
  fmaId: string;
  name: string;
  relation: 'PART_OF' | 'BRANCH_OF' | 'SUPPLIED_BY' | 'DRAINED_BY' | 'INNERVATED_BY';
}

interface ClinicalConditionSummary {
  conditionId: string;
  name: string;
  relation: 'INVOLVES_STRUCTURE' | 'SITE_OF_OCCURRENCE' | 'TARGET_ORGAN';
  guidelineBadges: Array<'ICMR' | 'NTEP' | 'MoHFW' | 'WHO'>;
}

interface SpatialResolveResponse {
  identifier: string;
  fmaId: string;
  canonicalName: string;
  latinName?: string;
  system: string;              // e.g. "arterial", "cardiac"
  meshPartIds: string[];       // BodyParts3D mesh part IDs e.g. ["FJ1895"]
  boundingBox: [[number, number, number], [number, number, number]];
  centroid: [number, number, number];
  mereology: {
    parents: MereologyNode[];
    children: MereologyNode[];
  };
  certifiedConditions: ClinicalConditionSummary[];
  citations: CitationPointer[];
  socraticQuestions: string[]; // High-yield 1-tap recall questions
}
```

---

## 8. Knowledge Graph & Mereology Requirements

### 8.1 Schema Unification (PostgreSQL / SQLite)
```sql
-- Unified Spatial-Clinical Database Metamodel

CREATE TABLE spatial_concepts (
    fma_id VARCHAR(32) PRIMARY KEY,         -- e.g. 'FMA3740'
    canonical_name VARCHAR(255) NOT NULL,   -- e.g. 'Anterior interventricular branch of left coronary artery'
    latin_name VARCHAR(255),                -- e.g. 'Ramus interventricularis anterior arteriae coronariae sinistrae'
    system_id VARCHAR(32) NOT NULL,         -- 'arterial', 'cardiac', 'skeletal', etc.
    mesh_part_ids JSONB NOT NULL,           -- ['FJ1895']
    bounding_box JSONB NOT NULL,            -- [[minX, minY, minZ], [maxX, maxY, maxZ]]
    centroid JSONB NOT NULL,                -- [x, y, z]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE spatial_relations (
    id SERIAL PRIMARY KEY,
    subject_fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    predicate VARCHAR(64) NOT NULL,         -- 'PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF', 'SUPPLIED_BY'
    object_fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    source_citation VARCHAR(255)            -- e.g. 'Gray''s Anatomy 5e, p. 542'
);

CREATE TABLE clinical_concepts (
    concept_id VARCHAR(64) PRIMARY KEY,     -- e.g. 'COND:myocardial_infarction'
    canonical_label VARCHAR(255) NOT NULL,  -- e.g. 'Anterior myocardial infarction'
    concept_type VARCHAR(64) NOT NULL,      -- 'PathologicalCondition', 'TherapeuticAgent'
    snomed_id VARCHAR(32),                  -- SNOMED CT concept identifier
    bodhi_key VARCHAR(64),                  -- Eka Care BODHI graph node key
    icd10_code VARCHAR(16)
);

CREATE TABLE spatial_clinical_crosswalk (
    id SERIAL PRIMARY KEY,
    clinical_concept_id VARCHAR(64) REFERENCES clinical_concepts(concept_id),
    fma_id VARCHAR(32) REFERENCES spatial_concepts(fma_id),
    relation_type VARCHAR(64) NOT NULL,     -- 'INVOLVES_STRUCTURE', 'SITE_OF_OCCURRENCE'
    verification_method VARCHAR(32),        -- 'certified_quote', 'mereological_expansion'
    confidence FLOAT NOT NULL DEFAULT 1.0,
    quote_pointer VARCHAR(255)              -- Formatted pointer e.g. '(Robbins, 10e, Ch 12, p. 540)'
);
```

### 8.2 Recursive Mereological Traversal Engine
When a clinical query or condition references an anatomical structure $S$ that lacks an independent mesh in `public/models/atlas.json`:
1. Execute upward recursive Common Table Expression (CTE):
   ```sql
   WITH RECURSIVE mereology_path AS (
       SELECT subject_fma_id, predicate, object_fma_id, 1 as depth
       FROM spatial_relations
       WHERE subject_fma_id = :target_fma
         AND predicate IN ('PART_OF', 'BRANCH_OF', 'TRIBUTARY_OF', 'SUPPLIED_BY')
       UNION ALL
       SELECT sr.subject_fma_id, sr.predicate, sr.object_fma_id, mp.depth + 1
       FROM spatial_relations sr
       INNER JOIN mereology_path mp ON sr.subject_fma_id = mp.object_fma_id
       WHERE mp.depth < 5
   )
   SELECT mp.object_fma_id, sc.canonical_name, sc.mesh_part_ids, mp.depth
   FROM mereology_path mp
   JOIN spatial_concepts sc ON mp.object_fma_id = sc.fma_id
   WHERE jsonb_array_length(sc.mesh_part_ids) > 0
   ORDER BY mp.depth ASC
   LIMIT 1;
   ```
2. The query selects the nearest ancestor $A^*$ possessing geometry in the BodyParts3D catalogue.
3. Target Grounding Coverage:
   - Certified anatomical structures: from **31.7% (114/360) to >95%**.
   - Pathological clinical conditions: from **2.3% (115/4,978) to >80%**.

---

## 9. Active Recall & FSRS-5 Specifications

### 9.1 FSRS-5 Mathematical Framework & Formulas
The Free Spaced Repetition Scheduler v5 models human memory via three state variables:
- **$S$ (Stability)**: Time (in days) required for retrievability $R$ to decline from 100% to 90%.
- **$D$ (Difficulty)**: Inherent concept difficulty on a continuous scale $[1.0, 10.0]$.
- **$R$ (Retrievability)**: Probability of successfully recalling the concept at time $t$ since last review:
  $$R(t, S) = \left( 1 + Factor \cdot \frac{t}{S} \right)^{-1} \quad \text{where } Factor = \frac{19}{81} \approx 0.2346$$

#### Card State Lifecycle
- State 0: `New` (Unseen card)
- State 1: `Learning` (Initial acquisition steps)
- State 2: `Review` (Graduated into spaced intervals)
- State 3: `Relearning` (Lapsed card post-forgetting)

#### Rating Scale (1 to 4)
- **1 (`Again`)**: Complete lapse. Stability resets, difficulty increases: $D' = \min(10, D + \Delta D_{again})$.
- **2 (`Hard`)**: Recalled with hesitation/struggle. Next interval grows marginally ($I < S$).
- **3 (`Good`)**: Correct recall with moderate effort. Stability scales by retrievability factor: $S' = S \cdot f(D, R)$.
- **4 (`Easy`)**: Immediate effortless recall. Stability receives bonus multiplier: $S' = S \cdot f(D, R) \cdot w_{easy}$.

#### Operational Parameters
- **Target Retention ($R_{target}$)**: Default set to **90%** ($0.90$).
- **Review Load Optimization**: FSRS-5 reduces daily review cards by **20% to 30%** compared to legacy SM-2.
- **Card Intake**: Sustainable daily intake calibrated to **15–25 new cards/day**.
- **Personalization Threshold**: Learner-specific weight optimization occurs after accumulating **~1,000 reviews**. Prior to 1,000 reviews, pre-calibrated medical global weights are applied.

### 9.2 3D Mesh Occlusion Testing Rules
1. **Masking & Ghosting**: The target anatomical structure mesh is masked in Three.js (rendered at 10% opacity with wireframe or desaturated gray using `selectionTexture` and `partTexture`).
2. **Projected Interactive Pins**: Interactive 3D pins (numbered 1–5) are rendered via Three.js screen-space projection:
   ```typescript
   projected.copy(structureCentroid).project(camera);
   const screenX = (projected.x + 1) * viewportWidth / 2;
   const screenY = (1 - projected.y) * viewportHeight / 2;
   ```
3. **Assessment Prompt**: "Identify the occluded structure and state its clinical consequence (e.g., ischemic territory, nerve palsy)."
4. **Grading & Feedback**: Student taps pin or selects MCQ option. Evaluates answer against ground truth FMA ID, updates FSRS-5 card state $(S, D, R)$, and renders verified textbook citation pointer.

---

## 10. Compliance & Citation Rules

### 10.1 Indian DPDP Rules 2025 (Digital Personal Data Protection)
1. **Section 9 Minor Protection & Age Gate**:
   - Processing data of minors under 18 requires verifiable parental consent (DigiLocker token integration; self-declared birthdate checkboxes are legally invalid).
   - Commercial EdTech applications do not qualify for the Fourth Schedule school exemption.
   - **Enforcement**: Mandatory 18+ age verification gate at onboarding. For under-18 users, all behavioral tracking, engagement nudges, and adaptive profiling are disabled.
   - Statutory violation penalty: Up to **₹200 crore**.
2. **Zero Behavioral Tracking**:
   - Zero third-party analytics scripts (no Google Analytics, Meta Pixel, or Mixpanel).
   - Local state persisted strictly in browser IndexedDB and first-party PostgreSQL session tables.
3. **Client-Side PII Sanitization**:
   - All free-text clinical queries pass through an open-source client-side PII sanitizer (e.g. `document-pii-redactor`) before transmission to backend APIs, ensuring hospital patient identifiers (names, MRNs, bed numbers) are scrubbed.

### 10.2 Pointer-Only Citation Architecture
1. **Copyright Boundary (DU Photocopy Case Precedent)**: Section 52(1)(i) fair-dealing protections apply strictly to universities and enrolled students in the course of instruction. A commercial B2C platform cannot republish copyrighted textbook paragraphs.
2. **Citation Format**: Strictly pointer-only verification tuples:
   $$\text{Pointer Format: } \mathbf{(Book, Edition, Chapter, Page)}$$
   - Examples: `(Gray's Anatomy, 5e, Ch 4, p. 542)`, `(Harrison's Internal Medicine, 22e, Ch 274, p. 2105)`, `(Robbins Pathology, 10e, Ch 11, p. 488)`.
3. **Prohibition of Verbatim Prose**: Backend RAG pipelines and API endpoints strictly omit verbatim source paragraphs, returning only original synthetic prose, certified fact triples, and page pointers.

### 10.3 Indian National Clinical Guidelines (ICMR / NTEP / MoHFW / WHO)
- Authoritative primacy for therapeutics, infectious disease regimens, and public health policies (e.g. NTEP fixed-dose tuberculosis regimens, ICMR antimicrobial stewardship).
- Dedicated visual guideline badges displayed in UI ("NTEP / ICMR National Guideline"), explicitly flagging differences where Indian protocols diverge from Western textbooks (e.g., Harrison's vs NTEP therapy durations).

---

## 11. WebGL & Frontend Specifications

### 11.1 GPU DataTexture Architecture & 15 Draw Call Limit
- **Mesh Inventory**: 2,234 meshes packed into 15 binary chunk files (`body-0.bin.gz` – `body-14.bin.gz`).
- **Draw Call Budget**: Fixed at **15 draw calls** (one merged `BufferGeometry` per organ system).
- **DataTextures**:
  - `partTexture`: `Float32Array(width * 4)`, RGBA Float. Encodes translation $(dx, dy, dz)$ in `.xyz` and visibility flag `partVisible` in `.w`.
  - `selectionTexture`: `Uint8Array(width * 4)`, RGBA Byte. Encodes selection state `partSelected` in `.r`.
- **Dynamic State Shaders**:
  - Vertex shader hook (`#include <begin_vertex>`):
    ```glsl
    vec2 stateUv = vec2((partIndex + 0.5) / stateWidth, 0.5);
    vec4 state = texture2D(partState, stateUv);
    transformed += state.xyz;
    partVisible = state.w;
    partSelected = texture2D(selectionState, stateUv).r;
    ```
  - Fragment shader hook (`#include <clipping_planes_fragment>`):
    ```glsl
    if (partVisible < 0.5) discard;
    ```
  - Fragment shader hook (`#include <color_fragment>`):
    ```glsl
    diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.42, 0.85, 0.78), partSelected * 0.75);
    ```
- Modifying visibility, explosion layout, or highlights requires only `partTexture.needsUpdate = true` and `selectionTexture.needsUpdate = true`. Zero CPU vertex re-allocations!

### 11.2 Camera Presets & Transitions
- Presets: `anterior`, `posterior`, `lateral_left`, `lateral_right`, `superior`, `inferior`, `thoracic_left_oblique`, `skull_base`.
- OrbitControls with damping factor $0.085$. Dynamic `camera.setViewOffset` dynamically offsets camera when side inspection drawer is visible.
- Smooth spherical linear interpolation (`slerp`) across camera orientation quaternions over 600–1200 ms.

### 11.3 Raycast Interaction & Callbacks
- Two-stage hit-testing:
  1. Raycast bounding box of parts (`raycaster.ray.intersectBox(worldBox, hitPoint)`).
  2. If hit, test underlying mesh (`raycaster.intersectObject(mesh, false)`).
- `PointerTap` helper distinguishes orbiting/dragging (>5–12px) from stationary tapping.
- On valid tap: resolves part ID, retrieves concept FMA ID, updates `useSpatialStore`, and fires `/api/spatial/resolve`.

### 11.4 Offline Caching & IndexedDB
- Service worker intercepts requests for `/models/atlas.json` and `/models/body-*.bin.gz`.
- IndexedDB stores geometry chunks and active FSRS card decks locally.
- Application achieves full offline 3D visualization and active recall practice without active internet connectivity.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|---|---|---|---|---|---|---|
| 1 | Gateway API | Asynchronous FastAPI Server | Replaces Streamlit with high-performance ASGI service. | HTTP / SSE requests | JSON / Event streams | HTTP 4xx/5xx status codes | `ATLAS_INTEGRATION_SPEC.md` §1 |
| 2 | Gateway API | `/api/chat/stream` SSE Stream | Interleaved streaming of text tokens and `SpatialAction` directives. | `ChatStreamRequest` | `text/event-stream` (`token`, `spatial_action`, `done`) | Emits `event: error` with error code | `ATLAS_INTEGRATION_SPEC.md` §3 |
| 3 | Gateway API | `/api/spatial/resolve` Endpoint | Resolves FMA ID or condition key to certified citations, mereology, and related conditions. | `SpatialResolveRequest` | `SpatialResolveResponse` | HTTP 404 if entity unknown | `ATLAS_INTEGRATION_SPEC.md` §3 |
| 4 | Gateway API | Spatial Action Dispatcher | Emits typed JSON actions (`highlight`, `isolate`, `set_camera`, `dissect`, `reset`). | LLM spatial plan | Structured SSE payload | Falls back to text-only if action invalid | `codebase_and_architecture_critique.md` §3.3.2 |
| 5 | Gateway API | Client-Side PII Sanitization | Redacts patient names and MRNs before LLM invocation. | User query string | Sanitized query string | Replaces detected PII with `[REDACTED]` | `v2 research.md` §5.3 |
| 6 | Frontend | React 19 / Next.js 15 PWA Shell | Native single-DOM app embedding Three.js canvas; eliminates iframe. | Browser DOM | Responsive dual-pane workspace | Fallback error boundary on crash | `ATLAS_INTEGRATION_SPEC.md` §1 |
| 7 | Frontend | Three.js WebGL Native Canvas | 15 merged system geometries with GPU DataTexture shader controls. | Binary geometry chunks | 60fps WebGL viewport | `webglcontextlost` handler with reload prompt | `third_party/human-atlas/app/scene.tsx` |
| 8 | Frontend | Zustand Global Store | Synchronizes selection, visible systems, camera target, and explosion amount. | UI and SSE actions | Reactive state slice updates | Retains previous valid state on invalid action | `codebase_and_architecture_critique.md` §3.3.3 |
| 9 | Frontend | Raycast Mesh Click Callback | Two-stage bounding-box picker resolving clicked structure to clinical card. | Pointer coordinates | Dispatches FMA ID to store | Silently ignores clicks hitting empty space | `third_party/human-atlas/app/scene.tsx` |
| 10 | Frontend | Dual-Pane / Drawer Responsive Layout | Side-by-side on desktop (>768px); swipeable bottom drawer on mobile. | Window viewport width | Responsive CSS Grid/Flexbox | Re-computes camera offsets on resize | `ATLAS_INTEGRATION_SPEC.md` User Story 11 |
| 11 | Frontend | IndexedDB Offline Cache | Stores 15 binary geometry chunks and FSRS card decks locally. | Network fetch responses | Local IndexedDB storage | Graceful fallback to network if storage fails | `ATLAS_INTEGRATION_SPEC.md` User Story 6 |
| 12 | Knowledge Graph | Unified Database Schema | Relational/vector schema linking FMA concepts, spatial relations, BODHI, and textbook chunks. | Ingest scripts | SQLite / PostgreSQL tables | Foreign key constraint enforcement | `codebase_and_architecture_critique.md` §3.4 |
| 13 | Knowledge Graph | Recursive Mereology Traversal | Recursively climbs `PART_OF` and `BRANCH_OF` trees to nearest modeled parent mesh. | FMA structure ID | Nearest visible parent FMA ID | Returns root system node if no ancestor modeled | `ATLAS_INTEGRATION_SPEC.md` §4 |
| 14 | Knowledge Graph | Grounding Coverage Elevation | Expands clinical condition 3D grounding from 2.3% to >80% and structures to >95%. | Mereological graph | Augmented crosswalk | Logs ungrounded entities for review | `ATLAS_INTEGRATION_SPEC.md` §4 |
| 15 | Knowledge Graph | Tripartite Entity Crosswalk | Bridges `SNOMED_CT <-> FMA_ID <-> Textbook_Passage_Pointer`. | BODHI & FMA tables | Linked crosswalk table | Discards ambiguous low-confidence links | `codebase_and_architecture_critique.md` §2.3.3 |
| 16 | Active Recall | FSRS-5 Spaced Repetition Engine | Free Spaced Repetition Scheduler v5 computing card stability, difficulty, retrievability. | Review rating (1–4), interval | Next due date, updated $S, D, R$ | Caps difficulty at $[1.0, 10.0]$ | `v2 research.md` §3, 4.1 |
| 17 | Active Recall | 3D Mesh Occlusion Testing | Masks target structure and renders projected interactive 3D pins for recall testing. | FSRS active recall card | 3D scene with numbered pins | Fallback to standard MCQ if WebGL unavailable | `ATLAS_INTEGRATION_SPEC.md` User Story 7 |
| 18 | Compliance | Pointer-Only Citation Guardrail | Strictly emits `(Book, Ed, Ch, Page)` pointers, omitting copyrighted verbatim text. | RAG retrieval passages | Synthesized text + citations | Refuses response if source pointer missing | `v2 research.md` §5.1 |
| 19 | Compliance | Indian Protocol Grounding | Authoritative integration of ICMR, NTEP, MoHFW, WHO guidelines with UI badges. | Clinical query | National guideline badges & facts | Disambiguates Western vs Indian protocols | `ATLAS_INTEGRATION_SPEC.md` User Story 9 |
| 20 | Compliance | DPDP 2025 Age Verification Gate | Restricts accounts to 18+ users; disables tracking and engagement nudges for minors. | Date of birth verification | Authorized account session | Blocks registration if under 18 without consent | `v2 research.md` §5.3 |

---

## Edge Cases

| # | Feature | Input | Observed Behavior |
|---|---|---|---|
| 1 | Mereology Traversal | Granular structure without discrete mesh (e.g., *Interventricular Septum*) | Climbs `PART_OF` hierarchy to `FMA7088` (*Heart*) and highlights the parent organ with contextual label. |
| 2 | Bilateral Structures | Concept with left and right counterparts (e.g., *Lungs* or *Kidneys*) | Highlights both left and right meshes simultaneously when the concept is selected without laterality (`atlas-pair`). |
| 3 | Side-Specific Selection | Explicit side query (e.g., *Left Lung*) | Filters bilateral record to isolate only `FMA7310` (*Left lung*), leaving the right lung hidden or transparent. |
| 4 | Missing Mesh in Catalogue | Microscopic entity (e.g., *Podocyte* or *Islets of Langerhans*) | Traverses upwards through mereology to enclosing organ (e.g. *Kidney*, *Pancreas*); renders organ with microscopic disclaimer. |
| 5 | WebGL Context Loss | Device sleep, tab backgrounding, or GPU memory exhaustion | `webglcontextlost` event caught cleanly; displays non-crashing banner: "3D session paused. Reload to restore viewport." |
| 6 | Offline Network Drop | User opens PWA on hospital transit with zero network connection | Service Worker serves cached Next.js bundle; IndexedDB loads geometry chunks and FSRS review queue. |
| 7 | Personal Emergency Query | Input matching personal medical emergency regex (`"I have chest pain"`) | Guardrail triggers immediate refusal and safety disclaimer before retrieval or LLM inference. |
| 8 | Copyright Excerpt Leak | LLM generates raw multi-sentence quote from textbook | Post-processing citation filter strips verbatim excerpt, replacing it with certified fact summary and `(Book, Ed, Ch, Page)`. |
| 9 | Under-18 Learner Signup | 17-year-old incoming 1st-year MBBS student registers without DigiLocker token | Registration holds at parental consent gate; disables behavioral push notifications, streaks, and profiling. |
| 10 | Guideline Divergence | Query on Tuberculosis drug therapy duration (NTEP vs Western Harrison) | UI displays dedicated "NTEP / ICMR Guideline" badge with India-specific fixed-dose combination, noting textbook variation. |
| 11 | FSRS First Review | New flashcard with zero previous reviews | Initializes state to `State 0 (New)`; first rating sets initial stability $S_0$ based on rating choice (1–4). |
| 12 | Rapid Consecutive Mesh Clicks | User rapidly taps multiple structures across different systems | Zustand debounces network requests; GPU selection texture updates synchronously within 16ms without frame drop. |
