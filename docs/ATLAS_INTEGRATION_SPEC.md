# Specification: Unified AI-Native Integration of MedEvolv Mentor and 3D Anatomy Atlas

## Problem Statement

Medical students preparing for high-stakes clinical examinations (such as NEET-PG, INI-CET, and university professional exams) are forced to toggle between disconnected tools: semantically inert 3D anatomical atlases (like Complete Anatomy or BioDigital Human) that offer visual models without clinical reasoning, and text-based question banks or AI chatbots (like AMBOSS or ChatGPT) that explain disease pathophysiology but are completely blind to 3D spatial anatomy. 

In the current MedEvolv implementation, `med-rag` (MedEvolv Mentor) and `med-rag-atlas` (3D Anatomy Atlas) exist as separate codebases bolted together through an isolated `<iframe>` driven by unidirectional URL parameters (`?select=FMA...`). This architecture creates critical failures for exploratory learning:
1. When a student interacts with the 3D model (clicking an artery, nerve, or organ), zero telemetry reaches the mentor; the student cannot explore its clinical significance, view textbook citations, or test recall.
2. When the AI mentor explains a clinical vignette or pathophysiology mechanism, it cannot manipulate the 3D viewport, isolate structures, or peel anatomical layers in real time.
3. Streamlit's execution model re-runs top-to-bottom on every user action, causing WebGL canvas context destruction, dropped textures, and prohibitive latency.
4. Over 97% of certified clinical conditions in the knowledge graph have zero 3D anatomical grounding because the static crosswalk lacks mereological (`PART_OF`, `BRANCH_OF`) relationship traversal.

## Solution

Merge `med-rag` and `med-rag-atlas` into a single, production-grade, AI-native web application and Progressive Web App (PWA). The unified platform features:
1. **A Dual-Pane Exploratory Workspace:** A native client-side application (React 19 / Next.js) embedding the Three.js 3D WebGL viewport directly into the same DOM tree as the Socratic AI Mentor, sharing a unified reactive state store.
2. **A Bi-Directional Spatial-Semantic Bridge:** 
   - **Text-to-Spatial:** As the AI mentor streams clinical explanations via Server-Sent Events (SSE), it emits structured spatial tool calls that dynamically highlight anatomical structures, adjust camera angles, and peel tissue layers with zero latency.
   - **Spatial-to-Text:** Clicking any 3D mesh raycasts the structure, resolves its Foundational Model of Anatomy (FMA) identifier against the clinical knowledge graph, displays certified textbook citations, and unlocks 1-click clinical reasoning and recall prompts.
3. **Unified Spatial-Clinical Knowledge Graph:** A consolidated graph and vector database linking FMA anatomical concepts, BODHI clinical conditions, and textbook citations through mereological graph expansion, raising anatomical grounding for clinical conditions from 2.3% to >80%.
4. **Active Recall & Exam Practice Integration:** Grounding 3D exploration into FSRS-5 spaced-repetition flashcards (including 3D mesh occlusion testing) and clinical vignette multiple-choice questions (MCQs) mapped to previous-year exam concepts, enforcing pointer-only textbook citations `(Book, Edition, Chapter, Page)` and open Indian national protocols (ICMR/NTEP/WHO).

## User Stories

