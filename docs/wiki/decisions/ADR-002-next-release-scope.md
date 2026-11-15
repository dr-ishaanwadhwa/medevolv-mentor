# ADR-002: Next release scope (after the 17 Nov 2026 demo)

| | |
|---|---|
| Date | 2026-11-15 |
| Status | **Proposed**. Nothing is approved, built or deployed. The user decides OQ-8 (v2 freeze) and OQ-1 (public landing) first |
| Repo state | `main` @ `e0eec26` |
| Spec | [Next release PRD](../../prd/2026-11-15-next-release-prd.md) |
| Evidence | [Code audit](../research/2026-11-15-next-release-code-audit.md) · [YouTube related videos](../research/2026-11-15-youtube-related-videos.md) · [Female 3D models](../research/2026-11-15-female-anatomy-3d-models.md) · [Strategy review](../../strategy_review_2026-11-14.md) |

## Context
The user asked for six things: a three.js landing page at `/` that shows a medical student what Mentor is for, a flowchart maker on answers, YouTube video suggestions after answers, tooltips on every button, an atlas "Reset view" that really resets, and a female 3D anatomy model.

The evidence shaped the scope:
- **Reset view is a confirmed bug.** It only turns Isolate off and re-frames the current selection (`AtlasView.tsx:194`, `atlas-store.ts:61`, `AtlasScene.tsx:502-506`) [audit E].
- **Flowcharts** exist only in the old Streamlit app (`rag/diagrams.py`, ontology `case`/`drug` subjects only). Ontology sources are numbered separately from answer citations, so reusing them naively would misattribute evidence [audit B; PRD review ENG-1, TP-3].
- **YouTube**: the official Data API v3 allows about 100 uncached searches a day at default quota. API data may be stored for at most 30 days. Scraping is not allowed, and `relatedToVideoId` no longer works [yt §1-§5].
- **Tooltips**: there is no primitive, and about 67 of about 82 control sites have no label. This is an approximate regex count [audit D].
- **Female model**: the only open, segmented candidate is HRA Visible Human Female v1.5 (CC BY 4.0, 202 MB GLB). Its skeleton and muscles are partial, and it has no external genitalia [fem §1, §3.1].
- **No model credit is shown in the v2 app today**, although CC BY meshes are already served (checked at `e0eec26`).
- **The strategy review** says to "Freeze v2, the 3D atlas and graph expansion until pilot data shows repeat use". It also says the 12/18 patient-specific drug-advice leak "blocks any public growth", and that the safety gate "must pass before anything public or paid" (strategy §1 "Next 90 days" item 4, line 81; §6 lines 381 and 399).

## Decision (proposed)
1. **Nothing ships before the 17 Nov demo.** Even R4 (Reset view) waits unless the user says yes (OQ-4).
2. **One freeze decision covers the whole release (OQ-8).** Recommended: lift it now only for the trust fixes and small items: R4 Reset with Undo, C1 model credits, the R3 tooltips with their baseline check, and the proxy-header and rate-limit fix. Decide on R1, R2, the landing and R5 when pilot repeat-use data arrives.
3. **Order, if lifted:**
   - P0: foundation (R4, C1, R3, flags file, events, rate limiter).
   - P1: `/privacy` and `/terms`, the `/ask` alias, R1 flowcharts and R2 videos.
   - P2: the landing, with `/` switching to it in the same deploy.
   - P3: the female atlas.
4. **Flowcharts keep cite-or-decline.**
   - Path order: a certified ontology path, used only when the answer covers the same subject, then an LLM path that restructures the answer, then a helpful decline.
   - Every node and every edge carries a namespaced citation (passage `[n]` or fact `F`/`[G#]`), checked by a deterministic validator (V1-V6, E1-E5).
   - Requests are HMAC-signed, run under timeouts and daily caps, and return versioned JSON rendered with dagre and React SVG.
5. **Videos stay outside the textbook contract.**
   - They render in a separate section after the answer article, with an honest label and YouTube's attribution.
   - The query comes from a structured topic label only, never from the question text.
   - YouTube data is held only in a 7-day cache, purged at 14 days. Shared answers store only the topic.
   - `/privacy` and `/terms` must exist first.
   - Searches degrade to a plain search link at 80 per rolling 24 h.
6. **Tooltips**: the `tip` prop starts optional. `check:tips` runs inside `pnpm check` (not `next lint`) against a shrinking baseline, and `tip` becomes required once the baseline is empty. Touch devices get coach marks on the five non-obvious controls.
7. **Landing**:
   - Five scenes. The hero is a server-rendered answer card with page pointers and a coverage strip. "Why was I wrong?" comes second.
   - It uses a new exam-style recorded journey, not the patient-management pheochromocytoma one.
   - It runs in `pilot` copy mode, gated and noindex, until the rights decision and the safety gate (OQ-1).
   - The chiasm scene loads a pre-extracted `chiasm.bin`. The atlas path measured about 3.7 MB, over the 3 MB budget.
8. **Female atlas**: a "Male | Female (organs)" switch. The two models are never mixed in one scene. The student confirms before the download starts. Manifest caches are kept per sex. Files ship through the human-atlas build, and crosswalk rows ship through an eka-app rebuild.
9. **Feature flags** live in a VM JSON file outside the deploy rsync, read by `/api/features`. Flags are off at deploy and flipped after the smoke test, because there is no staging host.

## Alternatives considered
- **Lift the whole freeze now (OQ-8 A).** Faster, but it contradicts the strategy review before any pilot data exists. Offered to the user, not recommended.
- **Mermaid or Graphviz WASM for diagrams.** Mermaid parses markup that the LLM would write (an injection risk), and both add bundle or WASM weight. Rejected in favour of a JSON graph with dagre.
- **Scraping, yt-dlp, Invidious or Piped for videos.** Not allowed by YouTube's ToS [yt §3]. Rejected.
- **Saving the video list in shared answers.** That would store YouTube data past 30 days in the `answers` table. Rejected.
- **Making `tip` required on day one.** Roughly 70 call sites would break the type check at once. Rejected for the staged baseline.
- **A fully public landing with the "Your textbooks, answering back" headline.** Blocked by the rights and safety positions. Kept as `public` mode behind OQ-1.
- **Other female models** (Z-Anatomy, commercial sets, NIH 3D single organs). Rejected on licence or coverage grounds [fem §1-§3].

## Consequences
- **Positive:** every new surface strengthens the trust promise: cited boxes and arrows, labelled external videos, credits shown, honest declines. The existing CC BY credit gap closes first. Reset matches what students expect. The plan can proceed whichever way OQ-8 goes.
- **Costs:** about 25.5-33 working days for one workstream with no buffer (PRD §1.2). New dependencies, each needing the user's yes: dagre; Playwright and Lighthouse; `@gltf-transform/core` (build only); a YouTube API key; the 202 MB female GLB download.
- **Risks carried:** diagram decline rates for anatomy topics are unknown until the offline eval. The female model's units, axes and credit title are unverified. YouTube clause readings come from summaries and need a verbatim re-read. DPDP and minors obligations are open (OQ-15).
- **Follow-ups:** separate ADRs for diagram grounding and for the landing route once built (PRD §5.7). `/how` still replays the patient journey (OQ-16).

## Related pages
- [Engineering Principles](../standards/engineering-principles.md)
- [ADR-001 Unified AI-Native Architecture](ADR-001-unified-ai-native-architecture.md)
- [Spatial-Semantic Bridge](../subsystems/spatial-semantic-bridge.md)
