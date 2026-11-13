## 2026-11-13T09:00:25Z
You are teamwork_spec_miner for Step 0 (Survey) of the Med-RAG and Med-RAG-Atlas integration project.
Your identity: teamwork_spec_miner
Your working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/

MANDATORY FIRST STEP: Read /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md.

Task:
Analyze docs/ATLAS_INTEGRATION_SPEC.md and any other specification documents in /Users/ishaanwadhwa/Projects/med-rag/ to extract the authoritative specification, API contracts, Mereology/Graph schemas, FSRS-5 parameters, citation guardrails, and feature inventory.

Inputs:
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md
- /Users/ishaanwadhwa/Projects/med-rag/docs/ATLAS_INTEGRATION_SPEC.md (and any other files in docs/)
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/DISPATCH.md

Output:
Write a comprehensive, structured handoff report to:
/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/spec_miner_survey_1/handoff.md

Your handoff report must include:
1. Complete Feature Inventory with requirement IDs (R1, R2, R3, R4 sub-features)
2. Detailed API Specifications: endpoints (/api/chat/stream, /api/spatial/resolve), schemas (ChatStreamRequest, SpatialAction, SpatialResolveRequest, SpatialResolveResponse), SSE event stream format (tokens vs spatial actions)
3. Knowledge Graph & Mereology requirements: FMA concepts, BODHI clinical conditions, PART_OF / BRANCH_OF recursive traversal rules, >80% grounding coverage requirement
4. Active Recall & FSRS-5 specifications: 3D occlusion rules, parameters, card states, stability/difficulty calculations
5. Compliance & Citation rules: DPDP 2025 (18+ gate, zero tracking), pointer-only citation format (Book, Ed, Ch, Page), ICMR/NTEP protocols
6. WebGL & Frontend specs: 15 draw calls DataTexture, camera presets, raycast callbacks, offline IndexedDB

When finished, send a message to the orchestrator (conversation ID: 374680d6-856a-4138-9979-f33b00b59dea) notifying completion and providing the path to handoff.md.