1. As a medical student studying coronary anatomy, I want to click the Left Anterior Descending (LAD) artery in the 3D viewport, so that the mentor instantly displays its certified textbook relations, vascular territory, and clinical significance.
2. As a medical student reading an AI explanation of an inferior wall myocardial infarction, I want the 3D viewer to automatically isolate the Right Coronary Artery (RCA) and posterior descending branch, so that I can visualize the ischemic territory without manually searching the atlas.
3. As an exam aspirant, I want the AI mentor to stream answers while smoothly animating the 3D camera to the relevant anatomical region, so that my visual focus aligns with the text I am reading.
4. As a student exploring the mediastinum, I want to peel superficial muscular and skeletal layers in 3D using a layer slider, so that deeper neurovascular structures (such as the phrenic and vagus nerves) become visible in relation to thoracic organs.
5. As an MBBS student revising Pancoast tumors, I want the mentor to highlight the lung apex, sympathetic chain, and T1 nerve root simultaneously, so that I understand why the tumor causes Horner syndrome and brachial plexopathy.
6. As a student in hospital transit on patchy Wi-Fi, I want the 3D geometry and my active-recall flashcard decks to load instantly from offline device storage, so that I can study without network dropouts.
7. As an exam candidate practicing active recall, I want to review 3D occlusion flashcards where an anatomical structure is ghosted or masked, so that I must identify the structure and state its clinical consequence before revealing the answer.
8. As a medical student preparing for university Prof exams, I want every clinical fact and anatomical relation to provide a verified pointer `(Book, Edition, Chapter, Page)`, so that I can verify facts directly in my physical textbook (Gray's, Guyton, Robbins).
9. As an Indian MBBS student, I want tuberculosis and public health regimens to follow official national guidelines (NTEP/ICMR) with clear badges highlighting differences from Western standard textbooks, so that I do not lose marks on exam questions.
10. As a student exploring pathology, I want to click any condition in the clinical explorer (e.g., Aortic Dissection Stanford Type A), so that the 3D viewport immediately isolates the ascending aorta and highlights the entry tear location.
11. As a mobile learner on an Android smartphone, I want the dual-pane workspace to smoothly adapt into a responsive split layout with a swipeable bottom sheet, so that 3D interaction and chat conversation remain usable on small screens.
12. As a student reviewing an anatomical structure with left and right counterparts (such as the kidneys or lungs), I want selecting the concept to highlight both structures simultaneously when appropriate, so that bilateral relations are accurately portrayed.
13. As an exam aspirant reviewing clinical vignettes, I want each multiple-choice question to feature an interactive 3D link that reveals the involved anatomy upon submission, so that I understand the anatomical basis of my correct or incorrect choices.
14. As a student who has isolated an anatomical structure, I want a single "Show Surrounding Anatomy" toggle, so that I can immediately restore the contextual spatial relationship with neighboring organs.
15. As a student reviewing pharmacology, I want clicking a drug in the clinical graph (e.g., Atenolol) to highlight its target organ and autonomic receptors in 3D, so that I connect mechanism of action with spatial organ physiology.
16. As a student reviewing surgical anatomy, I want to inspect anatomical triangles (such as Calot's triangle or the femoral triangle) with their bounding ducts, arteries, and nerves highlighted in distinct colors, so that I can master surgical boundaries for viva exams.
17. As an exam sprinter on a tight timeline, I want an exam-date adaptive study planner that prioritizes high-yield anatomical and clinical weak areas based on FSRS-5 memory retention calculations, so that I focus my revision time efficiently.
18. As a user concerned about digital privacy, I want my clinical queries and chat history protected without third-party behavioral profiling or tracking, so that the application fully complies with Indian DPDP 2025 standards.
19. As a medical educator, I want to share a deep link that loads the exact camera pose, selected 3D structures, and clinical inquiry state, so that I can share specific case studies with students.
20. As a student asking open-ended Socratic questions (e.g., "What happens if this structure is transected during thyroidectomy?"), I want the mentor to identify the recurrent laryngeal nerve in 3D while explaining vocal cord paralysis and airway compromise, so that my exploratory questions receive multimodal answers.

## Implementation Decisions

### 1. Monorepo & Deployment Architecture
- Consolidate the client and server into a single monorepo repository structure:
  - Client Application: React 19, Next.js 15 App Router, Tailwind CSS, shadcn/ui components, and Lucide icons.
  - Server Application: Python 3.12+ FastAPI asynchronous application.
- The client application is built and served as an offline-capable Progressive Web App (PWA) with service worker caching and IndexedDB local storage.
- The server application is deployed behind a reverse proxy (Caddy) handling HTTPS termination, API routing, and compression.
- Streamlit (`app.py`) is deprecated and fully removed from the production runtime path.

### 2. Frontend State & WebGL Rendering Architecture
- Three.js WebGL canvas is embedded natively inside the React component hierarchy (eliminating all `<iframe>` sandboxes).
- The 3D scene utilizes GPU DataTexture rendering for BodyParts3D binary geometry chunks, maintaining a maximum of 15 GPU draw calls across 2,234 anatomical meshes.
- A single global client state store (Zustand) synchronizes:
  - Selected FMA concept identifiers (`selectedFmaIds: string[]`)
  - Active anatomical physiological systems (`activeSystems: SystemId[]`)
  - Camera pose and transition state (`cameraPose: CameraPreset`)
  - Hovered/inspected mesh entity (`hoveredConcept: Concept | null`)
  - Isolate and dissection layer state (`isolate: boolean, layerDepth: number`)
- Raycaster click events on the WebGL canvas directly update the state store, triggering reactive updates in the chat pane and clinical drawer without full DOM remounting.

### 3. Asynchronous Server & Bi-Directional Event Bus
- Communication between client and server occurs over HTTP and Server-Sent Events (SSE).
- Primary endpoint `/api/chat/stream` accepts conversational messages and returns an event stream supporting two distinct payload types:
  - Text Token Events: `{"type": "token", "content": "string"}`
  - Structured Spatial Action Events:
    ```typescript
    type SpatialAction = 
      | { type: "highlight"; fmaIds: string[]; color?: string; isolate?: boolean }
      | { type: "camera"; preset: "anterior" | "posterior" | "lateral" | "superior" | "target"; targetFmaId?: string }
      | { type: "layer"; system: string; visible: boolean }
      | { type: "reset" };
    ```
- Endpoint `/api/spatial/resolve` accepts an FMA identifier or clinical condition key and returns the resolved crosswalk, certified textbook citations, related clinical conditions, and mereological parent/child hierarchy.

### 4. Unified Spatial-Clinical Knowledge Graph
- Bridge FMA ontology concepts with the clinical ontology (BODHI and certified textbook facts):
  - Ingest FMA mereology relationships (`PART_OF`, `BRANCH_OF`, `SUPPLIED_BY`, `DRAINED_BY`, `INNERVATED_BY`).
  - Implement a recursive mereological traversal engine: when a condition or clinical entity references an anatomical structure not directly modeled as an independent mesh, traverse upwards to the nearest enclosing parent structure present in the 3D geometry catalogue.
- Replace the static offline `atlas_crosswalk.jsonl` with a relational database schema (PostgreSQL with pgvector for production; SQLite for local evaluation) storing:
  - `concepts` (ID, canonical name, semantic type, ontology source, FMA mapping)
  - `spatial_relations` (source_id, relation_type, target_id)
  - `certified_facts` (subject, predicate, object, book_id, chapter, page_pointer)
  - `textbook_passages` (passage_id, book_id, edition, chapter, page, embedding_vector)

### 5. Active-Recall & Legal Guardrails
- Ingest an active-recall engine implementing FSRS-5 (Free Spaced Repetition Scheduler v5) algorithms for all generated flashcards and clinical vignettes.
- Enforce strict pointer-only output for proprietary textbooks: the API emits original semantic synthesis and structured fact triples accompanied by `(Book, Edition, Chapter, Page)` verification pointers, strictly omitting verbatim copyrighted prose excerpts.
- Indian national clinical guidelines (ICMR, NTEP, MoHFW, WHO) are integrated as primary authoritative sources for clinical therapeutics and public health protocols, flagged with dedicated visual guideline badges.
- Strict adherence to Indian DPDP 2025: mandatory age gating for under-18 learners, zero third-party tracking scripts, and client-side PII sanitization.

## Testing Decisions

### What Makes a Good Test
Tests must evaluate external system behavior and observable contracts, never internal implementation details or private component state. A good test simulates real user inputs (such as submitting a chat prompt or clicking a 3D mesh) and verifies the observable output (such as emitted SSE event streams, rendered DOM elements, or state transitions).

### Primary Testing Seams

#### 1. The Gateway API & SSE Event Seam (Backend)
- **Scope:** Integration tests against FastAPI endpoints using `httpx.AsyncClient`.
- **Verified Behaviors:**
  - Submitting a clinical query to `/api/chat/stream` produces valid SSE streams containing both text tokens and syntactically valid `SpatialAction` payloads.
  - Querying `/api/spatial/resolve` with an FMA ID returns certified textbook pointers and related conditions without leaking copyrighted text.
  - Mereological traversal successfully maps granular clinical structures (e.g. coronary artery branches) to visible parent meshes.

#### 2. The Reactive State & Component Interaction Seam (Frontend)
- **Scope:** Client-side integration tests using React Testing Library and Vitest.
- **Verified Behaviors:**
  - Dispatching a mesh click event updates the Zustand store and renders the clinical profile drawer with correct citations.
  - Receiving a spatial action event (`highlight`, `camera`) properly updates viewport state without re-mounting the Three.js canvas.
  - Offline sync verifies that cached geometry and FSRS card decks load successfully from IndexedDB when network requests fail.

### Prior Art
- Existing unit tests in `med-rag`: `tests/test_atlas.py` (verifies FMA name/label resolution and variant lookups), `tests/test_answer.py` (verifies RAG answer generation and citation formats), and `eval/heading_metrics.py`.
- Upstream tests in `human-atlas`: `app/agent-tools.ts` (verifies programmatic tool execution over the anatomical catalogue).

## Out of Scope
1. Full 19-subject video lecture streaming or video player hosting.
2. Direct integration with electronic health record (EHR) systems or live patient bedside ward assistance.
3. Multimodal Vision-Language Model (VLM) image-based question answering for radiology/histology (deferred to Phase 4 / Pro tier).
4. Native iOS/Android app store wrappers (the primary deployment target is a standards-compliant mobile PWA).
5. Voice-driven conversational OSCE standardized patient simulators.

## Further Notes
- Upstream 3D geometry is sourced from DBCLS BodyParts3D 4.0 under the Creative Commons Attribution 4.0 International license (CC BY 4.0); attribution is permanently retained in application metadata and UI footer disclosures.
- DeepSeek-V4-Flash and DeepSeek-V4-Pro with prompt prefix caching are designated as the primary inference engines, maintaining blended compute costs within ₹3.37–₹4.87 per monthly active user.
