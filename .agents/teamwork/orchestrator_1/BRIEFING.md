# BRIEFING — 2026-11-13T08:58:42Z

## Mission
Implement the unified AI-native production platform integrating med-rag (MedEvolv Mentor) and med-rag-atlas per docs/ATLAS_INTEGRATION_SPEC.md.

## 🔒 My Identity
- Archetype: teamwork_orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/orchestrator_1/
- Original parent: caller
- Original parent conversation ID: ac4db067-eae1-4782-ad74-ebcfd8193682

## 🔒 My Workflow
- **Pattern**: Project Pattern
- **Scope document**: /Users/ishaanwadhwa/Projects/med-rag/PROJECT.md
1. **Decompose**: Step 0 Survey (3 Explorers / Spec Miners) -> Decompose into 3-7 milestones + E2E Testing Track -> Dispatch sub-orchestrators
2. **Dispatch & Execute**:
   - **Delegate (sub-orchestrator)**: For each milestone, spawn sub-orchestrator
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: Project Orchestrator has no parent to escalate technical decisions to — must redesign
4. **Succession**: Self-succeed at 16 spawns
- **Work items**:
  1. Survey & Architecture Mapping [in-progress]
  2. PROJECT.md & TEST_INFRA.md Formulation [pending]
  3. Milestone Decomposition & Dispatch [pending]
- **Current phase**: 0 (Survey)
- **Current focus**: Step 0 Survey (map full scope from docs/ATLAS_INTEGRATION_SPEC.md and existing repo)

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- File-editing tools ONLY for metadata/state files (.md) in .agents/teamwork/ (and PROJECT.md at root).
- If Forensic Auditor reports INTEGRITY VIOLATION, milestone FAILS UNCONDITIONALLY.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.
- Always include path to ORIGINAL_REQUEST.md in every subagent dispatch.

## Current Parent
- Conversation ID: ac4db067-eae1-4782-ad74-ebcfd8193682
- Updated: 2026-11-13T08:58:42Z

## Key Decisions Made
- Selected Project Pattern with Dual Track (Implementation Track + E2E Testing Track).
- Starting Step 0 Survey with 3 Explorers / Spec Miners:
  1. Spec Miner on docs/ATLAS_INTEGRATION_SPEC.md (exact requirements, API contracts, FMA/BODHI schema, FSRS-5, Three.js specs)
  2. Explorer on Backend & KG (existing med-rag python codebase, Streamlit app, clinical graph, embeddings, rag pipeline)
  3. Explorer on Frontend & 3D Assets (med-rag-atlas, human-atlas, Three.js shaders/DataTexture, Next.js setup)

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| spec_miner_1 | teamwork_spec_miner | Spec Requirements Mining | completed | 9e74d7a9-8892-402b-a9a8-7d029b68e5b5 |
| explorer_backend_1 | teamwork_explorer | Backend & KG Survey | completed | 1cc366e4-3c1a-4bcf-97e8-8568b09b2620 |
| explorer_frontend_1 | teamwork_explorer | Frontend & 3D WebGL Survey | completed | d6593d92-79ce-43c0-a893-1d9850c7cdd8 |
| worker_m1_1 | teamwork_worker | M1 KG & Mereology Traversal | in-progress | 0b89a9c5-670c-443d-9fac-7230b0ca60ce |
| test_writer_e2e_1 | teamwork_test_writer | E2E Testing Suite (Tiers 1-4) | in-progress | 65ff93bc-ec6c-419b-b8a8-5173f5ed5319 |
| worker_m4_1 | teamwork_worker | M4 Frontend Workspace & 3D Canvas | in-progress | f0695b5c-0a90-4848-b523-f7ef2c78f568 |

## Succession Status
- Succession required: no
- Spawn count: 6 / 16
- Pending subagents: 0b89a9c5-670c-443d-9fac-7230b0ca60ce, 65ff93bc-ec6c-419b-b8a8-5173f5ed5319, f0695b5c-0a90-4848-b523-f7ef2c78f568
- Predecessor: none
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 374680d6-856a-4138-9979-f33b00b59dea/task-17
- Safety timer: 374680d6-856a-4138-9979-f33b00b59dea/task-102
- On succession: kill all timers before spawning successor
- On context truncation: handle timers as step 4 of the State Recovery section of your prompt says

## Artifact Index
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/ORIGINAL_REQUEST.md — immutable user request
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/orchestrator_1/DISPATCH.md — dispatch log
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/orchestrator_1/BRIEFING.md — working memory
- /Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/orchestrator_1/progress.md — progress tracker & heartbeat
