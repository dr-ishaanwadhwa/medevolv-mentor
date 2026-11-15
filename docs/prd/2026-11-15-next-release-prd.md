# MedEvolv Mentor: next release plan and PRD

| | |
|---|---|
| Date | 2026-11-15 (revised the same day after four reviews; see the Review log at the end) |
| Status | **Draft** (nothing here is approved, built, committed or deployed) |
| Repo state | `main` @ `e0eec26` |
| Owners | **User** (product owner: approves scope, pushes, deploys, downloads, the YouTube key, copy). **Lead agent** (plans, reviews, integrates, runs gates). **Build workstreams** WS-A Atlas, WS-K UI kit, WS-X Answer extras, WS-L Landing (haiku/sonnet subagents; see 1.3) |
| Release window | After the 17 Nov 2026 demo, and only if the user lifts the strategy review's v2 freeze for this release (OQ-8). The only pre-demo candidate is the S-sized Reset-view fix, and only if the user says yes |
| Evidence base | [Code audit](../wiki/research/2026-11-15-next-release-code-audit.md) · [YouTube related videos](../wiki/research/2026-11-15-youtube-related-videos.md) · [Female 3D models](../wiki/research/2026-11-15-female-anatomy-3d-models.md) · [Engineering principles](../wiki/standards/engineering-principles.md) · [API README](../../api/README.md) · [Strategy review](../strategy_review_2026-11-14.md) · [Eval 2026-11-13](../eval_2026-11-13.md) |
| Decision record | [ADR-002 Next release scope](../wiki/decisions/ADR-002-next-release-scope.md) |

How to read this document. Facts carry their source in brackets, for example `[audit E]` (code audit, section E), `[yt §1]` (YouTube note), `[fem §3.1]` (female-models note), `[strategy §3]`, or a file path with line numbers at `e0eec26`. Anything we could not check is marked **ASSUMPTION**, **UNKNOWN** or **UNVERIFIED**. Numbers called "target" or "budget" are goals we are setting, not measurements. Effort figures are estimates. Where we made a choice between conflicting sources or reviewers, the text says "decision" and the Review log says why.

A short glossary for readers who are not medical:
- **MBBS**: the Indian undergraduate medical degree (about 5.5 years including internship). Exams come in "professional" stages: 1st prof (anatomy, physiology, biochemistry), 2nd prof (pathology, pharmacology, microbiology), 3rd prof (medicine, surgery and others).
- **Viva**: an oral exam where an examiner asks follow-up questions.
- **Cite-or-decline**: Mentor either answers with numbered citations pointing to book, chapter and page, or says "the books don't settle this". It never answers from the model's own memory.
- **Citation kinds**: answers cite two kinds of evidence: textbook passages `[n]` and certified graph facts `[G#]` (`rag/answer.py:150-158`, `:209`). Both appear in answer text.
- **Ontology**: our graph of quote-checked facts ("certified facts") linking conditions, drugs and structures. Its size is reported internally as about 26k facts at about 95% precision; that figure is **internal and unaudited** and could not be traced to a doc in `docs/` [strategy line 140, line 519]. This PRD does not rely on the number and the landing does not show it.
- **FMA id**: an id from the Foundational Model of Anatomy (for example `FMA62045`, optic chiasm). The 3D atlas, the answers and the concept pages all link through FMA ids [audit F].

---

## 1. Executive summary and plan

### 1.1 What ships, why, and in what order

This release adds five things the user asked for and one landing page, plus three trust fixes the reviews found (model credits, rate limiting behind the proxy, a Terms page). All of them serve the same promise: **a student can trust what Mentor shows, and can see quickly what it is for.**

**Precondition (strategy freeze).** The strategy review says: "Freeze v2, the 3D atlas and graph expansion until pilot data shows repeat use" [strategy line 81, §1 item 4]; "The 12/18 patient-specific drug-advice leak blocks any public growth" [strategy line 381]; and "SuperMe's safety gate must pass before anything public or paid" [strategy line 399]. Every item below is v2 expansion, and the landing is a public-growth surface. So the whole release, not only the female atlas, needs the user's explicit decision to lift or narrow the freeze (OQ-8), and a *public* landing additionally needs the safety gate and a rights decision (OQ-1). Until then this PRD is a plan, not a schedule.

| # | What | Why it matters to a student | Size |
|---|---|---|---|
| R4 | Atlas **Reset view** really resets (clears selection, frames the whole body), with Undo | Today it only turns Isolate off when a structure is selected. A confirmed bug [audit E] | S |
| C1 | **Model credits** (BodyParts3D now, HRA later) shown wherever a 3D mesh renders, plus a `/credits` page | The v2 app shows **no** BodyParts3D / CC BY credit today (checked at `e0eec26`: no match for `BodyParts|HuBMAP|CC BY|creativecommons|attribution` in `apps/web/src` or `apps/web/public`). CC BY 4.0 requires it | S |
| R3 | **Tooltips on every control** (purpose + effect) on hover and keyboard focus, touch coach marks for the non-obvious controls, and a check script that fails on new unlabelled controls | About 82 control sites, about 67 without a `title` or `aria-label` (audit regex count, approximate [audit D caveats]). New students do not know what "Isolate" or "Why was I wrong?" does | M |
| R1 | **"Make a flowchart"** on an answer: classification, pathway or sequence diagrams where every box and arrow traces to a citation or a certified fact, or the feature declines | Students revise from flowcharts and draw them in prof exams. Today diagrams exist only in the old Streamlit app [audit B] | L |
| R2 | **Suggested YouTube videos** after an answer, in a separate section, plus related topics from our ontology | Students already use YouTube lectures. We put some one tap away, clearly labelled as external and not checked | M |
| Landing | A three.js landing page at `/` that shows the product working; Ask moves to `/ask` | First-time visitors see what Mentor does for their exam and why it can be trusted, using real data (the 36,725-passage library) | L |
| R5 | A **Female** 3D atlas (HRA Visible Human Female organs, CC BY 4.0), behind a Male/Female switch | No female-specific anatomy exists in the atlas today ("no uterus" [audit F]) | L |

Order: fix and foundation first (R4, C1, R3 baseline, rate limiting and flags), then the two answer features (R1, R2) with `/privacy` and `/terms`, then the landing page (which shows R1/R2 only if live), then the female atlas (largest data job, needs a 202 MB download).

### 1.2 One-screen plan

```
            17 Nov demo (FREEZE: nothing ships before, except R4 if the user says yes)
            OQ-8: user decides whether the v2 freeze is lifted for this release
                 |
P0  foundation   |  R4 Reset view + Undo ...... WS-A  S  0.5 d
(18-21 Nov)      |  C1 Credits (/credits, mesh credit lines) WS-L  S  0.5 d
                 |  R3 Tooltip primitive (optional tip), tips/* registry,
                 |     check:tips + committed baseline ...... WS-K  M  2 d (re-estimated, §1.2a)
                 |  R3 sweep, shrinking the baseline ... WS-K  M  2 d (AtlasView after R4)
                 |  /api/features (flags file), /api/events, shared rate limiter,
                 |     --forwarded-allow-ips fix, route-size baseline  WS-X  S  1 d
                 |
P1  answer       |  /privacy + /terms ......... WS-L  S  1 d    (blocks R2 going live; moved from WS-X, §1.2a)
features         |  /ask alias (/ still chat) . WS-X  S  0.5 d  (sets mm_asked cookie from day one)
(22 Nov-3 Dec)   |  R1 Flowchart maker ........ WS-X  L  5-7 d  (ontology refactor, kinds, validator)
                 |  R2 Videos + related topics  WS-X  M  3-4 d  (needs YouTube key from user,
                 |                                        /privacy + /terms, channel list)
                 |
P2  landing      |  Captures: new journey, decline, why.json, chiasm.bin (user yes) WS-L 1 d
(3-12 Dec)       |  Landing three.js story .... WS-L  L  6-8 d
                 |  Switch / to landing + redirects + middleware  WS-L  S 0.5 d (same deploy as landing)
                 |
P3  female atlas |  Download GLB (user yes) ... user  -
(after P2)       |  Convert + id mapping ...... WS-A  L  2-3 d
                 |  Male/Female switch, ?sex= . WS-A  M  1-2 d  (builds on R4's reset semantics)
                 |  Deploy runbook: atlas push + eka-app crosswalk rebuild  WS-A  S  0.5-1 d
```

The dates in the block above are the draft's and are **superseded by §1.2a**, which re-dates the phases from per-workstream critical paths with a buffer and makes every date conditional on OQ-8. Effort is working days for one agent workstream, estimated from the audit's sizes [audit summary table], the female note's estimate [fem §5] and the extra scope the reviews added. **Sum of the listed estimates: P0 5 d + P1 9.5-12.5 d + P2 7.5-9.5 d + P3 3.5-6 d = 25.5-33 working days**, before the re-estimates in §1.2a. **ASSUMPTION**: one workstream runs at a time on shared files (see 1.3), so the calendar is longer than the sum where files overlap.

Dependencies that matter:
1. OQ-8 (freeze) is answered before any build work starts.
2. R3's `tip` prop (optional at first) and the per-feature tip files must exist before R1/R2/Landing add new buttons, so those buttons are born with tooltips (pit of success). `check:tips` fails on any *new* unlabelled control from the first day, using a committed baseline of known gaps.
3. R2 cannot go live before `/privacy` and `/terms` exist (YouTube API policy III.A.1 and III.A.2 [yt §2]) and before the user supplies a key.
4. The landing page's "make it yours" scene needs R1/R2 live; if they are not, that scene is left out on the server, never shown as "coming soon".
5. R5 needs R4 (Reset must reset per model), the user's yes on the 202 MB download, and a deploy runbook for both the atlas files and the crosswalk rebuild.
6. `/` switches from chat to the landing **in the same deploy** as the landing and the `/?q=` redirect [audit A]. Before that, `/ask` is an alias and `/` stays the chat, so there is never a blank or half-built `/`.

### 1.2a Schedule from critical paths (conditional on OQ-8)

The draft calendar loaded one workstream per phase onto fixed dates: P1 (22 Nov-3 Dec, 9 working days) gave WS-X 9.5-12.5 d; P2 (3-12 Dec, 7 working days) gave WS-L 7.5-9.5 d; P0 (18-21 Nov, 3 working days: Wed 18 to Fri 20) gave WS-K 3 d of serial work with the AtlasView sweep blocked on R4. None of those fit, and the dates also contradicted OQ-8's recommended answer (B), under which R1, R2, the landing and R5 wait for pilot repeat-use data. Dates are therefore stated as **working-day offsets from a trigger**, with a **25% buffer** on each workstream's critical path (a buffer we set; no measured velocity exists). **ASSUMPTION**: one agent per workstream, no team leave, user approvals (G5) answered within one working day; each late approval moves the dates one-for-one.

Re-estimates used below (changes from §1.2): R3 primitive + `CoachMark` + `check-tips.mjs` (TypeScript compiler API, fixtures, baseline) + Markdown delegated tooltips is **M, 2 d** (was 1 d); WS-K also adds an `action` to the toast (0.25 d, §4.4); `/privacy` + `/terms` move from WS-X to **WS-L** (WS-L has no other P1 work, and this shortens WS-X's path); `api/safety_cues.py` is 0.5 d on WS-X; the landing hallway test (§4.L) is 0.5 d on WS-L.

| Phase | Trigger (start) | Critical path (workstream, estimate, with 25% buffer) | Other workstreams in parallel | Example dates if the trigger is 17 Nov |
|---|---|---|---|---|
| P0 | The working day after the 17 Nov demo; runs under **every** OQ-8 answer (A, B and C all include R4, C1, R3 and the proxy fix) | WS-K: primitive 2 d + toast action 0.25 d + sweep 2 d = 4.25 d → **about 5.5 working days**. The AtlasView part of the sweep is not on the path: WS-A does it right after R4 on day 1 | WS-A: R4 0.5 d + atlas tips 0.25 d + C1 atlas/`Concept3D` credit lines 0.25 d (≈1.5 d buffered, after WS-K's toast action). WS-X: flags, events, limiter, proxy fix 1 d (≈1.5 d). WS-L: C1 `/credits`, shell link, `/how` credit line (≈1 d). Lead: `package.json` scripts and the unit test runner (§5.5) | Wed 18 Nov to Wed 25 Nov; deploy after G1-G6 and the user's yes |
| **Hold point (OQ-8 = B, recommended)** | P0 shipped | Nothing further is scheduled. R1, R2, the landing and R5 resume only when the user answers OQ-8 again with pilot repeat-use data in hand. The trigger for P1 is that answer, not a date | Optional under OQ-8 = C: WS-A runs the P3 offline steps (download after the user's yes, converter, id map), no ship | none: this is the default plan |
| P1 + P2 (run in parallel) | The working day after **OQ-8 = A** is recorded **and** P0's G6 passes, whichever is later (day N) | WS-X: `/ask` alias 0.5 d + `safety_cues.py` 0.5 d + R1 5-7 d + R2 3-4 d = 9-12 d → **about 11.5-15 working days** | WS-L: `/privacy` + `/terms` 1 d first (they block R2 going live), then captures 1 d, landing scenes 0-3 and the static fallback, hallway test 0.5 d; scene 4's "make it yours" half waits for R1/R2 to be live; switch `/` in the same deploy as the landing. 1 + 1 + 6-8 + 0.5 + 0.5 = 9-11 d → about 11.5-14 working days. Files are disjoint per §1.3 (WS-L edits `ChatView.tsx:81` only in the switch) | N = 26 Nov: R1 + R2 done between 11 Dec and 16 Dec; the landing switch the next deploy after both are live (about 17 Dec) |
| P3 | Ship: after the landing switch. Build: may start at day N (WS-A has no P1/P2 work) | WS-A: convert + id map 2-3 d + switch 1-2 d + runbook 0.5-1 d = 3.5-6 d → **about 4.5-7.5 working days**, plus the named reviewer's time (§4.5) | none | Built in parallel from 26 Nov; shipped after the landing, about 18 Dec |

Option to shorten P1 (not the default): split R2 into its own workstream (`api/videos.py`, `Videos.tsx`, `RelatedTopics.tsx`, `test_api_videos.py`), with its edits to `AnswerCard.tsx`, `store/chat.ts` and `api/main.py` requested through WS-X. That brings WS-X's path to about 7.5-10 working days at the cost of more hand-offs on hotspot files.

### 1.3 Workstreams and file ownership

One owner per file at a time avoids merge conflicts between parallel subagents.

| Workstream | Agent | Owns (writes) | Reads only |
|---|---|---|---|
| WS-A Atlas | sonnet | `web/components/canvas/AtlasView.tsx`, `AtlasScene.tsx`, `web/lib/atlas-store.ts`, `web/lib/anatomy.ts`, `web/lib/format.ts` (`atlasHref`), `web/components/explore/Concept3D.tsx`, `web/components/story/chiasm.ts` (sex-aware URL only), new `web/lib/tips/atlas.ts`, `deploy/atlas/*`, new `deploy/atlas/female/*`, `rag/atlas.py`, `api/spatial.py`, `scripts/build_atlas_crosswalk.py`, `tests/test_crosswalk.py`; in P3, `api/schemas.py` (`SpatialAction.sex`) by hand-over from WS-X | crosswalk data |
| WS-K UI kit | sonnet for the primitive, haiku for the sweep | `web/components/ui/*` (new `Tooltip.tsx`, `CoachMark.tsx`), new `web/lib/tips/index.ts` + `tips/shell.ts`, `tips/why.ts`, `tips/explore.ts`, `tips/story.ts`, new `apps/web/scripts/check-tips.mjs` and `apps/web/scripts/tips-baseline.json`, then every call site in the audit's D table **except** files another workstream owns at that moment | |
| WS-X Answer extras | sonnet | new `api/diagram.py`, `api/videos.py`, `api/events.py`, `api/features.py`, `api/ratelimit.py`; `api/main.py` (route registration), `api/schemas.py` (until P3 hand-over), `rag/diagrams.py` (the `_Dot` refactor); `web/lib/api.ts`; `web/store/chat.ts`; new `web/components/chat/Diagram.tsx`, `Videos.tsx`, `RelatedTopics.tsx`; `AnswerCard.tsx`, `SharedAnswer.tsx` (including the `:87` href change), `Actions.tsx`; new `web/lib/tips/answer.ts`; new `web/app/ask/page.tsx` (alias) (`/privacy` and `/terms` moved to WS-L, see below); `deploy/v2/push.sh`, `deploy/v2/Dockerfile.api`, `deploy/v2/docker-compose.yml`; tests `tests/test_api_diagram.py`, `tests/test_api_videos.py`, `tests/test_api_events.py`, `tests/test_ratelimit.py` | `rag/ontology*`, `rag/answer.py` |
| WS-L Landing | sonnet | `web/app/page.tsx`, new `web/middleware.ts`, new `web/components/landing/*`, new `web/lib/tips/landing.ts`, new `web/app/credits/page.tsx`, new `web/app/privacy/page.tsx` and `web/app/terms/page.tsx` (P1), new `web/components/credits/*`, `web/components/shell/nav.ts`, `AppShell.tsx` (logo links, credits link, CTA offset), `VerdictCard.tsx:13`, `ChatView.tsx:81`, `HowClassic.tsx:116`, `Story.tsx:243`, `not-found.tsx:9`, `next.config.mjs` | `web/components/story/*` (imports `palette.ts`, `shaders.ts`, `math.ts`, `engine.ts`, `data.ts` as they are; does **not** edit `controller.ts`). Any edit to a story file needs the `/how` visual QA in G2 |
| Lead agent | opus | this PRD, wiki pages, gate runs, review | everything |

**Files not covered above (added in the completeness pass).** Each has one owner; "lead" means the lead agent.

| File | Owner | Notes |
|---|---|---|
| `apps/web/package.json`, `pnpm-lock.yaml` | **Lead** | Hotspot: WS-K needs `check`/`check:tips` scripts, WS-X needs `@dagrejs/dagre`, the lead adds the unit runner script and Playwright (if OQ-12 = yes). Workstreams **request** script or dependency changes from the lead; nobody else edits these two files |
| `api/safety_cues.py`, `tests/test_safety_cues.py` | WS-X (P1) | Used by R1, R2 and the landing's question picks; WS-L reads only |
| `scripts/build_landing_captures.py`, `scripts/extract_chiasm.mjs`, `public/landing/*` | WS-L (P2) | Capture run needs the user's yes |
| `shared/copy/videos.json`, `web/lib/copy/videos.ts`, `web/lib/copy/diagram.ts` | WS-X (P1) | One copy source for the API `label` and the UI; the diagram reason-to-copy map |
| `web/lib/features.ts`, `web/components/FeaturesProvider.tsx`, the provider line in `web/app/layout.tsx` | WS-X (P0, with `/api/features`) | Read by WS-L (landing), WS-A (`female_atlas`) |
| `api/data/video_channels.json`, `api/data/video_blocklist.json` | WS-X (structure, loader, tests); channel ids added by the named verifier (OQ-11) through the lead | |
| `apps/web/e2e/*`, `apps/web/playwright.config.ts`, `apps/web/e2e/README.md` | Lead (config, README); each spec by its feature's workstream (`atlas-reset.spec.ts` WS-A, redirect spec WS-L, tooltip spec WS-K, female spec WS-A) | Only if OQ-12 = yes |
| Web unit tests `apps/web/src/**/*.test.ts` | Each feature's workstream for its own module; runner wiring by the lead (§5.5) | |
| `tests/test_api_v2.py` (new `topic` event ordering test) | WS-X (P1) | |
| `api/README.md` | WS-X (endpoints and SSE events it adds); lead reviews | WS-A sends its `/api/spatial/resolve` `sex` note to WS-X in P3 |
| `deploy/atlas/build_atlas.sh`, `deploy/atlas/push_atlas.sh`, `deploy/atlas/ATTRIBUTION.md`, `deploy/atlas/README.md` | WS-A | Already under `deploy/atlas/*`; listed for clarity |
| `apps/web/scripts/fetch-models.sh` | WS-A | Edited only if the E2E recipe needs it |
| `web/store/ui.ts` (toast `action`) and `web/components/ui/Toast.tsx` | WS-K (P0, before R4) | R4's Undo needs it (§4.4) |
| `web/lib/atlas-reset.ts` (pure reset helper, §5.5) and its unit test | WS-A | |
| C1 credit lines in `AtlasView.tsx` and `Concept3D.tsx` | **WS-A**, right after R4 in P0 | WS-L writes the shared `<ModelCredit>` component in `web/components/credits/` first; WS-A only places it |
| C1 credit line on `/how` near the chiasm | **WS-L**, with the `/how` visual QA (G2) | The one allowed story-file edit for C1 |
| `/privacy`, `/terms` pages | **WS-L** (moved from WS-X, §1.2a) | WS-X supplies the YouTube and diagram-cache lines |
| `mm_asked` cookie write | **WS-X**, in `web/store/chat.ts` when the first answer of the browser reaches `done` | WS-L's middleware reads it |
| Videos section placement | **WS-X** renders `<Videos>` as the sibling `<section>` right after the answer `<article>` from `AnswerCard.tsx` (inside the turn wrapper, outside the article) | `ChatView.tsx` (WS-L) is not edited for this |

Conflict rules:
- `AnswerCard.tsx`: WS-K sweeps it first in P0; WS-X owns it from P1 and adds tips itself.
- `AtlasView.tsx`: R4 (WS-A) lands first; WS-A then adds the atlas toolbar tips itself (`tips/atlas.ts`), so the WS-K sweep skips it.
- `Concept3D.tsx`: WS-A adds its tips.
- Tip copy is split per feature (`web/lib/tips/<feature>.ts`, re-exported by `tips/index.ts`), so each workstream appends only to its own file.

### 1.4 Release gates (every phase)

| Gate | Passes when | Who |
|---|---|---|
| G1 Tests | `pytest -q` green (including new API tests); `pnpm --dir apps/web check` (now `tsc --noEmit && node scripts/check-tips.mjs`), `pnpm --dir apps/web test:unit` (§5.5) and `pnpm --dir apps/web build` green; Playwright specs when OQ-12 = yes; `check-tips.mjs` reports no gaps beyond the committed baseline, and an empty baseline at release | agent |
| G2 Browser QA | Manual pass at 390 px and 1440 px, light and dark, plus `prefers-reduced-motion`, on a local production build; VoiceOver (macOS/iOS) spot check, TalkBack if a device is available; `/how` checked whenever a story file changed; screenshots attached to the PR | agent, reviewed by user |
| G3 Budgets | The performance budgets in §5.2 met, measured from `next build` output, the network panel and a Lighthouse mobile run (Lighthouse is an `npx` download, approval in OQ-12) | agent |
| G4 Honesty and safety | Every number on screen traces to a named data or eval file, with its caveats in the same constants file; external content labelled; decline paths tested; every page that renders a mesh shows or links the credit for that model; the study-aid line is present on diagrams and exports; no diagram or videos on patient-scoped questions | lead agent + user |
| G5 Approval | User says yes to the push/deploy (and to any download, key setup, DeepSeek capture run or book-title display decision) | user |
| G6 Live smoke | After deploy: `/api/health` ok; one question end to end; `GET /api/features` returns the intended flag values; old `/?q=` link works; `request.client.host` logging shows real client IPs (rate-limit check) | agent |

Standing rule: nothing is pushed, deployed or downloaded without the user's yes.

---

## 2. Goals, non-goals, success metrics

### 2.1 Goals
1. A first-time student understands, within the first screen, what Mentor does for their exam (a cited answer with page pointers), and within one scroll why it can be trusted (honest declines, why-was-I-wrong, body and books linked).
2. Every control explains itself on hover and keyboard focus; on touch, the non-obvious controls explain themselves once through coach marks.
3. An answer can become a flowchart without weakening cite-or-decline.
4. An answer can lead to external videos, clearly marked as outside the textbook contract.
5. The atlas behaves as students expect (Reset resets, with Undo) and covers female organs where an open model allows, with credits shown.

### 2.2 Non-goals
- No new medical content sources inside answers. Videos never feed the answer.
- No accounts, payments, password gate design or Hinglish in this release (accounts and gating are separate strategy items [strategy §1, B3]).
- No i18n.
- No embedded YouTube player (we link out) [yt §1 params].
- No full female twin of BodyParts3D. The HRA female set has partial skeleton and muscle [fem §1].
- No change to retrieval, ranking or the answer prompt.
- No fix to the patient-specific drug-advice leak itself (that is the strategy's safety gate); this release only avoids adding surfaces that amplify it.

### 2.3 Success metrics

There is no analytics today. The only usage signal is `POST /api/feedback` (kinds `wrong_citation | unhelpful | other`) and the `answers` table for shared answers [api/README.md]. So every baseline below is **UNKNOWN** until P0 adds a tiny first-party event counter (§5.3). Targets are ours to set and are marked as such. **Counting rule**: each event fires at most once per page load (a `sessionStorage` guard per event name), so ratios below are ratios of deduplicated daily counts, not per-person rates. Counts are anonymous and can be inflated by a script; treat them as rough signals.

| Metric | Definition | How measured | Baseline | Target (ours, revisit after 2 weeks of data) |
|---|---|---|---|---|
| Landing to Ask | `landing_cta` / `landing_view` (deduplicated daily counts) | events | UNKNOWN | Set after 2 weeks |
| First question | `question_sent_from_landing` / `ask_from_landing` (a `sessionStorage` `from_landing` marker set by the landing CTA) | events (no question text logged) | UNKNOWN | Set after 2 weeks |
| Diagram yield | `diagram_ok` / `diagram_request`, reported by `kind` | events | n/a (new) | Report, no target until we see it |
| Diagram trust | `diagram_wrong` reports per 100 `diagram_ok` | feedback | n/a | Every report read by the team |
| Video usefulness | `video_click` / `videos_shown` | events | n/a | Report |
| Video fallback rate | Answers where only the "Search YouTube" link showed | `source: fallback` counted server-side | n/a | Below 50% after a week of cache warm-up (target) |
| YouTube quota | `search.list` calls in any rolling 24 h | server counter | 0 | Under 80 (the degrade point [yt §6]) |
| Tooltip coverage | Entries in `tips-baseline.json` | `check-tips.mjs` | About 67 sites (audit regex count, approximate [audit D]); the script's first run is the real baseline | 0 |
| Reset correctness | Reset leaves no `?select=` and sets the whole-body goal pose | automated browser check (§4.4) | Fails today [audit E] | Passes |
| Female atlas use | Share of atlas page loads that switch to Female | `atlas_sex_switch` | n/a | Report |
| Performance | LCP, JS on `/`, `/ask`, `/how`, `/atlas` | Lighthouse mobile, `next build` route table | Route sizes are measurable today; recorded in P0 | §5.2 budgets |

---

## 3. Personas and jobs to be done

These are drawn from the strategy review's target user [strategy §3]. We have **no** user research data yet; the questionnaire in `docs/gtm/02_student_questionnaire.md` is planned for 20 Nov [strategy decision brief]. Treat the personas as hypotheses. Some 1st-prof students are under 18 (ASSUMPTION based on typical entry age; see OQ-15).

**P1. Preclinical student (1st and 2nd prof).** Studies anatomy, physiology, then pathology, pharmacology, microbiology from Gray's, Guyton, Robbins, Tripathi and *Essentials of Medical Microbiology*. Biochemistry has **no** book in the library today (`story.json` lists 7 books). Exam style: long answers, short notes, vivas, MCQs, drawn diagrams (classifications, pathways, cascades). Often on a phone, often on mobile data (ASSUMPTION, to confirm in the questionnaire).
- "When I revise a topic the night before a viva, I want a quick flowchart I can trust, so I can recall the sequence under questioning." (R1)
- "When I can't picture where a structure is, I want to see it in 3D and get back to the full body easily." (R4, R5)
- "When a textbook paragraph doesn't click, I want a short lecture video on exactly this topic, without trawling YouTube." (R2)

**P2. Clinical student (3rd prof and interns).** Studies medicine from Davidson and Harrison; does case-based questions and MCQs; later NEET-PG.
- "When I get an MCQ wrong, I want to know why, with the page, so I fix my understanding." (existing Why was I wrong?, the landing's lead feature)
- "When I study a condition, I want the workup and treatment as a revision flowchart with sources." (R1; the ontology `case` flowchart models condition, presentation, differentials, workup, treatment [audit B]; framed as exam revision, never as patient decisions)

**P3. First-time visitor (either of the above, arriving from a shared link or a friend).**
- "Before I trust this, I want to see that it shows its sources, admits when it doesn't know, and covers my subject." (Landing)

**P4. Female-anatomy learner (any year).** Studies the pelvis, uterus, ovaries and breast for anatomy. There is no OBG textbook in the library, so answers on these organs come only from Gray's, Guyton, Robbins, Davidson and Harrison.
- "When I study the female pelvis, I want a 3D model, not the male one." (R5)

---

## 4. Requirements

Each section: problem, UX, functional requirements (FR, numbered and testable), API, data and licensing, honesty rules, acceptance criteria, tests, risks, open questions.

Common UX rules for all sections (apply unless a section overrides):
- Mobile first at 390 px wide; desktop checked at 1440 px.
- Light and dark themes via existing tokens (`bg-surface`, `text-ink`, `text-muted`, `accent`; see `ui/Button.tsx`). Theme follows `prefers-color-scheme`, as today.
- `prefers-reduced-motion: reduce` turns off non-essential animation; the existing story already honours it (`CountUp` in `Story.tsx`).
- Touch targets at least 44 px for primary controls (the kit's `md` size is 44 px: `ui/Button.tsx` comment).
- All new controls use the kit (`Button`, `LinkButton`, `Chip`) with a `tip` (R3).
- **Safety framing**: no new surface (diagram, videos, landing scene) is offered for a patient-scoped question. "Patient-scoped" = `rag.answer._guard(question)` is true (`rag/answer.py:73`) **or** a small patient-cue check (`patient`, `my mother`, `I have`, `should I take`, a dose question, and similar; list kept in `api/safety_cues.py` with tests). This is a filter on our new features, not the safety gate itself.

---

### 4.L Landing page at `/` (and Ask moves to `/ask`)

#### Problem and user story
Today `/` is the chat [audit A: `web/app/page.tsx:1-5`]. A first-time student lands in an empty chat box with no idea what makes Mentor different from a free chatbot. The `/how` story explains the *pipeline* (for curious people and professors); the landing must show a *student* the **utility** (what it does for my exam) and the **potential** (what more it can do), and make them want to ask a first question.

> As a first-time MBBS student, I want to see in under a minute what Mentor can do for my studies, whether it covers my subject, and why its answers can be trusted, so that I ask my first question.

#### Gate and copy variants (decision; see OQ-1)
- The landing is built to work in two states, chosen by one constant `LANDING_MODE: 'pilot' | 'public'` in `web/components/landing/copy.ts`:
  - **pilot** (default until OQ-1 is decided): no "your textbooks" claim; a visible "Research pilot" label; headline "Ask. Get the page." and sub "A cite-or-decline study pilot for MBBS: every answer points to the book, chapter and page, or says the books don't settle it." CTA reads "Enter access code" or "Join the pilot", matching whatever gate exists; never "Ask your first question" when a gate is in front of `/ask`.
  - **public** (only after the user records a rights decision **and** the safety gate passes [strategy line 130, line 381, line 399]): headline "Your MBBS textbooks, answering back." (the strategy's positioning line [strategy line 128], which may be used "only once the content rights are settled"), CTA "Ask your first question".
- Whether book titles appear at all is a separate user decision in G5 (pilot copy can use subject descriptors such as "a standard anatomy textbook" if the user decides so).
- **L-11** The landing inherits `robots: noindex` (`web/app/layout.tsx:12`) and Caddy's `X-Robots-Tag: noindex, nofollow` (`deploy/v2/Caddyfile.v2-block:4`), and sits behind the same gate as the app unless OQ-1 says otherwise. A test asserts the robots meta on `/`.

#### Narrative: scene-by-scene storyboard

Visual language: the dark "specimen" look of `/how` (hand-rolled shaders, accent teal, fresnel rim on 3D anatomy; `story/shaders.ts`, `chiasm.ts`) in dark mode, and a tuned light palette (point size and alpha adjusted for normal blending; `story/palette.ts` notes dark uses additive glow and light uses normal blending) in light mode. The page is a scroll story with a sticky WebGL canvas behind SSR text panels. **Five scenes** (decision: the draft's seven were too long for "within one scroll", and the Explore scene relied on team jargon). Every number comes from data shipped with the page.

| # | What the student sees | Copy direction (draft, user to approve) | What it proves |
|---|---|---|---|
| 0 Hero: an answer, with the page | **First viewport, SSR, no WebGL needed**: a real answer card for an exam-style question (the new recorded journey, below): the question, a two-line answer in Mentor's own words, and citation chips that read like a student's own reference, for example "Gray's 5e · Ch N · p N" (pointers only, values from the capture). Three tappable example-question chips sit in the hero. **Then the three.js payoff**: one chip lifts off and flies into the library map (`public/story/library.bin`, the real t-SNE layout, LIB2 format [audit A]), which settles into seven galaxies, one per book, labelled with the names students use (Gray's, Guyton, Tripathi, Robbins, Essentials of Medical Microbiology, Davidson, Harrison) as typographic labels, not covers. The chip's book glows. Directly under the hero: a **coverage strip** (SSR text) | Headline per `LANDING_MODE`. Coverage strip (grouped by prof year): "Covers: Anatomy (Gray's 5e), Physiology (Guyton 14e), Pathology (Robbins), Pharmacology (Tripathi 7e), Microbiology (Essentials of Medical Microbiology), Medicine (Davidson 24e, Harrison 22e). Not yet: Biochemistry, OBG, Surgery, PSM, Forensic Medicine, ENT, Ophthalmology, Paediatrics." Editions from `story.json` book names | **Utility** in the first 5 seconds: a cited answer with the page. **Potential**: a real library, not a chatbot's memory |
| 1 Why was I wrong? | The strategy's wedge [strategy §3 resolution]. An MCQ card with four options; the student's pick turns red, the right one green, then a verdict with a page pointer and 3 viva questions. **Data**: one real `/api/why/stream` output captured into `public/landing/why.json` with the capture date. No made-up MCQ. The MCQ is exam-style, never a patient-management drug choice | "Got an MCQ wrong? Paste it. See why, with the page, and three viva questions to test yourself." | **Utility**: the exam workflow |
| 2 The honest no | A **near-miss medical** question the books really do not settle (for example a topic from a subject with no book in the library), not a trivia question: the points dim; the card reads "The books don't settle this." Captured from the real pipeline into `public/landing/declined.json`. The `/how` story's cricket question stays on `/how` | "It would rather say no than guess. If your book isn't in the library yet, it tells you." | **Trust**: cite-or-decline is visible behaviour |
| 3 Body and books, linked | The hero question's evidence streams into the optic chiasm (the same real mesh `/how` uses, here loaded from a pre-extracted `public/landing/chiasm.bin`), which rotates with a rim glow; a "View in 3D" chip appears on the answer card, and a tap opens `/atlas?select=FMA62045`. Credit line under the scene: "3D model: BodyParts3D, © DBCLS, CC BY 4.0" linking `/credits` | "Answers know where things are. Jump from a sentence to the structure in 3D." | **Potential**: text and anatomy connected |
| 4 Make it yours, what we've measured, start | If `diagram` and `videos` are live (resolved on the server): the hero answer spawns a flowchart, and below it, visually separated from the answer card, a row of **neutral placeholder video cards** (grey 16:9 blocks, generic title bars, no real titles, channels, thumbnails or YouTube logo) labelled "Suggested lectures (external, not checked by MedEvolv)". If not live, that half of the scene is absent. Then **"What we've measured so far"** (one line each, from a constants file with caveats; see Honesty rules), then the final CTA and the reassurance line | "Turn an answer into a flowchart. Find a lecture on the same topic." Measured: "In our internal test of 39 questions it answered, declined or refused correctly every time (13 Nov 2026)." Caveat line copied word for word from `/how` (`Story.tsx:240`): "Results on our own question sets, not a clinical-safety guarantee. Retrieval is not yet measured for every book. A study aid, not medical advice." Limitation line: "Hard clinical cases still fail our clinician review; do not use it for patient care." Reassurance line under the CTA: **facts the user confirms only** (candidate: "Free during the pilot · No sign-up · English only for now"); never invented. "Start with a topic you're revising this week." | **Trust**: measured, and honest about what is not |

**The recorded journey (replaces the draft's use of `story.json` `journey`).** The existing journey is a patient-management drug question ("A patient with pheochromocytoma is posted for surgery. What drug should be started first and why?", route `decompose`) whose answer gives drug choice and duration (`apps/web/public/story/story.json`). Making that the first thing a student sees would show exactly the use the strategy warns against [strategy §3 "Not clinical decision support", line 381], and it is a final-year question for a preclinical audience. The landing therefore uses a **new capture**:
- **L-7a** Landing journeys and example chips are phrased as exam or viva questions, never "a patient ... what drug should be started". Candidate hero question: "Trace the visual pathway and the field defect from a lesion at the optic chiasm." **UNKNOWN** whether it answers with Gray's and Guyton citations; the capture run checks, and if it declines or cites poorly, the agent tries the next candidate from the 39-question eval set. The user approves the final question.
- The capture (`scripts/build_landing_captures.py`, new, WS-L) records the journey (question, route, evidence pointers, answer prose, citation pointers), a decline, and a Why-was-I-wrong verdict, each with `captured_at` and the commit. It calls DeepSeek, so it needs the user's yes (cost: a handful of calls). Passage text and `excerpt` fields are stripped; pointers only.
- Follow-up outside this PRD: `/how` still shows the pheochromocytoma journey. Flagged to the user as OQ-16.

**Mobile honesty about the map.** `loadStory` always downloads the full `library.bin` (477,441 bytes = 16 + 36,725 × 13) and on mobile keeps only about every third point plus highlighted ones (`web/components/story/data.ts:36-45`, `:86` `i % 3 === 0`). So:
- The caption's count is computed from the points actually rendered: on mobile, "Each dot is a passage. Showing N of 36,725 on this screen." with N = the loaded count. On desktop: "36,725 passages. Each dot is one."
- Acceptance and budgets below say "the map animates in", not "36,725 points", for phones.

Copy direction: second person, short sentences, student vocabulary ("viva", "prof exam", "long answer"), no superlatives ("first", "best"), no claims of clinical use [strategy §3 "What NOT to claim"], no "AI-native 3D" or "AI tutor" lead [strategy §3]. No passage excerpts on the landing at all: pointers only (book, edition, chapter, page). This follows the pointer-only principle [engineering-principles §2] and the plan to stop showing excerpts publicly [strategy §1]. No latency claim unless shown with its measurement ("median about 3 s, p50 2.75 s, 13 Nov 2026 eval" [eval_2026-11-13.md:17]); default is to show none.

Fallbacks:
- **No WebGL** or the scene throws: the `StoryEntry` pattern [audit A] (dynamic import with `ssr:false` + error boundary) renders a static version: the same SSR text panels with **inline SVG illustrations** (answer card, MCQ card, decline card; theme via CSS tokens, near-zero bytes). Raster posters only where SVG cannot show the idea (the galaxy, the chiasm): WebP/AVIF, at most 25 KB each, `loading="lazy"`, light and dark variants, committed under `public/landing/`. No poster contains YouTube data.
- **Reduced motion**: canvas shows each scene's end state, cross-fades only, no point flight, no auto-rotation.
- **Save-Data / slow connection** (`navigator.connection.saveData` true or `effectiveType` in `2g`/`slow-2g`): static fallback with SVG only, three.js never loads. iOS Safari has no `navigator.connection`, so also: **time fallback**: if `library.bin` has not decoded within 6 s of the scene being requested (target), stay static.

#### Layout inside the app shell (decision)
The landing renders inside `AppShell` (no route-group move, to keep the change small): the canvas is full bleed **within** `<main>` (respecting `md:pl-[var(--rail-w)]` on desktop); the mobile sticky CTA bar sits above the fixed tab bar (`bottom: var(--tabbar-h)`, `AppShell.tsx:94`), and is hidden while scene 0's own CTA is on screen. The shell's existing "Skip to content" link is reused; no second skip link.

#### Route change: Ask moves to `/ask`
From the audit's link inventory [audit A], in two deploys:
- **P1 (WS-X): alias.** New `web/app/ask/page.tsx` renders `<ChatView />`; `/` still renders `<ChatView />` too. `SharedAnswer.tsx:87` points to `/ask` (WS-X owns that file). When `/ask` (or `/`) finishes a first answer, it sets the `mm_asked` cookie (below). Nothing else changes.
- **P2 (WS-L): switch, same deploy as the landing.**
  1. `web/app/page.tsx` becomes the landing.
  2. `nav.ts`: Ask `href: '/ask'`; `isActive` for Ask is `/ask` or `/a/*`. Landing is **not** a tab (keeps the mobile tab bar at four items [audit A.7]).
  3. Logo links (`AppShell.tsx:25,61`) go to `/ask` (home for people using the app); a "Take the tour" link in the shell's overflow and `/credits` footer goes to `/?tour=1`.
  4. CTAs to `/ask`: `HowClassic.tsx:116`, `Story.tsx:243`. `not-found.tsx:9` goes to `/` (the landing explains the product to a lost visitor). Decision D-6.
  5. `VerdictCard.tsx:13` builds `/ask?q=...&go=1`.
  6. `ChatView.tsx:81` `replaceState` to `/ask`.
  7. Old links: `next.config.mjs` gets `redirects()` from `/` to `/ask` when the `q` query key is present (`has: [{type:'query', key:'q'}]`), `permanent: false`. Next forwards the query string, so `/?q=...&go=1` keeps working [audit A.6]. No Caddy change needed [audit A.6].

#### Returning-user rule (decision D-5, revised)
**Rule**: when a chat answer finishes for the first time in a browser, the client sets a first-party functional cookie `mm_asked=1` (no id, no tracking, `SameSite=Lax`, one year). `web/middleware.ts` redirects `/` to `/ask` on the server when the cookie is present, unless `?tour=1` is in the URL. No flash, no client-side `router.replace`, no JS needed. `/privacy` discloses the cookie.
**Why**: students use Mentor in bursts during revision; the landing is a one-time explanation. A server redirect avoids showing the hero for a few seconds on slow phones before yanking the student away (the draft's client-side approach). The cookie is written from the first `/ask` alias deploy (P1), so returning users are already recognised when the landing ships.

#### CTA strategy
- One primary CTA per screen (label per `LANDING_MODE`), sticky at the bottom on mobile after scene 0 (above the tab bar).
- Example-question chips (hero and scene 4) deep-link to `/ask?q=<text>&go=1`, so the first answer appears with no typing. Three questions, one per prof year (anatomy, pathology or pharmacology, medicine), in viva phrasing, chosen from questions the 39-question eval set answers correctly (`docs/eval_2026-11-13.md`); none patient-scoped. WS-L picks, the user approves.
- Secondary: "See how it works" to `/how` (for the curious and for professors).
- Clicking a landing CTA sets `sessionStorage.from_landing = 1` for the `question_sent_from_landing` event.

#### UX states
| State | Behaviour |
|---|---|
| Loading | SSR hero (answer card, coverage strip, CTA) visible immediately; canvas fades in when `library.bin` is decoded; a thin progress line, no spinner over the text |
| Data load error or 6 s time fallback | Static fallback (SVG + small posters); console warning only |
| `diagram`/`videos` flags off | The "make it yours" half of scene 4 is not rendered by the server; no client-side insertion or removal, so scroll length never shifts |
| `/api/features` fails or is slow | Treated as all-false (server fetch with a 1 s timeout and a short revalidate) |
| 390 px | Hero card full width; canvas fills the viewport behind later panels; mobile point subsample with the honest caption; sticky CTA bar above the tab bar |
| 1440 px | Text panels left column, canvas full bleed within `<main>` |
| Light/dark | Canvas palette from `story/palette.ts` per theme, tuned for light; hero card is SSR text readable in both, independent of the canvas |
| Reduced motion | End states only, cross-fades |
| Accessibility | Each scene is a `<section>` with a heading; the canvas is `aria-hidden`; every visual claim also appears in text; chapter rail buttons have labels + tips; focus order follows scenes |

#### Functional requirements
- L-1 After P2, `/` renders the landing; `/ask` renders the chat with unchanged behaviour. Before P2, both render the chat.
- L-2 `/?q=X&go=1` redirects to `/ask?q=X&go=1` and auto-sends, as today.
- L-3 `/?q=X` (without `go`) redirects to `/ask?q=X` and prefills without sending.
- L-4 Nav "Ask" is active on `/ask` and `/a/*`, not on `/`.
- L-5 The three.js chunk for the landing is not requested before first paint, and is never requested when WebGL is missing, reduced data is on, or the returning-user redirect fires.
- L-6 The landing never fetches `/models/atlas.json` or any atlas chunk. Scene 3 loads only `public/landing/chiasm.bin`, and only when scene 3 is within one viewport.
- L-7 All passage counts, eval numbers **and their caveat strings** render from `story.json` / a typed constants file `web/components/landing/facts.ts` whose values are copied from the eval docs, with the source path and date in a code comment. A unit test asserts that each number has a caveat entry.
- L-7a Landing journeys and examples are exam-style, never patient-management questions (above).
- L-8 Returning-user rule as specified; `/?tour=1` bypasses it.
- L-9 Static fallback renders every scene's text and its SVG or poster.
- L-10 The "make it yours" content renders only when the server-side feature fetch reports `diagram` and `videos` true. The landing never embeds, fetches or captures YouTube API data (titles, channels, thumbnails, logo).
- L-11 Robots and gate inheritance, as above.
- L-12 The mobile caption's passage count equals the number of rendered points, or states the ratio.
- L-13 A credit line for BodyParts3D is visible near scene 3 and links `/credits`.

#### API contracts
No new endpoint is needed for the landing. Build-time captures (run by an agent with the user's yes, since they call DeepSeek and cost a little):
- `public/landing/journey.json`, `declined.json`: the new exam-style journey and decline; pointers only; `captured_at` and commit.
- `public/landing/why.json`: one real `VerdictEvent` [api/README.md] plus `captured_at` and the `e0eec26`-or-later commit. Explanation text is Mentor's own prose; `excerpt` fields are stripped (pointers only).
- `public/landing/chiasm.bin`: the two FMA62045 parts' positions, normals, indices and bounds, extracted by `scripts/extract_chiasm.mjs` from the local human-atlas models, with the source atlas `version` recorded in a sidecar JSON. Size: estimated a few tens of KB (UNKNOWN until extracted). `/how` may later switch to it too (separate change, needs `/how` QA).

#### Data and licensing
- Library map and counts: our own derived data (`library.bin`, `story.json`); contains no passage text ("indices into the map only", `scripts/build_library_map.py` docstring).
- Book titles: shown on `/how` today; on the landing only per the user's G5 decision.
- BodyParts3D mesh for the chiasm: CC BY 4.0. **No credit is shown anywhere in the v2 app today** (checked at `e0eec26`); the credit exists only in `deploy/atlas/ATTRIBUTION.md`, which is not rendered in v2. C1 (P0) fixes this site-wide; the landing adds its own credit line near scene 3 (L-13).

#### Honesty and trust rules
- No fake metrics, user counts, testimonials or logos.
- Eval numbers carry their sample size, scope and date, and the caveat strings from `/how`. "90.8% correct chapter in top 3" is **not** shown to students (retrieval jargon); if the user wants it, it must read "Tripathi only, 446 generated questions, 13 Nov 2026" [eval_2026-11-13.md:16, :63]. The 39/39 result is "39 questions, internal, 13 Nov 2026", with the known limitation line. Strategy caveats we keep in mind and do not contradict: only 2 of 7 books have retrieval metrics; 9/15 gold items are unverified [strategy lines 155, 420].
- The ontology fact count is not shown (internal, unaudited [strategy line 519]).
- The "make it yours" content never advertises features that are not live.
- No "AI-native 3D first" or similar claims [strategy §3].

#### Acceptance criteria
- Given a new browser, when I open `/`, then the hero answer card with citation pointers and the coverage strip are the first paint, within the LCP budget, and the library map animates in afterwards.
- Given a phone, then the map caption's count equals the rendered points or states the ratio.
- Given an old link `/?q=nephrotic%20syndrome&go=1`, when I open it, then I land on `/ask` and the question is sent.
- Given the `mm_asked` cookie, when I open `/`, then the server responds with a redirect to `/ask` and no landing HTML or three.js request appears.
- Given `/?tour=1`, when I open it as a returning user, then I see the landing.
- Given WebGL is disabled, when I open `/`, then I see all scene text and illustrations, and no errors break the page.
- Given reduced motion, when I scroll, then points do not fly; scenes cross-fade.
- Given `diagram` or `videos` is off, then the "make it yours" content does not exist in the server HTML.
- Given `LANDING_MODE = 'pilot'`, then the page shows "Research pilot" and no "your textbooks" claim, and the CTA matches the gate.
- Given `/`, then `<meta name="robots" content="noindex...">` is present.
- Given scene 3, then a BodyParts3D credit link is visible.
- **Awe and utility bar (pre-release hallway test, release gate for P2).** Given a production build on a phone, when 3-5 MBBS students who have not seen Mentor each scroll the landing for 60 s without help and are then asked (1) "What does this do for your exam?" and (2) "What would you try first?", then **at least 4 of 5 (or 3 of 3 if only 3 are available)** answer (1) with a cited-answer or page-pointer idea (for example "it answers from the textbook and shows the page", or "it tells me why my MCQ answer was wrong") and name a concrete first action for (2). Each student also rates "Did anything make you want to keep scrolling?" (yes/no, with what). Fail = rework scene 0 copy and order, then re-test. Recruitment, consent wording (no personal data recorded, notes only) and the session script are the lead's; the students are recruited by the user (UNKNOWN who; same pool as the 20 Nov questionnaire, ASSUMPTION). Notes go in the PR, no names.
- **Smoothness.** Given a named mid-range Android phone (ASSUMPTION: a Redmi Note- or Galaxy A-class device that a team member owns; the exact model is recorded in the PR) on Chrome, when I scroll the landing top to bottom twice, then the median frame rate during scroll is **at least 50 fps** (target, measured with Chrome remote DevTools Performance panel) with no long task over 200 ms after first paint. If the target is missed after one tuning pass (point count, pixel ratio cap at 1.5), that device class gets the static fallback (a GPU tier check via a frame-time probe in the first 2 s), and the PR records the result.
- **Keyboard.** Given a desktop browser, when I press Tab from the top of `/`, then focus moves skip link → hero example chips → hero CTA → each scene's interactive controls in scene order 0 to 4 (chapter rail buttons after the scene content, never before) → final CTA, with a visible focus ring at every stop, no focus on the `aria-hidden` canvas, and the page scrolls so the focused control is in view; Shift+Tab reverses the same order.
- **Screen reader.** Given VoiceOver on iOS (and on macOS), when I swipe through `/` from the top, then I hear the `LANDING_MODE` headline as a level-1 heading, the hero question, the two-line answer and each citation pointer as text (for example "Gray's 5e, chapter N, page N"), then the coverage strip, then each of the five scenes as a `<section>` with its heading and every visual claim in text; the canvas is never announced; the mobile caption reads the rendered-point count. Rotor heading navigation lists exactly the five scene headings under the h1.

#### Test plan
- Web build + type check + `check:tips` (G1).
- Redirect test: a small Node script (or Playwright, see §5.5) on `next start`: `/?q=x&go=1` gives a 307 to `/ask?q=x&go=1`; `/` with `mm_asked=1` gives a redirect to `/ask`; `/?tour=1` with the cookie gives 200.
- `facts.ts` unit test (every number has a source, date and caveat), run by the web unit runner (§5.5).
- Hallway test (above), 0.5 d of WS-L time plus the user's recruitment; frame-rate run on the named Android device; keyboard and VoiceOver passes recorded in the PR.
- Browser QA at 390/1440, light/dark (light hero specifically), reduced motion, WebGL off (Chrome flag), Save-Data on, slow-3G throttling for the time fallback.
- Lighthouse mobile on the production build for the budget (G3).
- Link audit: grep for `href="/"` and `'/?q='` after the change; only `not-found` and "Take the tour" may point at `/`.

#### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Landing weight hurts students on mobile data | SSR hero as LCP; three.js lazy after paint and skipped on Save-Data or after 6 s; budgets in §5.2. Note: mobile still downloads the full 477 KB `library.bin`; a separate mobile file is an option if G3 fails |
| Scene 3 3D data | The draft's plan (fetch `atlas.json` and the chunk holding the chiasm) measured **about 3.7 MB** in the local human-atlas build on 2026-11-15: `atlas.json` 1,335,285 bytes (no `.gz` sibling, so served uncompressed by the `/models` handle, which has `precompressed gzip` but no `encode`) plus `body-6.bin.gz` 2,378,951 bytes, where both FMA62045 parts sit. The deployed build may differ slightly. That breaks the 3 MB budget, so `chiasm.bin` is the plan, not a fallback |
| Old links break | Redirect keyed on `q`; acceptance test |
| Public marketing conflicts with the rights position or the safety gate | `LANDING_MODE = 'pilot'` by default; OQ-1 is a hard gate; L-11 noindex |
| Returning-user redirect confuses someone who wants the tour | `?tour=1`, "How it works" link, "Take the tour" link |

#### Open questions
See OQ-1, OQ-2, OQ-3, OQ-8, OQ-16 in §6.2.

---

### 4.1 R1: Flowchart maker ("Make a flowchart")

#### Problem and user story
Students revise sequences and classifications as diagrams, and draw them in prof exams: pharmacology classification trees ("Classify beta blockers"), anatomical pathways (visual pathway, brachial plexus), cascades (coagulation, RAAS) and pathogenesis sequences. `rag/diagrams.py` already builds ontology-grounded Graphviz DOT for `case` and `drug` subjects, but only in Streamlit, and returns `None` for topics outside the ontology [audit B]. v2 has no diagram route and no renderer [audit B].

> As a student reading a cited answer, I want a flowchart of the topic where every box and arrow points to its source, so I can revise it visually and trust it.

#### Grounding design (decision D-1, revised)
Two sources, tried in order. Both produce the **same versioned JSON graph** (below), so the client has one renderer.

1. **Certified path (ontology).** Used only when (a) `diagrams.pick_subject(question, ...)` finds a condition or drug, **and** (b) the answer text mentions that subject and at least 3 of the chosen facts' object labels (reusing the `highlight` word overlap in `diagrams.py`). Otherwise the ontology chart would cover things the answer never discussed (for example a workup/treatment chart for "pathophysiology of X"). The `_Dot` builder is **refactored** to emit nodes, edges and groups, with DOT derived from that for Streamlit; `VERSION` is bumped. Section headers ("Presentation", "Treatment", "First line") become **group titles, not nodes**, so every node is a fact with a source. Cap: at most 4 facts per section, only sections whose labels the answer mentions, and the total node cap of the chosen `kind` (below); otherwise truncate by answer overlap. The case title is changed from "`<condition>`: clinical decision flow (certified textbook facts)" (`rag/diagrams.py:212`) to "`<condition>`: textbook overview for revision". Badge: "From certified facts".
2. **Answer path (LLM, validated).** Otherwise, DeepSeek turns the **already-cited answer** into a graph of one `kind`. It may only restate what the answer says. Every node and edge must carry at least one citation (`[n]` passage or `[G#]` fact) that appears in the answer sentence it came from, and a deterministic validator checks that (rules below). Badge: "Drawn from this answer's citations".
3. **Decline.** If neither path yields a valid graph, the card declines with a helpful next step (UX below). No partial guesswork.

Why this design: the answer is already grounded (cite-or-decline, quote checks). A diagram that only restructures the answer adds no new claims, so it cannot be less trustworthy than the answer, provided the validator rejects anything new, including new relations carried by arrows.

**Diagram kinds** (new; drives verbs, caps and layout):
| `kind` | Use | Edge verbs allowed | Node cap |
|---|---|---|---|
| `classification` | "Classify X", types, subtypes | `includes`, `subtype of`, `is a` | 24 (left-to-right tree; collapsible branches on mobile) |
| `pathway` | courses, branches, supply, visual pathway, plexus | `passes to`, `branches to`, `supplies`, `drains to`, `joins` | 18 |
| `sequence` | mechanism, pathogenesis, cascade, workup | `causes`, `leads to`, `activates`, `inhibits`, `increases`, `decreases`, `then`, `investigate with`, `treats` | 14 |
| `case` / `drug` | ontology path only | as emitted by the refactored `_Dot` | 14 after caps |

**Validator rules (server side, deterministic).** Node rules:
- V1 JSON parses against the schema; one retry with the error message, then decline.
- V2 3 to the `kind`'s node cap; edges reference existing nodes; graph is connected; no self-loops.
- V3 Every node has non-empty `cites`; every cite exists in the answer's citations (passage `[n]` in `citations`, fact `[G#]` in `graph_citations`) **and** its marker appears in the answer text.
- V4 Lexical support: each node label's content words (lower-cased, stop-words removed, simple stemming) overlap at least half with the words of the answer sentences that carry the node's markers. Numbers in a label must appear verbatim in those sentences (no new numbers). Dose, duration and frequency numbers are removed from labels on both paths.
- V5 Each edge label is from the `kind`'s verb list or empty.
- V6 If more than 30% of proposed nodes fail V3/V4, decline the whole diagram. 30% is a ceiling to tighten on the eval set, never to loosen.

Edge rules (new):
- E1 Every edge has non-empty `cites`, and at least one cited sentence contains lexical support (as V4) for **both** endpoint labels.
- E2 The edge verb or a listed synonym appears in that sentence, and its polarity class matches (activate/increase/causes vs inhibit/decrease). For order-sensitive verbs (`causes`, `leads to`, `passes to`, `branches to`), the source node's words appear before the target's in the sentence; otherwise the edge label is set empty.
- E3 A negation cue (`not`, `never`, `no`, `without`, `unless`, `does not`) in the supporting span, without a matching negation in the node or edge, fails the edge.
- E4 When a node is dropped, its incident edges are dropped and **never bridged**; if that disconnects the graph, the diagram declines.
- E5 `role: "warning"` only when the cited sentence contains a warning cue (`never`, `contraindicated`, `avoid`, `must not`, `WARNING` from a graph fact).

Answers with status `not_in_sources`, `insufficient` or `personal_refusal`, and patient-scoped questions (common UX rules), never offer the button.

#### Renderer (decision D-2)
Server returns a JSON graph; the client lays it out with **`@dagrejs/dagre`** (layered layout for flowcharts; top-to-bottom for `sequence`/`pathway`, left-to-right for `classification`) and draws plain React SVG. Groups render as labelled bands.
- Why not Mermaid: it parses a text language (LLM output turned into markup is an injection surface), and its bundle is large (exact size UNKNOWN; measure if reconsidered). We would also lose control of citation chips on nodes and dark-mode tokens.
- Why not Graphviz WASM (for example `@viz-js/viz`): exact quality of DOT, but a WASM download (size UNKNOWN; measure if reconsidered) for an optional feature.
- Why not the existing `d3-force`: force layouts do not give the top-to-bottom order a flowchart needs [audit B notes lower quality].
- dagre is lazy-loaded with `next/dynamic` only when the student taps "Make a flowchart". **Budget**: the diagram chunk at most 60 KB gzip (target), checked from `next build` output (G3). If dagre's measured size breaks this, fall back to a tiny hand-written layered layout (longest-path ranks), since graphs are at most 24 nodes.

#### UX spec
- Trigger: `Chip` "Flowchart" with the lucide `Workflow` icon on the answer's action row. Shown only when the answer has at least 3 sentences carrying a citation marker (counted client-side from the answer text) and the safety framing allows. Tip: purpose "Turns this answer into a revision flowchart." effect "Every box and arrow links to its source. Takes a few seconds."
- Placement: the diagram card renders inside the answer `<article>` after `SourceList` and `SpatialChips`, before the trace disclosure (the slot the audit recommends [audit C]). Because the trigger sits lower, at the action row (`AnswerCard.tsx:101-113`), the skeleton is **scrolled into view** (smooth, or instant under reduced motion) and receives focus when loading starts.
- States:
  | State | What shows |
  |---|---|
  | Idle | Chip only |
  | Loading | Skeleton at the expected height (kit `Skeleton`), text "Drawing a flowchart from citations [1]-[k]..." (k from the answer); chip disabled (`aria-disabled`) with disabled tip "Working on it" |
  | Ready | SVG flowchart; groups as labelled bands; each node shows its citation chips. **Passage chips** `[n]` open the answer's source drawer at `[n]` (answer path only). **Fact chips** (ontology path, and `[G#]` on the answer path) use a different chip style labelled `F1`, `F2`... and open a "Diagram sources" list (book, edition, chapter, pages, `fact_id`; no `quote`, no `fact` text). Header: badge (certified or answer-based), "Save image", "Full screen", overflow "More" (SVG, Report a problem). Footer line on the card: "Study aid summarised from textbooks. Not for decisions about a real patient." |
  | Declined, `reason: too_few_supported_nodes` (or any validator reason) | Muted card: "This answer doesn't have enough cited steps for a flowchart. Try asking for a classification, pathway or mechanism." plus one tap-to-ask chip, for example "Classify <subject>" when a subject is known. No retry button (the validator result is deterministic for the same answer) |
  | Declined, `reason: generator_error` (LLM timeout or failure, D-13) | "Couldn't draw it right now." with a **Retry** button (not deterministic: a retry may succeed). Retry calls `POST /api/diagram` again; a cached `ok` is never replaced by a failure |
  | Declined, `reason: budget` (daily cap, D-14) | "Flowcharts are paused for today." No retry button; the chip stays disabled for the rest of the page load with disabled tip "Paused for today" |
  | HTTP 429 `rate_limited` | "Too many requests, try again in a minute." Chip re-enabled after 60 s; no Retry button inside the card |
  | Client abort at 35 s or network error | "Couldn't draw it right now." with a **Retry** button (same copy as `generator_error`) |
  | HTTP 403 `bad_signature` | Card removed and the chip hidden for that answer (not the student's problem; logged as a console warning and an anonymous `diagram_sig_fail` event) |
  | HTTP 503 `diagram_unavailable` (flag turned off after the page loaded) | Card removed and the chip hidden for the rest of the page load |
  | Flag `diagram` false, or `/api/features` failed | Chip absent (never shown and then refused; FR D-15) |
  | Answer without `answer_sig` (shared page, or an answer streamed from an older API) | Chip absent (D-16); a shared page shows only a stored diagram, read-only |
  | Unknown future `reason` | Treated as `generator_error` copy without Retry |

  All strings live in one copy map, `web/lib/copy/diagram.ts` (WS-X), keyed by `reason` and status, so the mapping is one table the tests import.
- 390 px: diagram fits width; `classification` trees collapse to the first level with expandable branches; labels wrap at about 26 characters (same as `_wrap` in `diagrams.py`); no pinch-zoom inside the card (it fights page zoom); "Full screen" opens an overlay with its own pan/zoom, rotate-friendly.
- Light/dark: node fill `surface2`, stroke `border`, text `ink`.
- Reduced motion: no draw-in animation.
- Accessibility: the SVG has `role="img"` and an `aria-label` summary; a visually hidden ordered list repeats the nodes in reading order with their citations, so screen readers get the same content; all header controls have tips.
- **Export ("Save image")**: always rendered on a **white background with the light palette**, portrait-friendly, at 2x, independent of the current theme. Footer in the image: "MedEvolv Mentor · Study aid summarised from textbooks. Not for decisions about a real patient. · sources: [1] Book ed, ch, p ... · <date>" (pointers only). Primary action uses `navigator.share({ files: [png] })` where supported (share sheet: WhatsApp, Photos), with a download fallback. SVG export is under "More". File name `medevolv-flowchart-<slug>.png|svg`.
- **Shared answers**: diagrams are server-issued. Each `ok` diagram is stored in `diagram_cache` under a `diagram_id`; the share payload carries only `diagram_id`; `SharedAnswer.tsx` fetches `GET /api/diagram/{diagram_id}` and renders it read-only, dropping the diagram if the fetch fails. If the student drew the diagram after sharing, the turn's `shareId` is cleared when a diagram is added, so the next Share creates a new share that includes it (`Actions.tsx:16` reuses `shareId` today; answers are immutable, `api/main.py` has only POST and GET `/api/answers`).

#### Functional requirements
- D-1 The "Flowchart" control appears only on answers with status other than `not_in_sources`, `insufficient`, `personal_refusal`, with at least 3 cited sentences, and not for patient-scoped questions.
- D-2 Tapping it calls `POST /api/diagram` once; repeated taps while loading do nothing.
- D-3 If the ontology path is used, the response `source` is `ontology`, every node cites a certified fact (`{kind:'fact'}`), and group titles carry no cites.
- D-4 Otherwise the answer path runs; every returned node and edge passes V3-V6 and E1-E5.
- D-5 If neither path yields a valid graph, the response is `status: "declined"` with HTTP 200 and a `reason`.
- D-6 The client renders the graph with no network calls beyond the API call (shared pages: one `GET /api/diagram/{id}`).
- D-7 "Save image" produces a PNG on a white background with the source footer and the study-aid line; SVG export likewise.
- D-8 The diagram chunk is not in the initial JS of `/ask`.
- D-9 Results are cached in `diagram_cache` in `$APP_DB` (the persisted `v2_appdb` volume), keyed on `sha256(VERSION | ontology mtime | question | answer text | citations)`; the raw question is never stored. The API calls `diagrams.build(..., use_cache=False)` (the relative `data/ontology/diagrams/` cache in the API container is not persisted and may not be writable, `rag/diagrams.py:28, :275-280`). Rows have a 90-day TTL unless pinned by a share. A cache hit returns in under 300 ms on the VM (target).
- D-10 No passage text and no ontology `quote` or `fact` text is sent to the browser beyond what the answer already shows.
- D-11 A fact chip never resolves into the answer's passage citations, and a passage chip never resolves into the fact list.
- D-12 Request authenticity: `/api/diagram` rejects (403) any request whose `answer_sig` does not match (below).
- D-13 Limits: the LLM call has a 20 s timeout (connect + read), the endpoint a 30 s total budget including one retry; the client aborts at 35 s and shows the Error state. The LLM call runs on a dedicated executor (`max_workers=2`) so chat keeps the default thread pool (the VM has 1 CPU and uvicorn runs 1 worker, `deploy/v2/Dockerfile.api`; chat uses `run_in_executor(None, ...)`, `api/main.py:84`). Exceeding the budget yields `declined` with `reason: "generator_error"`.
- D-14 A global daily cap on diagram LLM calls (target 300/day, a budget we set) returns `declined` with `reason: "budget"` once reached.
- D-15 **Flags on the client.** `/ask`, `/a/[id]` (`SharedAnswer`) and `/atlas` learn the flags from one source: the root server layout fetches `GET /api/features` (1 s timeout, short revalidate, same helper the landing uses) and passes the result to a client `FeaturesProvider`; components read `useFeature('diagram' | 'videos' | 'female_atlas')`. If the fetch fails or times out, every flag is false. No component calls `/api/features` from the browser. The Flowchart chip renders only when `diagram` is true; a 503 at request time (flag flipped after load) hides it for the page load (UX table). **ASSUMPTION**: a server fetch in the root layout does not make every route dynamic in a way that breaks the route-size budgets; WS-X measures it in G3, and the fallback is a single client fetch per load in the provider with the same all-false default.
- D-16 The chip renders only when the answer carries an `answer_sig` (in memory, for the current tab). The chat store is not persisted today (`web/store/chat.ts` has no `localStorage` or `persist`; checked at `e0eec26`), so there is no restored history; if persistence is added later, `answer_sig` is persisted with the turn. The share payload does **not** store `answer_sig` (shares are public, and the signature has no use there): `SharedAnswer` never shows the chip and renders only a stored `diagram_id`, read-only.
- D-17 Every `reason` and error status maps to exactly one row of the UX table; the mapping lives in one copy map with a test.

#### API contract
**Change to the chat stream (additive).** `AnswerEvent` gains:
- `graph_citations: [{"n": 1, "fact_id": "...", "book": "...", "edition": "...", "chapter": "...", "pages": "..."}]` for the `[G#]` facts the answer cites (pointers only, built from the facts' `provenance`);
- `answer_sig`: `HMAC-SHA256(DIAGRAM_SIG_SECRET, sha256(canonical_bytes))`, hex. The secret lives only in the server `.env`.
Old clients ignore both fields.

**Canonical serialisation for `answer_sig` (D-12).** The server never signs or checks bytes the client produced. Both at signing time (in the chat stream) and at checking time (in `/api/diagram`), the server parses the fields into Python objects and computes `canonical_bytes` itself:
1. Build the object `{"q": question, "a": answer_text, "c": citations, "g": graph_citations}` where `citations` and `graph_citations` are reduced to the documented keys only (`index, book, edition, chapter, pages, section_id` and `n, fact_id, book, edition, chapter, pages`); unknown keys are dropped and missing optional keys become `null`.
2. Apply Unicode **NFC** normalisation to every string, and normalise line endings to `\n`. No other trimming (whitespace inside the answer is part of the answer).
3. Keep list order as sent (citations are ordered by index; the server rejects a request whose `citations` are not sorted by `index` with 422 rather than re-sorting).
4. Serialise with `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)` encoded as UTF-8. Numbers are integers only (`index`, `n`); a float or a numeric string in those fields is a 422.
5. The client echoes the four fields exactly as received in the `answer` event (it never rebuilds them), and the TypeScript side never computes a signature, so there is one implementation (`api/diagram.py: canonical_answer_bytes`) used for both signing and checking.

Persistence: `answer_sig` lives only in the in-memory chat turn; it is not written to the share payload (D-16).

`POST /api/diagram`

Request:
```json
{
  "question": "string, 1..2000",
  "answer_text": "string, 1..8000 (the answer markdown with [n] and [G#] markers)",
  "citations": [{"index": 1, "book": "...", "edition": "...", "chapter": "...", "pages": "...", "section_id": "..."}],
  "graph_citations": [{"n": 1, "fact_id": "...", "book": "...", "edition": "...", "chapter": "...", "pages": "..."}],
  "answer_sig": "hex string from the answer event",
  "condition": "optional string"
}
```
The server recomputes the signature and returns 403 `{"detail":"bad_signature"}` on mismatch, so the endpoint only restructures answers Mentor itself produced (this settles OQ-6 without storing answers).

Response 200 (`version: 2`):
```json
{
  "status": "ok | declined",
  "diagram_id": "string | null (present when ok)",
  "source": "ontology | answer | null",
  "kind": "classification | pathway | sequence | case | drug | null",
  "subject": "string | null",
  "title": "string | null",
  "groups": [{"id": "g1", "title": "Presentation"}],
  "nodes": [{"id": "n1", "label": "string <= 80 chars", "role": "start | step | branch | end | warning", "group": "g1 | null", "cites": [{"kind": "passage", "n": 1}, {"kind": "fact", "n": 2}]}],
  "edges": [{"from": "n1", "to": "n2", "label": "verb from the kind's list | ''", "cites": [{"kind": "passage", "n": 1}]}],
  "fact_sources": [{"n": 1, "fact_id": "...", "book": "...", "edition": "...", "chapter": "...", "pages": "..."}],
  "dropped": 0,
  "reason": "string, present when declined (e.g. 'too_few_supported_nodes', 'generator_error', 'budget')",
  "version": 2
}
```
`fact_sources` come from the refactored `_Dot` source list, which today holds `{n, fact_id, fact, cite, quote}` (`rag/diagrams.py:102-111`, `:255`). `onto.cite()` returns a flat string today, so the refactor builds the structured pointer from the fact's `provenance` (book title, chapter, pages). The server **drops `quote` and `fact`** before sending (pointer-only rule). Passage cites refer to the answer's own `citations`; fact cites are numbered within the diagram (`F1`...) on the ontology path, and reuse the answer's `[G#]` numbers on the answer path.

`GET /api/diagram/{diagram_id}`: returns the stored response (for shared pages); 404 when missing or expired.

Errors: 422 on bad input; 403 bad signature; 429 `{"detail":"rate_limited"}`; 503 `{"detail":"diagram_unavailable"}` when the flag is off. LLM failures and timeouts are not errors: they become `declined` with `reason: "generator_error"` after one retry, so the UI never shows a stack trace (matches the `error` event policy [api/README.md]).

Rate limit: 10 requests per minute per client IP (target), through the shared limiter in §5.4 (which needs the proxy-header fix to see real client IPs), plus the global daily cap (D-14).

LLM prompt contract (answer path): system prompt says "Restructure ONLY the given answer into a <kind> diagram. Do not add facts. Every node and edge must list the [n] or [G#] markers from the sentence it came from. Use only these edge verbs: ... Output JSON matching this schema." Temperature 0. Max output tokens 1,000 (target). Tokens in/out logged per call (no question text).

#### Data and licensing
- Ontology facts are certified, derived from the textbooks; nothing from the ontology cache is committed [audit B].
- Diagram labels are Mentor's own short paraphrases of its own answer or of certified fact object labels; no textbook sentences. V4/E1 check overlap with the *answer*, not with passages, so no passage text is needed client-side.
- `diagram_cache` holds labels and pointers only, keyed by a hash; it is listed on `/privacy` with its 90-day TTL.

#### Honesty and trust rules
- A diagram never shows a box or an arrow without a source.
- The badge says which grounding was used; fact sources and passage sources are visibly different.
- Every diagram card and every export carries "Study aid summarised from textbooks. Not for decisions about a real patient."
- Decline is a first-class result, with plain copy and a next step.
- "Report a problem" sends `POST /api/feedback` with a new kind `diagram_wrong` and `target_id = diagram_id` (§5.3).

#### Acceptance criteria
- Given an answer about a condition covered by the ontology that mentions its presentation and treatment, when I tap "Flowchart", then I see a flowchart with the "From certified facts" badge, group bands, and every node has an `F` chip that opens the Diagram sources list at the right book and page.
- Given the same ontology diagram, when I tap `F1`, then it never opens the answer's passage `[1]`.
- Given "Classify beta blockers" answered with citations, when I tap "Flowchart", then I get a left-to-right classification tree (up to 24 nodes) or a decline.
- Given an answer citing `[G1]` for a first-line drug, then a node for that drug carries a fact chip and passes V3.
- Given a mocked LLM graph with a reversed, negated or antonym edge, then that edge is dropped or the diagram declines.
- Given a declined answer ("The books don't settle this.") or a patient-scoped question, then no Flowchart chip is shown.
- Given the LLM returns a node with a number not in the answer, then that node is dropped or the diagram declines (V4).
- Given a ready diagram in dark mode, when I tap "Save image", then the share sheet or a download offers a PNG on a white background with the source footer and the study-aid line.
- Given I shared, then drew a diagram, then shared again, then the new share link shows the diagram.
- Given 390 px dark mode, then the diagram is readable without horizontal page scroll.
- Given the API returns `declined` with `reason: too_few_supported_nodes`, then the card shows the "not enough cited steps" copy and the tap-to-ask chip, and no Retry button.
- Given the API returns `declined` with `reason: generator_error` (or the client aborts at 35 s), then the card shows "Couldn't draw it right now." with a Retry button; when I tap Retry, then exactly one new `POST /api/diagram` is sent.
- Given the API returns `declined` with `reason: budget`, then the card shows "Flowcharts are paused for today." with no Retry, and the chip is disabled with the tip "Paused for today".
- Given the API returns 429, then the card shows "Too many requests, try again in a minute." and the chip is enabled again after 60 s.
- Given the API returns 403 `bad_signature` or 503, then the card and the chip disappear for that answer, and no error text is shown.
- Given `/api/features` reports `diagram: false` (or the features fetch fails), when an answer finishes on `/ask` or `/a/<id>`, then no Flowchart chip exists in the DOM.
- Given a shared answer page, then no Flowchart chip is shown, and a stored diagram (if any) renders read-only.
- Given an answer whose citation `book` contains a non-ASCII character and whose `answer_text` contains Windows line endings, when the client sends it back unchanged, then `/api/diagram` accepts the signature (no 403).

#### Test plan
- `tests/test_api_diagram.py` (seam tests through the HTTP endpoint, LLM mocked, per engineering principle 3): ontology hit returns `source: ontology`, `version: 2`, no `quote`/`fact` field, group titles without cites; fact cites never index passage citations; mocked graphs violating V3, V4, V5, E1-E5 rejected (reversed, negated, antonym, bridged edges); answer containing `[G1]` validated; too many failures yields `declined`; malformed JSON retried once then declined; a hung mocked LLM yields `declined/generator_error` within the 30 s budget; bad signature 403; rate limit 429 with a spoofed `X-Forwarded-For` behind the trusted proxy; daily cap gives `reason: budget`; flag off 503; raw question absent from `diagram_cache`. **Signature round-trip**: take the `answer` event from a mocked chat stream (`TestClient` over `POST /api/chat/stream` (`api/main.py:111`), LLM mocked), post its fields unchanged to `/api/diagram` and expect no 403; repeat with NFD-encoded `book`, `\r\n` line endings, reordered JSON keys inside each citation and an extra unknown key (all accepted), and with one changed character in `answer_text`, a float `index` and unsorted citations (403, 422, 422).
- Web unit test (runner in §5.5) `web/lib/copy/diagram.test.ts`: every `reason` the API documents (`too_few_supported_nodes`, `generator_error`, `budget`) and every status (403, 429, 503, abort) maps to the UX row's copy and its Retry/visibility flags; an unknown reason maps to the fallback row. `web/lib/features.test.ts`: a failed or timed-out features fetch yields all flags false.
- `tests/test_diagrams.py` stays green after the `_Dot` refactor (DOT output derived from the new structure).
- **Offline eval (release gate)**: 20 real exam prompts across subjects (at least 5 "classify", 5 "pathway/course", 5 "mechanism", 5 "workup"), answers from the current pipeline, one diagram call each; a human reads each diagram. Report decline rate by `kind`. **Gate: 0 unsupported boxes or arrows in 20.** Cost: about 40 DeepSeek calls; needs the user's yes.
- Browser QA at 390/1440, light/dark; keyboard: tab to the chip, Enter, focus lands on the skeleton, tab through citation chips; tap an `F` chip and a `[n]` chip and check book and page.

#### Risks and mitigations
| Risk | Mitigation |
|---|---|
| LLM adds facts or relations not in the answer | V3-V6, E1-E5; decline rather than draw; offline eval gate |
| Validator too strict, many declines (especially anatomy) | Report decline rate by `kind`; tune V4/V6 on the eval set, never by loosening V3 or E1; helpful decline copy |
| Ontology chart covers things the answer didn't | Use the ontology path only with answer overlap; caps per section |
| Citation numbers collide between facts and passages | Namespaced cites, separate chip style, D-11 test |
| Diagram read as a clinical protocol | Revision title, study-aid line on card and export, no doses, no patient-scoped diagrams |
| DeepSeek cost or abuse | Signed requests, per-IP limit behind a trusted proxy, global daily cap |
| Chat slowed by diagram calls | Dedicated small executor, timeouts |
| Bundle grows | Lazy chunk + 60 KB budget |

---

### 4.2 R2: Suggested YouTube videos and related topics

#### Problem and user story
Students already supplement textbooks with YouTube lectures. Searching is slow and quality varies. Nothing exists in the app today [audit C].

> As a student who just read a cited answer, I want a few lecture videos on the same topic, clearly marked as outside the textbooks, and links to related topics, so I can go deeper.

#### Design summary (from [yt §6])
- Server-side `POST /api/videos`, YouTube Data API v3: one `search.list` + one `videos.list` per cache miss.
- Default quota as checked 2026-11-15: 100 `search.list` calls/day, 10,000 units for other endpoints, so about **100 uncached answers per day** [yt §1]. Must be re-verified on the Cloud console once a key exists.
- Cache per normalised topic, TTL 7 days, purge anything older than 14 days, always under the 30-day storage limit (Developer Policies III.E.4 [yt §2]). **No YouTube API data is stored anywhere else** (not in shared answers, logs, events, posters or the landing).
- Thumbnails shown unaltered; YouTube attribution with the official icon; link out to `https://www.youtube.com/watch?v=ID` in a new tab [yt §2].
- No scraping, yt-dlp, Invidious or Piped [yt §3b].
- Fallback: a "Search YouTube" link `https://www.youtube.com/results?search_query=...` when there is no key, quota is used up, or upstream fails [yt §3a].
- `relatedToVideoId` stopped working on 2023-08-07 [yt §5]; related topics come from **our ontology**.

#### Topic (what we search for)
- The query is built from a **structured topic label**, never from the raw question or answer prose [yt §5]. This also protects privacy: a question may describe a patient; a label like "nephrotic syndrome" does not.
- Topic source, in order: (1) `diagrams.pick_subject(question)` condition or drug name [audit B]; (2) the label of the first `spatial` highlight action (`SpatialEvent.actions[].label` [api/README.md]); (3) best concept match from the concept search, accepted only if it exactly matches a concept label or alias. **ASSUMPTION**: these give a topic for most answered questions; measure the share with no topic.
- **Seam (revised)**: spatial actions are computed after the `answer` event is sent (`api/main.py:96-100`: `answer`, then `spatial_actions` in a thread, then `spatial`, then `done`), so the topic cannot ride on `AnswerEvent`. A new additive SSE event **`topic`** `{ "topic": "string | null", "related": [{"id": "...", "label": "...", "predicate": "...", "tier": "certified"}] }` is emitted after `spatial` and before `done`. `related` is at most 6 items and is empty when `topic` is null (see Related topics). Old clients ignore unknown events; `api/README.md` and the web stream parser are updated. Patient-scoped questions always get `topic: null`.
- No topic: no videos section, no fallback link (we will not send free text to YouTube).
- Query string: `"<topic> lecture MBBS"` [yt §5]. One query per topic.

#### Search parameters (from [yt §1, §6])
- V-0 `search.list` is called with exactly: `part=snippet`, `type=video`, `q="<topic> lecture MBBS"`, `order=relevance`, `safeSearch=strict`, `relevanceLanguage=en`, `regionCode=IN`, `maxResults=15`. `videoEmbeddable` is **not** set. `videos.list` with `part=snippet,contentDetails,statistics` and the returned ids. `maxResults=15` is our choice among the note's conflicting values (about 10 in §1, 25 in §4, 15 in §6).
- During the live smoke test, measure the empty-result rate of `safeSearch=strict` vs `moderate` on a fixed topic list including reproductive, breast and pelvic topics (strict may suppress legitimate anatomy lectures). Any change needs the user's yes.

#### Ranking and the channel allowlist (team-verified)
- One general search, then `videos.list` for duration and views.
- Filters [yt §4, §6]: duration 4-90 min (over 90 labelled "Long lecture"); view floor (the note suggests 5k; **target**, tune later); drop duplicates; drop titles matching a small clickbait list kept in the repo; drop blocklisted ids.
- Ranking rule (decision, one rule, tested): allowlisted channels first in API order, then non-allowlisted in API order; **at most 4 cards and at most 2 non-allowlisted cards in any case**. With an empty allowlist this shows 2 cards plus the search link. (The note's "cap non-allowlist items at 1" [yt §4] assumed a populated allowlist; with the default empty list it would show one card, and the draft's "fall back to API order" contradicted it. We chose 2 so the feature is useful before verification, and still mostly bounded.)
- **The allowlist is a team-verified file**, `api/data/video_channels.json`: `[{channel_id, name, verified_by, verified_on, note}]`. The research note lists candidate names only and deliberately gives **no** channel ids [yt §4]. This PRD gives none either. A person on the team opens each channel, confirms it is the real current one, and adds its id.
- We label the list "Suggested videos", never "YouTube's results" (III.C.5 [yt §2]).

#### Related topics
- **Data source (revised).** Related topics are our own certified content, so they do **not** come from `POST /api/videos`. The server computes them in the chat stream from the concept page data of the topic's concept (`api/concept_page.py`, links with `tier`) and sends them on the `topic` SSE event (above). They therefore render whether or not the `videos` flag is on, whether or not a YouTube key exists, whatever the quota, and without waiting for the lazy videos fetch. They do not count against the videos rate limit. Shared answers store the `related` list (our own data, no YouTube data) with the `topic`.
- Up to 6 `links_out` (tier `certified`) of the topic's concept, rendered as chips. A tap **appends a new turn to the current thread** (same as a typed follow-up) and scrolls to it; it never navigates away or replaces the thread. Each chip's tip mentions the concept page; the concept page link stays available on the answer's existing concept chips. `see_also` (tier `suggested`) is not used here.
- Placed in its own row inside the answer `<article>` (it is our own certified content), after `SpatialChips` and before the diagram slot, titled "Related topics (from the textbooks)". Rendered by `RelatedTopics.tsx` from `AnswerCard.tsx`, independent of `<Videos>`. Absent when `related` is empty, the answer is declined, or the question is patient-scoped (`topic: null`).

#### UX spec
- **Placement (revised)**: the videos section is a **sibling `<section aria-label="Suggested videos from YouTube, not checked by MedEvolv">` after the answer `<article>`**, not inside it, with a distinct border/background and its own heading, so it never reads as part of the cited answer [yt §4 "Never mix the cards visually into the cited-answer block"]. Only for non-declined, non-patient-scoped answers with a topic.
- **Fetch timing (decision D-3)**: fetched automatically after the `done` event, lazily when the section scrolls into view (IntersectionObserver), so quota is spent only on answers people read to the end. **Shared pages** store only the `topic` string in the share payload and call `POST /api/videos` live when the section scrolls into view (a cache hit within 7 days, otherwise a normal fetch under quota, or the fallback link).
- **Header (every state that shows anything)**: the official YouTube icon file from YouTube's brand resources, unmodified, not the most prominent element, linking to YouTube [yt §2], + "Suggested videos on YouTube".
- **Label (decision on copy)**: one string set, defined once in `web/lib/copy/videos.ts` and mirrored by `api/videos.py` for the API `label` field, both from a single JSON file `shared/copy/videos.json` read by both:
  - Always visible, one line: "External videos from YouTube. Not from your textbooks and not checked by MedEvolv."
  - Info tip and the `/terms` video section, **verbatim from the note** [yt §4]: "Suggested videos from YouTube. These are not from your textbooks, are not checked by MedEvolv, and may differ from the cited answer. Always trust the cited textbook passages first."
  - The one-line version is **adapted from [yt §4]** (shortened against banner blindness); it needs the user's approval as a copy change.
  - Terms line under the label: "By using video suggestions you agree to YouTube's Terms of Service" (link https://www.youtube.com/t/terms) and a link to `/terms` and `/privacy` [yt §2 III.A.1, III.A.2].
- Cards: horizontal scroll row on 390 px (snap, about 2.2 cards visible), up-to-4 grid at 1440 px. Each card: thumbnail `medium` 320x180, unaltered, `alt` = title, `loading="lazy"`, `referrerpolicy="no-referrer"`; title (2 lines); channel name; caption line "20:34 · 123K views"; external-link icon; a "Quick revision" caption for videos under 15 minutes. Duration goes in the caption, **not** on the image [yt §2]. The **thumbnail and title** are one `<a target="_blank" rel="noopener noreferrer">` to the watch URL (tip: "Opens this video on YouTube in a new tab."). A **separate sibling** overflow button (outside the `<a>`, 44 px target) holds "Report this video". No hover zoom on thumbnails at any motion setting; hover shows a border or shadow on the card.
- Trailing link: "Search YouTube for more" (fallback URL).
- States:
  | State | What shows |
  |---|---|
  | Loading | 4 skeleton cards; header, label and terms line already visible |
  | Ready | Cards + search link |
  | Empty (filters removed everything) | Header, label, terms line, "Search YouTube for <topic>" link |
  | Fallback (no key, quota, error) | Header, label, terms line, search link; no error copy (it is not the student's problem) |
  | No topic / declined / patient-scoped answer | Section absent |
  | Feature flag `videos` off, or `/api/features` failed (V-13) | Section absent; no `/api/videos` request. Related topics inside the answer are unaffected |
  | `/api/videos` returns 503 (flag flipped after load) | Section removed silently |
  | `/api/videos` returns 429 | Fallback state (header, label, terms line, search link) |
- Privacy notice: thumbnails load from `i.ytimg.com`, which sends the student's IP to Google [audit C]. `/privacy` says so. **Option (OQ-5)**: a one-time "Show videos" tap per session instead of auto-loading thumbnails; that tap would also be the explicit agreement point for III.A.
- Light/dark: card surface tokens; thumbnails unchanged.
- Accessibility: list semantics (`<ul>`), each link names "Video: <title>, <channel>, <duration>, opens YouTube in a new tab".

#### Functional requirements
- V-0 Search parameters exactly as listed above; a test asserts them.
- V-1 The API key lives only in the server `.env` (`YOUTUBE_API_KEY`); it never appears in the web bundle or responses. `deploy/v2/push.sh:27` currently copies only `DEEPSEEK_API_KEY` and `ATLAS_URL` into the deployed `.env`, so its grep is extended to `^(DEEPSEEK_API_KEY|ATLAS_URL|YOUTUBE_API_KEY|EVENTS_TOKEN|DIAGRAM_SIG_SECRET)=`. Feature flags are **not** in `.env` (§5.6).
- V-2 Cache hit: no YouTube call. Cache miss: exactly one `search.list` and one `videos.list`.
- V-3 Cached rows older than 7 days are refreshed on next use; rows older than 14 days are purged **on every write and at API startup** (`DELETE WHERE fetched_at < now - 14 d`; there is no scheduler). No YouTube API data (title, channel, thumbnail URL, statistics) is stored in any other table or file, including the `answers` table, events, logs and backups, so nothing older than 30 days can exist. Video ids are kept in the blocklist and feedback only if the verbatim re-read of III.E.4 allows indefinite id storage; otherwise they are purged at 30 days too (open item, recorded in §4.2 Data and licensing).
- V-4 A counter of `search.list` calls over a **rolling 24 h window**; at 80 the endpoint stops calling YouTube and returns the fallback until the window drops below 80. (The quota reset time is **UNKNOWN** [yt §6 says only "alert and degrade at 80 searches/day"]; a rolling window keeps every calendar day at or under 80 regardless of the reset time.)
- V-5 HTTP 403 `quotaExceeded`, missing key, timeout (async `httpx`, 3 s total, no thread) or any error → fallback response, HTTP 200.
- V-6 Single-flight per cache key (concurrent requests for the same topic share one upstream call).
- V-7 No user id, IP or question text is stored or logged with a topic [yt §2 health-data note]. The topic travels in a POST body (not a query string), so access logs never pair it with an IP.
- V-8 Thumbnails, titles and channel names are shown unmodified; each card links to the canonical watch URL.
- V-9 Related topics are certified links only, max 6, arrive on the `topic` SSE event (never from `/api/videos`), render regardless of the `videos` flag, key and quota, and a tap appends a new turn to the thread.
- V-13 **Flags on the client**: the videos section reads `useFeature('videos')` from the provider in D-15; when the flag is false or the features fetch failed, the section is absent and `POST /api/videos` is never called. A 503 at fetch time (flag flipped after load) removes the section silently. Related topics are not affected by this flag.
- V-10 `/privacy` and `/terms` exist and are linked from the videos section and the site footer before the flag is turned on.
- V-11 The label, the YouTube icon and the terms line are present in the Ready, Empty and Fallback states, and no video element is inside the answer `<article>`'s DOM subtree.
- V-12 A saved share payload contains no YouTube metadata fields (only `topic`).

#### API contract
`POST /api/videos` with body `{"topic": "<label>", "subject": "<optional>"}`

Response 200 (shape from [yt §6], with two additions: `label`, `long_lecture`; `related` was removed from this response and moved to the `topic` SSE event, V-9):
```json
{
  "topic": "nephrotic syndrome",
  "videos": [{
    "video_id": "...",
    "title": "...",
    "channel_title": "...",
    "channel_id": "...",
    "thumbnail_url": "https://i.ytimg.com/...",
    "duration_seconds": 1234,
    "duration_label": "20:34",
    "view_count": 123456,
    "watch_url": "https://www.youtube.com/watch?v=...",
    "allowlisted": true,
    "long_lecture": false
  }],
  "fallback_url": "https://www.youtube.com/results?search_query=nephrotic+syndrome+lecture+MBBS",
  "fetched_at": "2026-11-15T10:00:00Z",
  "source": "cache | api | fallback",
  "label": "External videos from YouTube. Not from your textbooks and not checked by MedEvolv."
}
```
(Values above are placeholders, not real videos. `label` comes from the shared copy file.)

Errors: 422 if `topic` missing or over 120 characters; 429 `rate_limited` at 30 requests/min per client IP [yt §6] through the shared limiter; 503 when the flag is off. Never 5xx for upstream trouble.

Storage: SQLite `video_cache(key TEXT PRIMARY KEY, json TEXT, fetched_at INTEGER)` and `video_search_log(ts INTEGER)` (for the rolling window; rows older than 24 h deleted on write) in `$APP_DB` [yt §6].

#### Data and licensing
- YouTube API Services Terms and Developer Policies apply [yt §2]: 30-day storage limit, attribution, unaltered thumbnails, links intact, a privacy policy users agree to (III.A.2), and a link to YouTube's Terms with a statement that users are bound by them (III.A.1). MedEvolv has no Terms page today (`apps/web/src/app` has no `terms` route), so `/terms` is new (§5.4).
- The note's clause readings come from fetched summaries; **re-read III.A, III.C.5, III.E.4 (including whether video ids may be kept indefinitely), III.F.2, III.I.4 and the branding guidelines verbatim before launch**, and record the result in the wiki [yt §6 open items].
- Pricing at default quota: likely free but unverified [yt §1].

#### Honesty and trust rules
- Videos are never inside the cited answer block and never feed the answer.
- The "not checked" label is always visible with the section.
- "Allowlisted" is internal ranking only; the UI does not say "recommended by MedEvolv". A reported or blocklisted video is never shown.
- Feedback: "Report this video" sends `POST /api/feedback` kind `video_bad` with `target_id = video_id` (§5.3), so the team can block it (`api/data/video_blocklist.json`).

#### Acceptance criteria
- Given a cited answer with topic "X" and a cold cache, when the section scrolls into view, then the server makes exactly one search (with the V-0 parameters) and one videos call, and up to 4 cards appear in a section outside the answer article, with the label, the YouTube icon and the terms line.
- Given the same topic again within 7 days, then no YouTube call is made (`source: cache`).
- Given the key is missing, then the header, label, terms line and "Search YouTube for X" show, and the page has no error.
- Given 80 searches in the last 24 h, then the response is `source: fallback`.
- Given a declined or patient-scoped answer, then no videos section exists.
- Given a card, when I tap the thumbnail or title, then YouTube opens in a new tab at the watch URL; when I tap the overflow, then only the report menu opens.
- Given a shared answer, then its stored payload has `topic` and no video fields, and the shared page fetches videos live.
- Given `/privacy` and `/terms`, then they name YouTube API Services, link Google's Privacy Policy (https://policies.google.com/privacy) and YouTube's Terms (https://www.youtube.com/t/terms), and `/terms` states that users of video suggestions agree to be bound by YouTube's Terms [yt §2].
- Given a related-topic chip, when I tap it, then a new turn is appended to the same thread.
- Given the `videos` flag is off (or no YouTube key, or quota used up), when a cited answer with a topic finishes, then the related-topics row still shows up to 6 certified chips inside the answer, and no videos section exists (flag off) or only the fallback shows (no key, quota).
- Given the `videos` flag is off, then no request to `/api/videos` is made on `/ask` or on a shared page.

#### Test plan
- `tests/test_api_videos.py` with the YouTube client mocked: exact `search.list` parameters; cache hit/miss call counts; TTL refresh; purge on write and startup; rolling-window degrade at 80; 403 quotaExceeded → fallback; timeout → fallback within 3 s; duration and view filters; ranking rule with an empty and a populated fixture allowlist (at most 2 non-allowlisted); blocklist; no question text or topic+IP pair in captured log records; 422/429/503; a share payload rejects or strips video fields.
- `tests/test_api_v2.py` (V-9 seam test, ontology fixture): the `topic` event carries `related` with only `tier: certified` links, at most 6 even when the concept has more, `related: []` with `topic: null` for a patient-scoped question, and the event order `answer, spatial, topic, done`. `tests/test_api_videos.py` asserts the videos response has no `related` key.
- Web unit test `RelatedTopics` helper (runner in §5.5): a tap builds a new turn for the same thread id (no navigation).
- One live smoke call after the user supplies a key (counts against quota; user yes), plus the strict vs moderate safeSearch comparison on a fixed topic list.
- Browser QA: 390 horizontal scroll, 1440 grid, light/dark, keyboard, screen-reader labels, report button not nested in the link.

#### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Quota exhausted | Topic cache, lazy fetch on scroll, degrade at 80 in any 24 h, fallback link; apply for an extension later [yt §1] |
| Bad or misleading medical video | `safeSearch=strict`, filters, team-verified allowlist, at most 2 unvetted cards, blocklist via reports, honest label |
| Policy breach | `/privacy`, `/terms`, attribution with the official icon, no thumbnail edits, no YouTube data outside the cache, verbatim re-read of clauses before launch |
| IP leak to Google via thumbnails | Disclosed on `/privacy`; OQ-5 opt-in tap |
| Future CSP blocks thumbnails | When a CSP is added, include `img-src https://i.ytimg.com` [audit C] |

---

### 4.3 R3: Tooltips on all buttons

#### Problem and user story
No tooltip primitive exists. The audit's regex count found about 82 JSX control sites, about 67 without a `title` or `aria-label` [audit D]. The count is approximate: the audit's own table is inconsistent (the AtlasView row lists line 183, Isolate, as unlabelled while noting Isolate has a `title`), and it advises treating "about 80" as the working number and 62-65 as the real set [audit D caveats]. `check-tips.mjs`'s first run is the real baseline. Students meet controls like "Isolate", "Layers", "Default", citation numbers and story rail dots with no explanation.

> As a student, when I hover or focus any control, I want to read what it is for and what will happen, so I can use features confidently.

#### Tooltip primitive (`web/components/ui/Tooltip.tsx`)
- Opens on pointer hover after **500 ms** (target) and on **keyboard focus** (`:focus-visible`) after 0 ms; closes on pointer leave (with 100 ms grace so the pointer can move onto the tooltip), blur, and **Escape**. This meets WCAG 2.1 SC 1.4.13 (dismissible, hoverable, persistent).
- **ARIA**: the description is rendered **persistently** in a visually hidden element with a stable id, referenced by `aria-describedby` at all times, so screen readers announce it on focus without waiting for a mount. The visible bubble (`role="tooltip"`) is a separate presentational layer. The tooltip text is the *description* (purpose + effect); the *name* stays the visible label or `aria-label`.
- **Disabled controls**: controls with a disabled reason use `aria-disabled="true"` (still focusable and hoverable, click suppressed in the handler) instead of the `disabled` attribute with `disabled:pointer-events-none` (`ui/Button.tsx` base class). One element, one ref, hover and keyboard both get the reason. No wrapper span.
- **Touch** (decision, revised): a tap always activates the control and never shows a tooltip first. **Long-press-to-tip applies only to icon-only `<button>`s**, never to links or `LinkButton`. It is built from `pointerdown`/`pointerup` with `pointerType === 'touch'` and a 500 ms timer, and it **never calls `preventDefault` on `click`**, so a screen reader's double-tap (which arrives as a synthetic `click`, not a long touch) always activates the control. No screen-reader detection is attempted (browsers do not expose it reliably). The long-press only shows the tip if the finger is still down at 500 ms and has moved under 10 px; releasing after a long-press does not fire the action (the `click` that follows a long-press is suppressed only when the tip was shown by that same pointer). `-webkit-touch-callout: none` is never set on `<a>`. Touch users get the purpose from the accessible name and description, from **first-use coach marks** and from the atlas "?" toggle (below).
- **Coach marks** (`web/components/ui/CoachMark.tsx`, WS-K owns the component only): on touch devices, the non-obvious controls show a one-time, dismissible bubble the first time they are on screen. Each coach mark is **placed and owned by the workstream that owns the feature**, and exists only while that feature is live: Isolate (WS-A), citation chip and "Why was I wrong?" (WS-K, in the P0 sweep), "Flowchart" (WS-X, only when `diagram` is on), "Male / Female" (WS-A, only when `female_atlas` is on). Under OQ-8 = B only the first three ship. Seen state is remembered in `localStorage` (try/catch; failure means it shows again, harmless). The atlas toolbar also gets a small "?" toggle that shows all toolbar labels inline.
- Rendering: a portal to `document.body` (avoids clipping inside `Drawer` and overflow containers [audit D]); position above the trigger, flipping below near the top edge; max width 280 px; **never overlaps its own trigger, nor a video card's thumbnail or title** (it flips or shifts instead); kit tokens for light/dark; no animation under reduced motion, otherwise a 120 ms fade.
- One tooltip open at a time (a module-level store).
- Client boundary: `Button.tsx` and `Chip.tsx` become `'use client'` components (they are not today). `tip` accepts only a `TipId` string or a plain `{purpose, effect, disabled?}` object, so server components such as `not-found.tsx` can pass it.
- `Chip` with `href` currently drops `...rest` on links; fixed so ARIA and data props reach the element.
- Zero new dependencies. Native `title` is removed where a tip exists (no double tooltips).

#### Copy registry (`web/lib/tips/*`)
Split per feature so each workstream owns its file: `tips/atlas.ts` (WS-A), `tips/answer.ts` (WS-X), `tips/landing.ts` (WS-L), `tips/shell.ts`, `tips/why.ts`, `tips/explore.ts`, `tips/story.ts` (WS-K), re-exported with one merged `TipId` type by `tips/index.ts`.
```ts
// tips/atlas.ts
export const ATLAS_TIPS = {
  'atlas.isolate': { purpose: 'Shows only the selected structure.', effect: 'Hides everything else. Tap again to bring the body back.', disabled: 'Select a structure first.' },
  'atlas.reset':   { purpose: 'Goes back to the whole-body starting view.', effect: 'Clears your selection and Isolate. Layers stay as you set them. You can undo.' },
  'atlas.layers':  { purpose: 'Chooses which body systems are visible.', effect: 'Opens the layer list.' },
} as const satisfies Record<string, Tip>;
```
Copy rules (in the file header, checked in review):
1. Never repeat the visible label ("Send: Sends" is not allowed).
2. Every tip states **purpose and effect** (the user's requirement). For obvious controls (Send, Cancel, Close) these may be one combined sentence, for example Send: "Sends your question; the cited answer appears below."
3. Effect-first wording for non-obvious controls.
4. Data tips where they help: the citation chip shows its pointer, for example "Harrison 22e · Ch N · p N. Opens the source." (values from the citation); story rail dots show the chapter title.
5. Plain words, at most about 20 words, no jargon a first-year would not know.
- **Approval in two tiers**: the user reviews the about 20 non-obvious tips (atlas toolbar, citation chip, Why was I wrong?, Flowchart, videos, Male/Female, Isolate, Reset); the lead agent reviews the rest against the rules.

#### Kit integration (pit of success, staged)
- `Button`, `LinkButton`, `Chip` (when it renders a `button` or link) and `CitationChip` get a new **optional** prop `tip: TipId | { purpose: string; effect: string; disabled?: string }` in P0. Making it required on day one would turn about 70 existing call sites in about 28 files into TypeScript errors at once [audit D] and block G1 between the primitive and the sweep.
- `apps/web/scripts/check-tips.mjs` (TypeScript compiler API, already a dev dependency) scans `apps/web/src` and reports a gap for:
  - a kit control (`Button`, `LinkButton`, `Chip`, `CitationChip`) without `tip`;
  - a raw `button`, `a`, `Link`, or any element with `role="button" | "radio" | "option" | "tab"`, or `input[type=radio|checkbox]`, that is not wrapped in `<Tooltip>` and does not carry `data-tip-id`;
  - `tip={NO_TIP}` without an adjacent comment.
  It compares gaps with the committed `apps/web/scripts/tips-baseline.json` and **fails only on new gaps** (and on baseline entries that no longer exist, so the file shrinks honestly). The sweep shrinks the baseline to empty. A final one-line PR then makes `tip` **required**.
- Script wiring: `"check:tips": "node scripts/check-tips.mjs"` and `"check": "tsc --noEmit && node scripts/check-tips.mjs"` in `apps/web/package.json`. **Not** `pnpm lint`: `lint` is `next lint`, and `apps/web` has no ESLint config and no `eslint` dependency, so `next lint` would prompt to set up ESLint instead of running. Adding ESLint would be a new dev dependency needing the user's yes; not planned.
- Fixture tests for the script: one `.tsx` fixture per rule (kit control, raw button, link, `role="radio"`, `input[type=radio]`, `role="option"`, `NO_TIP` without comment) must fail; a compliant fixture must pass.
- **Markdown citation chips**: `Markdown.tsx` emits the inline `[n]` buttons as HTML strings through `dangerouslySetInnerHTML` (`ui/Markdown.tsx:38`, `:68`), so neither the prop nor the scan can see them. They get a **delegated tooltip**: one listener on the `.md` container reads `data-cite` and shows "Source n: Book ed, ch, p. Opens the source." (data from the answer's citations), with the description also placed in `aria-describedby` of each generated button.
- Non-button controls in the sweep: `WhyForm.tsx:63` radio inputs, `role="radio"` in `Actions.tsx:83`, `role="option"` results (`AtlasView.tsx:167`, `ExploreView.tsx:199`).
- Imperatively created controls inside three.js scenes (the atlas hover label [audit D]) are out of the scan; they are listed by hand in `tips/atlas.ts`.
- CI: none exists today (no `.github/`). The strategy review's CI job [strategy C1] would run `pnpm check`; until then the gate is the agent running G1 locally.

#### Coverage target
**100% of sites** (baseline empty) plus everything added this release (R1, R2, R5, Landing). Runtime instances from `.map`s (story rail, atlas layer toggles, `KINDS` radios) get dynamic tips.

Priority order for the sweep: icon-only controls; answer card actions (`Actions.tsx`, `Cards.tsx`, `SourceList.tsx`, `CitationChip.tsx`, Markdown cite chips); Why flow (`WhyForm.tsx`, `VerdictCard.tsx`, `WhyView.tsx`); Explore (`ConceptView.tsx`, `ExploreView.tsx`); shell nav; story; rest. The atlas toolbar is done by WS-A right after R4.

#### Functional requirements
- T-1 Kit controls accept `tip`; at release, `tip` is required and the type check fails without it.
- T-2 `pnpm --dir apps/web check` fails on any gap not in the baseline; the baseline is empty at release.
- T-3 Hover 500 ms shows the tip; focus shows it at once; Escape closes it; moving onto the tip keeps it open.
- T-4 Long-press 500 ms (touch pointer, under 10 px movement) on an icon-only `<button>` shows the tip and does not activate it; a normal tap and a synthetic `click` (as sent by a screen reader's double-tap) always activate it; links and `LinkButton` never get long-press handling and keep native long-press behaviour. Tested in the web unit runner with synthetic pointer events (§5.5) and in G2 with VoiceOver on iOS.
- T-5 Every control with a tip has a stable `aria-describedby` pointing at a persistent description; the visible bubble has `role="tooltip"`.
- T-6 Tooltips are not clipped inside `Drawer` or scroll containers, and never cover their trigger or a video thumbnail or title.
- T-7 Disabled controls (via `aria-disabled`) show their `disabled` reason on hover and focus.
- T-8 No control has both a native `title` and a tip.
- T-9 Each coach mark whose feature is live shows once per browser on touch and can be dismissed; a coach mark for a feature that is off (flag false or not shipped) never renders.

#### API, data, licensing
None.

#### Honesty and trust rules
Tips describe actual behaviour. When behaviour changes (for example R4), the tip changes in the same PR; reviewers check the tips diff.

#### Acceptance criteria
- Given any control on desktop, when I hover for half a second, then I see what it is for and what will happen.
- Given I tab to "Reset view", then its tip appears immediately and a screen reader announces "Reset view" followed by the description.
- Given a phone, when I tap "Layers", then the layers open with no tooltip; the first time I see Isolate, a coach mark explains it once.
- Given a phone, when I long-press a source link, then the native link menu appears.
- Given Isolate with nothing selected, when I tab to it, then the tip says "Select a structure first."
- Given a developer adds `<Button>Foo</Button>` with no `tip`, or a raw `<button>` with no tooltip, then `pnpm --dir apps/web check` fails.

#### Test plan
- `check-tips.mjs` fixture tests (above).
- Browser QA: hover, focus, Escape, long-press (mobile emulation), coach marks, inside the source Drawer, near the screen edge, dark mode.
- Screen reader spot check (VoiceOver on macOS and iOS; TalkBack if a device is available) on 5 controls including a disabled one and a Markdown cite chip.

#### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Tooltips are useless on touch, the main audience | Coach marks on the 5 non-obvious controls, accessible names and descriptions, "?" toggle in the atlas toolbar |
| Long-press breaks native link menus or assistive gestures | Long-press only on icon-only buttons; never on links; `click` is never cancelled, so assistive double-tap always activates (T-4) |
| Filler copy | Copy rules; two-tier approval |
| Sweep touches files other workstreams own | Ownership table 1.3; per-feature tip files |
| Big-bang type errors | Optional prop plus baseline, required only when the baseline is empty |

---

### 4.4 R4: Atlas "Reset view" really resets

#### Problem (confirmed bug)
`Reset view` calls `reset()` from the store (`AtlasView.tsx:194`), which only bumps `resetNonce` and sets `isolate: false` (`atlas-store.ts:61`). The scene then re-frames `partIdxRef.current`, the **current selection** (`AtlasScene.tsx:502-506`). With a structure selected, the result is "Isolate turns off and the camera re-frames the same structure"; the selection and `?select=` stay [audit E]. Confirmed again in the code at `e0eec26` while writing this PRD.

> As a student who has zoomed into a structure, when I press Reset view, I want to be back at the starting whole-body view, and to undo it if I pressed it by mistake.

#### Definition of "default view" (decision D-4)
The default view is the state of `/atlas` opened with no query parameters, after load, **for the current visible layers and current inset**:
1. **Selection**: empty; `?select=` removed from the URL.
2. **Isolate**: off.
3. **Camera**: the goal pose of `frame3([], true)`: bounding box of the visible (`wanted`) non-integumentary parts, view direction `(0.32, 0.08, 1)` normalised, distance `max(fitH, fitW, size.z*0.9) * 1.18 + size.z/2` (min 1), shifted by the panel inset via `setViewOffset` [audit E "Default camera pose"; `AtlasScene.tsx:298-305` uses `wanted`]. `userMoved` reset to false. If layers were changed, the framing follows the visible layers (so it can differ from a fresh load with default layers; that is intended).
4. **Layers**: **unchanged** (Layers has its own "Default" button, `resetLayers` [audit E fix step 2]). The tip says so.
5. **Sex (after R5)**: unchanged; Reset resets the view of the current model, using that model's default (§4.5).
6. **Hover/explosion state**: cleared if any (ASSUMPTION: verify `explosion-layout.ts` has a resettable state; if it has none, nothing to do).

#### Fix (from [audit E "Minimal correct fix"])
1. `AtlasView.tsx:194`: `onClick={() => { snapshotForUndo(); setSelection([]); reset(); }}`. `setSelection` (AtlasView.tsx:51-56) strips `?select=` via `router.replace`, and is changed to **preserve other query params** (needed for R5's `?sex=`; today it rewrites the query with only `select` [audit F]).
2. Keep `isolate: false` in the store `reset` (`atlas-store.ts:61`).
3. Hardening: in `AtlasScene.tsx:502-506`, the reset branch calls `frame3([], true)` (whole body) instead of `frame3(partIdxRef.current, true)`, so the pose is correct even if the selection update lands a frame later or an embed controls selection elsewhere. `router.replace` is asynchronous; this removes the ordering dependency between the URL update and the nonce. It is not a timing workaround (no `setTimeout`), which the engineering principles forbid [engineering-principles §1].
4. **Undo**: before resetting, store `{selection, isolate, camera goal pose}`; show a toast "View reset" with an **Undo** action for 5 s; Undo restores all three. The toast is the polite live-region announcement. **Verified gap**: the existing toast has **no action button**: `store/ui.ts:10, :17-20` defines `toast(text: string, ms = 2600)` holding only `{id, text}`, and `ui/Toast.tsx` renders `t.text` in a `pointer-events-none` container (children re-enable pointer events). The timeout (`ms`) already exists. WS-K therefore adds an optional `action: {label, onClick}` to `toast()` and renders it as a kit `Button` (with a tip, 44 px target, keyboard reachable) in P0 before R4 (§1.3, §1.2a). Until it lands, R4 ships without Undo only if the user agrees; otherwise R4 waits.
5. Tip copy updated (`atlas.reset` in `tips/atlas.ts`).

Size: S (a few lines plus checks) [audit E].

#### UX spec
- Same button and place (toolbar, AtlasView.tsx:183-199). Camera tweens to the pose with the existing lerp; under reduced motion it jumps.
- States:
  | State | Behaviour |
  |---|---|
  | Manifest still loading (no atlas yet) | Reset is `aria-disabled` with the disabled tip "Atlas still loading"; clicks do nothing; enabled when the atlas-ready signal fires |
  | Loaded, nothing selected, Isolate off, camera untouched | Enabled; pressing it re-frames the whole body (as today) and shows no Undo toast (nothing to undo) |
  | Loaded, with a selection or a moved camera | Enabled; resets and shows the Undo toast |
  | Female model downloading (after R5) | `aria-disabled`, tip "Atlas still loading" |
- Mobile: the bottom-sheet inset is applied inside `frame3`, so the pose respects it [audit E edge cases].
- Accessibility: after reset, focus stays on the button; the toast is announced politely; Undo is keyboard reachable.

#### Functional requirements
- RV-1 After Reset, the URL has no `select` parameter; other parameters are preserved.
- RV-2 After Reset, `isolate` is false and no structure is highlighted.
- RV-3 After Reset, the scene's goal pose (`goalTarget`, `goalPos`) equals the goal pose of `frame3([], true)` for the current visible layers and current inset, within 1e-6. (Comparing the live camera after the tween would need a 5e-3 tolerance, because the tween stops within 0.002/0.004 of the goal.)
- RV-4 Visible layers are unchanged.
- RV-5 Reset twice in a row is harmless.
- RV-6 Undo within 5 s restores selection, Isolate and the previous goal pose.
- RV-7 Before the atlas manifest has loaded, Reset is `aria-disabled` with the tip "Atlas still loading" and does nothing.

#### Acceptance criteria
- Given `/atlas?select=FMA62045` with Isolate on and the camera rotated, when I press Reset view, then the URL becomes `/atlas`, Isolate is off, nothing is selected, and the whole body is framed as on a fresh load with the same layers.
- Given I hid two systems in Layers, when I press Reset view, then they stay hidden and the framing fits the visible systems.
- Given a 390 px screen with the selection sheet open, when I press Reset, then the sheet closes (no selection) and the body is framed above the inset.
- Given I pressed Reset by mistake, when I tap Undo, then my selection, Isolate state and view come back.
- Given `/atlas` is still loading its manifest, when I focus Reset view, then its tip says "Atlas still loading" and pressing it does nothing.

#### Regression test
There are no web tests today [audit E]. Add the first one as a Playwright test (see §5.5) `apps/web/e2e/atlas-reset.spec.ts`: open `/atlas?select=FMA62045`, wait for the atlas-ready signal, click Isolate, drag to rotate, click Reset, assert the URL, and read the **goal pose** through a test-only `window.__atlasDebug` getter (exposes `goalTarget`, `goalPos` and a `computeDefaultGoal()` helper), compared within 1e-6 (RV-3). Then click Undo and assert restoration.
Run recipe (documented in `apps/web/e2e/README.md`): `scripts/fetch-models.sh` (about 90 MB of local models, a download needing the user's yes the first time); `NEXT_PUBLIC_E2E=1 pnpm --dir apps/web build && pnpm --dir apps/web start` (a separate non-production build); Chromium with `--use-angle=swiftshader` for headless WebGL. The test is skipped with a clear message when `/models/atlas.json` is unreachable. G2's manual check on the production build stays the production check.

**Model-free unit test (runs in G1 whatever OQ-12 says).** WS-A extracts two pure modules so Reset can be tested without models or WebGL: `web/lib/atlas-reset.ts` exports `resetIntent(prev)` returning `{selection: [], isolate: false, frameParts: [], undo: {selection, isolate, goal}}`, which both the `AtlasView` click handler and the `AtlasScene` reset branch use; and `web/lib/atlas-camera.ts` exports `computeGoalPose(boxes, visible, inset)` (the `frame3` math from `AtlasScene.tsx:298-305`, using three.js math classes only, which import in Node). `AtlasScene`'s reset branch (`AtlasScene.tsx:502-506`) calls `computeGoalPose` with `resetIntent(...).frameParts`, i.e. `[]` (whole body). `web/lib/atlas-reset.test.ts` asserts: the intent clears selection and isolate; `frameParts` is `[]` even when a selection exists; two resets in a row give the same intent (RV-5); the undo snapshot holds the previous selection, isolate and goal; and `computeGoalPose` on a three-box fixture with `[]` equals the whole-visible-bbox pose within 1e-6 and differs from the pose for one selected box. **ASSUMPTION**: the `frame3` math can be extracted without scene objects; if it cannot, WS-A records why in the PR and the unit test covers `resetIntent` only.

#### Pre-demo option
This is the only change that could ship before 17 Nov, and only with the user's explicit yes. Recommendation: **do not** ship before the demo (see OQ-4). The bug is cosmetic; the demo freeze protects a rehearsed flow [strategy §1 "17 Nov demo: change nothing"].

#### Risks
| Risk | Mitigation |
|---|---|
| `setSelection` rewrite drops other params | RV-1, tested |
| Embeds (`Concept3D`) share the store and get reset unexpectedly | Reset is only wired in `AtlasView`; check `Concept3D` in QA |
| Reset loses a selection the student wanted | Undo toast (RV-6) |

---

### 4.5 R5: Female 3D atlas

#### Problem and user story
The atlas is BodyParts3D, an adult **male** reference (CC BY 4.0, 2,234 meshes, 3,432 FMA concepts) with no uterus [audit F; `deploy/atlas/ATTRIBUTION.md`]. It "is not a complete model of every possible human anatomical structure or variation" (`ATTRIBUTION.md:16`). Students studying the female pelvis or breast get no 3D view, and answers on those topics get no "View in 3D" link by design [fem §6].

> As a student studying female anatomy, I want to switch the atlas to a female model, so I can see the uterus, ovaries, tubes and breast in 3D.

#### Source model (from [fem §3.1])
- **HRA "3D Reference Organ Set for United, Female" v1.5** (Visible Human Female), CC BY 4.0 (confirmed 2026-11-15 in graph.json, the GitHub repo and an NIH 3D entry).
- GLB: `https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb`, **211,624,968 bytes (about 202 MB)** by HEAD request on 2026-11-15, last-modified 2026-06-10.
- 1,073 nodes, 888 mesh nodes (606 non-brain, 282 `Allen_*` brain meshes), about 5.56 M triangles before welding (about 2.4x the male atlas).
- Female-specific coverage includes vagina, cervix, uterus (body, fundus, walls, lower segment), ovaries, fallopian tubes and parts, ligaments, uterine vessels, breast structures, and 8 placenta/umbilical items. **No vulva, clitoris or labia nodes were found.**
- **It is NOT a full female twin of BodyParts3D.** No skull, mandible, ribs, sternum, clavicle, scapula, arm bones, hand or foot bones were found, and only about 20 "muscle" names exist. Skeleton and muscle coverage is partial [fem §3.1 gaps; ATTRIBUTION.md].
- Different subject, scale, pose and coordinate frame from the male model; never overlay or morph them [fem §8].
- Mesh-level ids are **not** provided in the GLB (names only); our own name-to-id mapping is needed [fem §3.1, §8].
- **Subject (conflict, UNVERIFIED)**: fem §8 calls it "single-subject, cadaver-derived"; our own `ATTRIBUTION.md:29` says of this dataset "It is not a complete model of every human structure or a single-person scan" (the brain, for example, comes from the Allen atlas). Resolve against the HRA metadata or the DOI page before any user-facing copy says "one body".

#### Download needing the user's yes
| Item | Value |
|---|---|
| URL | `https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb` |
| Size | 211,624,968 bytes (about 202 MB), as of 2026-11-15 HEAD |
| Destination | `~/Projects/third_party/hra-vhf/` on the Mac (not in the repo) [fem §5.1] |
| Record | sha256 and download date into `deploy/atlas/ATTRIBUTION.md` |
| Also needed | Later upload of the converted female chunks (estimated about 30 MB gzip, not measured [fem §7]) to `/srv/atlas` on the VM, also needing a yes; VM free disk space is **UNKNOWN**, check first |

#### Conversion pipeline (from [fem §5], owned by WS-A)
1. Download (above), record sha256.
2. `deploy/atlas/female/convert_glb.mjs` (Node, `@gltf-transform/core`, a build-only dependency outside `apps/web`). **Units and axes are UNKNOWN**: fem §5 step 2 and `ATTRIBUTION.md:27` say "native meter/Y-up coordinates", while fem §8 says the HRA placement metadata uses a -90° X rotation and millimetres. So the converter's **first step is a bounds check**: print the GLB accessor min/max after baking node transforms, compare the extent with the metadata bounding box (about 967 x 1666 x 329 mm [fem §3.1]), decide the scale (1 or 0.001) and up-axis from the measured extent, and **fail** if neither interpretation matches within 5%. Then for each mesh node: bake world transforms; name = node name minus `VH_F_`, underscores to spaces, `_L`/`_R` to Left/Right; translate feet onto the stage (recompute from the female bounds); write the manifest in the exact `Part` layout (float32 positions, int16 normals, uint32 indices, byte offsets, `bounds`) [audit F schema].
3. Id mapping `deploy/atlas/female/id_map.csv` (`mesh_name, concept_id, concept_name, source, reviewed_by`):
   - Pass 1: automatic exact and variant matches against BodyParts3D FMA names (`rag.atlas.variants`) and the per-organ HRA UBERON/FMA labels.
   - Pass 2: hand-curate the clinically important set (uterus parts, ovary, tube, vagina, cervix, breast, ligaments; about 100 names [fem §5.3]).
   - No FMA match: synthetic ids that survive our matchers: **uppercase, no spaces or commas**, for example `UBERON:0000995` or `HRA:VH_F_UTERUS_BODY` (`normalizeFma()` uppercases, `anatomy.ts:209-212`, and the `?select=` parser splits on commas). Matcher tests cover both forms.
   - Clean known odd names (for example `jejenum`, `eigth thoracic spinal cord segment`) in display names [fem §8].
4. Systems: map `VH_F_<system>` parents to the 15 display systems; add "Reproductive (female)" and a "Pregnancy reference" system for placenta items, hidden by default [fem §5.4]. Extend the fixed system enum in `anatomy.ts` [audit F].
5. Name the manifest `female.json` in the human-atlas `public/models/`, and run `node scripts/optimize-anatomy.mjs female.json` there: the script picks the `female` prefix from the manifest name (`name.includes('female')`, `optimize-anatomy.mjs:4`), welds and averages normals, simplifies at 0.2%, and writes `female-N.bin`; then `compress-models.mjs` for `.gz` [fem §2, §5.5].
6. `validate-atlas.mjs`; visual QA; spot-check 20 clinically important structures by name and position.
7. Size check against the budget below; record measured sizes in the wiki.

Manifest: `models/female.json` + `models/female-N.bin(.gz)` (the names the script produces), with `sex: "female"`, `source: "HRA VH_F united v1.5"`, and a distinct `version` (so IndexedDB chunk keys `${version}:${url}` do not collide [audit F]).

#### Deploy path (runbook, P3)
- **Model files**: `/models` is served from the human-atlas `dist/`, which `deploy/atlas/push_atlas.sh` rsyncs with `--delete`, so a manual upload of female files would disappear on the next atlas push. The female files are therefore produced inside the human-atlas build (`deploy/atlas/build_atlas.sh` gains the female steps) and shipped by `push_atlas.sh`, after checking VM free disk. User yes required.
- **Crosswalk rows (F-4)**: `data/graph/atlas_crosswalk.jsonl` is git-ignored (`.gitignore:28` `/data`) and baked into the `eka-app` image, which the v2 API image is built `FROM` (`deploy/v2/Dockerfile.api:3`). Shipping new rows needs `deploy/oci/push.sh` plus an image rebuild, which also redeploys the Streamlit fallback, and is not part of `push.sh`'s `API_SHA`. This is its own user-approved deploy with a smoke test of both the v2 API and Streamlit.
- **Manifest compression**: `atlas.json` (1,335,285 bytes in the local build) has no `.gz` sibling; add `atlas.json.gz` and `female.json.gz` to the build (`compress-models.mjs`), so the `/models` handle's `precompressed gzip` serves them compressed. Also benefits `/atlas` today.

#### Size budget
- **Target: at most 35 MB gzip** for the female chunks with the brain included; the note estimates about 30 MB, unmeasured [fem §7].
- If over budget: move the 282 `Allen_*` brain parts (0.65 M source triangles) into a separate optional chunk group behind "Brain detail" [fem §7], or use a stricter simplification error for small parts.
- Loaded only when the student confirms the Female download; only one model resident in the scene at a time [fem §6].

#### UX spec
- Toolbar segmented control **"Male | Female (organs)"** next to Isolate / Reset view / Layers (AtlasView.tsx:183-199) [audit F]. Tips: "Male: BodyParts3D adult male reference (2,234 parts)." / "Female: Visible Human Female reference organs. Skeleton and muscles are partial."
- URL `?sex=female|male`; default male; the last choice is remembered in `localStorage` as a per-browser convenience; links without `sex` keep working [fem §6]. A `?select=` link always wins over the stored preference (see auto-switch).
- **First-download confirm**: before the first female download in a browser, a sheet: "Download the female model (about N MB)? Best on Wi-Fi. [Download] [Not now]", with N from the manifest's `gzipBytes` total. When `navigator.connection` reports Save-Data or a 2g/3g `effectiveType`, "Not now" is the focused default. The download shows progress, can be cancelled, and resumes from the IndexedDB chunk cache.
- **Female default view** (extends D-4 per model): frames the torso and pelvis, with Reproductive (female), Urinary and the pelvic bones visible. Skin is **off by default** on both models (as today: `DEFAULT_VISIBLE` excludes integumentary, `anatomy.ts:94-109`); this is stated in the spec because classroom and phone screenshots of a skin surface are a real concern for students. A faint skin silhouette option is out of scope.
- Note under the toggle when Female is on: "Female model: Visible Human Female reference organs. Skeleton and muscles are partial; external genitalia are not included."
- Switch behaviour: dispose current scene buffers, load the other manifest with progress, keep the selection if the same concept id exists in the target model, otherwise clear it and show a toast "<structure> is only in the Male model [Switch back]" (or the female equivalent). Camera goes to that model's default view.
- **Auto-switch (symmetric)**: if `?select=` names a concept missing from the loaded model and present in the other, switch to the other (with a toast saying so). If the switch needs the first female download, show the confirm sheet first.
- Error: if the female manifest or chunks fail, toast "Couldn't load the female model" and stay on Male.
- 390 px: segmented control fits in the wrapping toolbar row.
- Light/dark and reduced motion: as the existing atlas.
- Attribution: female credit on `/credits`, in the atlas credit line while Female is active, and in `ATTRIBUTION.md` (§4.5 Data and licensing; C1 in §5.1).
- **Flag gating**: the Male/Female control, the confirm sheet, the female auto-switch and female "View in 3D" links exist only when `female_atlas` is true (D-15 provider). With the flag false: no toggle, `?sex=female` is ignored (Male loads, URL param removed with `router.replace`, no toast), a `?select=` naming a female-only id shows the existing "not found" behaviour for that id, and `atlasHref` never adds `&sex=female`.
- **Accessibility**:
  | Element | Spec |
  |---|---|
  | Male/Female control | `role="radiogroup"` with `aria-label="Body model"`; two `role="radio"` items with `aria-checked`; one tab stop (roving `tabindex`); Left/Right and Up/Down arrows move and select; Space selects; each item has a tip (R3) and a visible text label (not icon only); 44 px targets |
  | Confirm sheet | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` the sheet title; focus moves to "Download" (or to "Not now" under Save-Data/2g/3g); Tab is trapped inside; Escape = "Not now"; on close, focus returns to the Female radio |
  | Download progress | A `role="progressbar"` with `aria-valuenow` (percent) and an `aria-valuetext` such as "12 of 30 MB"; a polite live region announces only at 25%, 50%, 75% and "Female model ready" (no per-chunk chatter); "Cancel" is a kit `Button` with a tip and stays focusable during the download |
  | Switch toasts | Use the polite toast live region; the "Switch back" action is keyboard reachable (toast `action`, §4.4) |
  | Female note under the toggle | Plain text, associated with the radiogroup by `aria-describedby` |

#### Functional requirements
- F-1 `atlas-store` holds `atlases: Record<Sex, Atlas | null>` with per-sex inflight guards and `loadManifest(sex)`, replacing the single-atlas guards (`if (get().atlas) return`, `inflight`) [audit F; `atlas-store.ts:35-55`]. `AtlasView`, `Concept3D` and `chiasm` each request the sex they need.
- F-1a The IndexedDB manifest cache is keyed per sex (`atlas.json:male`, `atlas.json:female`) and falls back only to the same sex; today it uses the single key `'atlas.json'` and falls back to it on fetch failure (`atlas-store.ts:45-49`), which could silently load the male manifest while the UI says Female.
- F-2 `?sex=` round-trips; selection changes preserve it (RV-1).
- F-3 Switching re-resolves selection by concept id, never by part index [audit F risk].
- F-4 Female-only crosswalk rows in `data/graph/atlas_crosswalk.jsonl` carry `sex: "female"`; `/api/spatial/resolve` and `atlasHref` add `&sex=female` for them, so answers about uterus or ovary get a working "View in 3D" link. Shipped through the eka-app rebuild (deploy path above).
- F-5 Placenta/umbilical parts hidden by default.
- F-6 Male behaviour is unchanged when `sex` is absent.
- F-7 `Concept3D` and `story/chiasm.ts` request the male atlas unless explicitly given a sex, regardless of what `/atlas` last loaded.
- F-8 The first female download asks first (confirm sheet) and is cancellable.
- F-9 With `female_atlas` false or the features fetch failed, the Male/Female control, confirm sheet, auto-switch and female links are absent, and `?sex=female` loads Male without error (flag gating above).
- F-10 The Male/Female control and confirm sheet meet the accessibility table above (radiogroup semantics, arrow keys, focus trap and return, progress announcements).

#### API contract
No new endpoint. `GET /api/spatial/resolve` response gains `sex: "male" | "female"` per structure (additive). `SpatialAction` gains optional `sex` so "View in 3D" chips link to the right model (`api/schemas.py`, handed from WS-X to WS-A in P3).

#### Data and licensing
- CC BY 4.0, no share-alike [fem §4].
- **Credit text** (adapted from [fem §4]; exact required credit **UNVERIFIED** until the DOI page is opened): "Kristen Browne and Heidi Schlehlein, Human Reference Atlas / HuBMAP, *<title>*, v1.5. CC BY 4.0. https://doi.org/10.48539/HBM352.BTSQ.586. Source geometry: https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb. Adapted: <full change list>." Title candidates, to be settled on the DOI page: "3D Reference Organ Set for United, Female" [fem §3.1, §4] or "3D Reference Organ Set for Female v1.5 (2023)" (`ATTRIBUTION.md:20`).
- **Full change list** (CC BY requires changes to be indicated): units and axes converted (per the bounds check); re-centred and placed on the stage; vertex-welded and normals averaged; simplified at a 0.2% per-structure error bound; normals quantised to 16 bit; re-packed into chunk files; mesh names cleaned and renamed for display; meshes mapped to FMA, UBERON or HRA ids by us; display systems regrouped and colours added; brain meshes split into an optional group (if done).
- Also credit the NLM Visible Human Project and the Allen Institute brain atlas, as the HRA metadata does. The Allen brain licence is known only second-hand ("NIH 3D says the brain moved to CC BY 4.0 in v1.3" [fem §3.1]): **verify on the HRA DOI page before shipping, or ship without the `Allen_*` meshes.**
- `ATTRIBUTION.md`: move the female section from "Historical assets (not included in the current release)" into the current-release part, with the sha256 and date.
- Do not imply endorsement by HuBMAP, NIH or DBCLS.
- Model files stay out of git (as the male set) [audit A].

#### Honesty and trust rules
- The UI states the female model's gaps (partial skeleton and muscles; no external genitalia); never call it "complete".
- About/credits copy until the subject question is resolved: "A reference assembly; real anatomy varies." No "one body" claim until verified.
- Mapped ids that were not hand-reviewed are not used for answer "View in 3D" links (only `reviewed_by` rows feed the crosswalk).

#### Acceptance criteria
- Given `/atlas`, when I pick Female for the first time, then a confirm sheet shows the download size; when I confirm, the female model downloads with progress, renders the torso/pelvis default view, and the URL shows `?sex=female`.
- Given the female model, when I search "uterus", then I can select it and Isolate works.
- Given `/atlas?select=<uterus id>` with no `sex` and a stored preference of Male, then the atlas opens on Female (after the confirm sheet on first download).
- Given Female and `/atlas?select=<humerus FMA id>`, then the atlas switches to Male with a toast.
- Given Female with "Left ovary" selected, when I switch to Male, then I see a toast with a Switch back action and the male default view.
- Given the female manifest fetch fails and a male manifest is cached, then the UI says it couldn't load the female model and stays on Male (never shows the male model labelled Female).
- Given an answer about the ovary (mapped and reviewed), then its "View in 3D" chip opens the female model with the ovary selected.
- Given Female, when I press Reset view, then the female default view shows and `?sex=female` stays.
- Given Female active, then the atlas credit line shows the HRA credit.
- Given `female_atlas` is false, when I open `/atlas?sex=female`, then the Male model loads, no Male/Female control exists in the DOM, and the URL drops `sex`.
- Given a keyboard, when I Tab to the Male/Female control and press Right Arrow, then Female is selected and the confirm sheet opens with focus on "Download"; Tab stays inside the sheet; Escape closes it and focus returns to the Female radio.
- Given VoiceOver, when I confirm the download, then I hear progress at most at each quarter and "Female model ready" at the end.

#### Test plan
- Converter: the bounds check; `validate-atlas.mjs` on output; a pytest over `id_map.csv` (no duplicate concept ids for different structures, every hand-curated row has `reviewed_by`, every synthetic id matches `^[A-Z]+:[A-Z0-9_]+$`).
- `tests/test_crosswalk.py` extended for `sex`.
- Matcher tests for `HRA:` and `UBERON:` ids through `normalizeFma` and the `?select=` parser.
- `atlas-store` test: female fetch failure with a cached male manifest stays on Male.
- Playwright: switch, confirm sheet, selection re-resolution, symmetric auto-switch (skips without local models).
- Visual QA on the 20 spot-check structures by the named anatomy reviewer (below).
- **Reviewer and time.** One person reviews `id_map.csv` (the about 100 hand-curated rows; `reviewed_by` = their initials) and does the 20-structure visual QA. **Who is UNKNOWN**: the user names them before P3 starts (OQ-17). The draft said "a team member"; that is not an owner. Estimate (ASSUMPTION, about 1-2 minutes per row): about 2-3 hours for the id map plus about 1 hour for the visual QA, so **about half a day of reviewer time** in P3, on top of WS-A's 3.5-6 d, and on P3's critical path (unreviewed rows never feed answer links). WS-A prepares the sheet (mesh name, proposed id, screenshot) so the reviewer does not need the dev setup.

#### Risks and mitigations
| Risk | Mitigation |
|---|---|
| Id mapping errors send students to the wrong structure | Hand review for clinically important rows; unreviewed rows excluded from answer links |
| Size larger than budget | Brain-detail split; stricter simplification |
| Coordinate frame mistakes | Converter bounds check that fails on mismatch; visual QA |
| Female view looks broken (floating organs) | Torso/pelvis default framing; honest toggle label and note |
| Surprise mobile data cost | Confirm sheet with size; Save-Data default "Not now"; cancellable |
| Students expect a full female skeleton | UI note, toggle label and credits text |
| Files lost on the next atlas push | Female files built and pushed through the human-atlas build |
| Strategy freeze | OQ-8 |
| VM disk | Check free space before upload |

---

## 5. Cross-cutting

### 5.1 Design system and credits
- Use the existing kit (`web/components/ui`: Button, LinkButton, Chip, Tag, StatusPill, Skeleton, CitationChip, Markdown, Drawer, Toaster) and tokens; add `Tooltip` and `CoachMark` to the kit and document them in `ui/README.md`.
- New components (`Diagram`, `Videos`, `RelatedTopics`, landing scenes) use kit tokens only, no new colours except the landing canvas palette from `story/palette.ts`.
- Typography: existing Instrument Sans and IBM Plex Mono via `next/font` (`layout.tsx`).
- **C1 Credits (P0; WS-L for `/credits`, the shell link, the shared `<ModelCredit>` component and the `/how` line with `/how` QA; WS-A places the line in `AtlasView.tsx` and `Concept3D.tsx` right after R4, §1.3)**: a `/credits` page that renders the content of `deploy/atlas/ATTRIBUTION.md` (title, creators, licence link, source link, list of changes) for every model in use; a "Credits" link in the shell (rail footer and mobile overflow) next to `/privacy` and `/terms`; a visible one-line credit with a link to `/credits` on `/atlas`, in every `Concept3D` embed, on `/how` near the chiasm, and on the landing near scene 3; the female credit added when R5 ships and shown while Female is active. **G4 check**: every page that renders a mesh shows or links the credit for the model it renders. The gap exists today; the recommendation is to ship C1 as the first change after the demo (not before; the demo freeze applies).

### 5.2 Performance budgets (targets)
| Item | Budget | How checked |
|---|---|---|
| Landing LCP (mobile, Lighthouse "Slow 4G" preset) | at most 2.5 s (the SSR hero card) | Lighthouse on production build |
| Landing initial JS (before three.js), gzip | at most 150 KB | `next build` route table |
| Landing three.js + scene chunk, gzip | at most 250 KB, loaded after first paint | `next build` |
| Landing data before scene 3 | `story.json` (10,139 bytes) + the full `library.bin` (477,441 bytes on every device; mobile renders about a third of the points but downloads the whole file) [audit A; `data.ts:36-45, :86`] + `journey.json`/`why.json`/`declined.json` (small, measure) | network panel |
| Landing posters (static fallback only) | at most 25 KB each, lazy; SVG preferred | file sizes |
| Landing scroll smoothness | median at least 50 fps during scroll, no long task over 200 ms after first paint, on a named mid-range Android (target; §4.L) | Chrome remote DevTools Performance panel |
| Landing scene 3 3D data | at most 3 MB budget; plan is `chiasm.bin` (estimated tens of KB, UNKNOWN until extracted). For reference, the draft's approach measured about 3.7 MB (`atlas.json` 1,335,285 B uncompressed + `body-6.bin.gz` 2,378,951 B, local human-atlas build, 2026-11-15) | network panel |
| Atlas manifest on the landing | never (L-6) | network panel |
| Full atlas on landing | never | L-6 test |
| `/ask` initial JS | no increase over today beyond 5 KB gzip (diagram and videos chunks lazy) | `next build` before/after |
| Diagram chunk | at most 60 KB gzip | `next build` |
| Female model | at most 35 MB gzip, on demand after confirm | file sizes |
| `/api/videos` cache hit | at most 100 ms server time | API log timing |

Today's route sizes for `/`, `/how`, `/atlas` are measurable now with `pnpm --dir apps/web build`; P0 records them in the wiki as the baseline.

### 5.3 Analytics and feedback
- New `POST /api/events` with body `{name: <enum>, props?: {<enum key>: <enum value>}}`; stored as daily counts in SQLite `events(day, name, key, count)`. No user id, no IP, no question text, no topic, no video id, no cookies. `name` and every `props` key and value come from fixed enums (for example `kind` for diagrams); free text is rejected (422). Rate limited per client IP in memory through the shared limiter (not stored).
- Client rule: each event fires at most once per page load (`sessionStorage` guard); `from_landing` marker as in §4.L.
- Extend `POST /api/feedback`: kinds gain `diagram_wrong` and `video_bad`, and `FeedbackRequest` gains optional `target_id` (max 32 chars) for the `diagram_id` or `video_id` (`api/schemas.py:244-248` has no such field today). Tests cover the 422 cases (unknown kind, over-long `target_id`).
- A read-only `GET /api/events/summary` for the team, protected by `EVENTS_TOKEN` in the server `.env` (not shipped to the client).

### 5.4 Security, privacy and terms
- **Real client IPs (P0)**: the API runs `uvicorn ... --workers 1 --proxy-headers` without `--forwarded-allow-ips` (`deploy/v2/Dockerfile.api:13`), so `X-Forwarded-For` from Caddy (another container) is not trusted and `request.client.host` is Caddy's container IP for every user. Any per-IP limit would therefore be a site-wide limit. Fix: `--forwarded-allow-ips` set to the docker network range (or `*`, since only Caddy can reach the API port), with a test and a G6 check that the logged client IP is the real one.
- **Shared rate limiter** (`api/ratelimit.py`): one in-process token bucket keyed by client IP (one worker, so a dict is enough), used by diagrams (10/min), videos (30/min) and events; tested through the HTTP seam with a spoofed `X-Forwarded-For` from the trusted proxy address. Plus global daily caps per costly endpoint (diagram LLM calls, D-14; YouTube searches, V-4), so a shared college network or a script cannot burn the budget.
- No keys client-side: `YOUTUBE_API_KEY`, `DEEPSEEK_API_KEY`, `DIAGRAM_SIG_SECRET`, `EVENTS_TOKEN` only in the server `.env`; restrict the YouTube key to the YouTube Data API v3 and the VM's IP [yt §6].
- `push.sh` env passthrough extended for the new keys (V-1).
- LLM output never rendered as HTML (diagram labels are text nodes in SVG; Markdown stays in the existing renderer).
- External links use `rel="noopener noreferrer"`; thumbnails `referrerpolicy="no-referrer"`.
- **Known issue (recorded, not fixed here)**: `POST /api/answers` accepts a free `payload` object (up to 200 KB) with no auth [api/README.md], so anyone can host fabricated answer text at `/a/<id>`. This release does not widen it: diagrams in shares are server-issued by id, and videos are re-fetched live.
- **Privacy page `/privacy`** (required by YouTube API policy III.A.2 [yt §2]), user approves the text. It lists every item we store or process:
  - questions are sent to DeepSeek to answer them and, for flowcharts, to draw diagrams (DeepSeek is China-based [strategy C5]);
  - shared answers are stored when you share and are public to anyone with the link, with no expiry;
  - feedback stores the question and your note when you send it;
  - anonymous daily event counts (no ids);
  - server and proxy logs (contents, including IP addresses, and how long they are kept: **UNKNOWN today**, to be checked on the VM and stated);
  - `diagram_cache` (hashed key, labels and pointers, 90 days);
  - the `mm_asked` cookie; `localStorage` keys (atlas sex preference, coach marks, theme if any); the IndexedDB model cache;
  - the app uses YouTube API Services, with a link to Google's Privacy Policy (https://policies.google.com/privacy) and YouTube's Terms (https://www.youtube.com/t/terms); thumbnails load from Google servers, which receive your IP address;
  - contact and grievance details (user to supply, OQ-13), data-principal rights, and the position on minors (OQ-15).
- **Terms page `/terms`** (new, WS-L, P1, blocks R2; moved from WS-X, §1.2a): study aid, not medical advice and not for decisions about a real patient; video suggestions are external, with the note's full label; "By using the video suggestions you agree to be bound by the YouTube Terms of Service" with the link [yt §2 III.A.1]; link to `/privacy`. User approves the wording; included in the verbatim clause re-read.
- `/privacy`, `/terms` and `/credits` are linked from the shell footer/overflow and from the videos section header.
- **DPDP**: India's Digital Personal Data Protection Act 2023 and its Rules may apply; this PRD is not legal advice. OQ-15 asks the user which obligations apply now, and for the grievance contact and the minors position.
- If a CSP is added later: `img-src https://i.ytimg.com` [audit C].

### 5.5 Testing strategy
- **Python**: pytest seam tests over FastAPI endpoints with LLM and YouTube mocked (engineering principle 3), new files `tests/test_api_diagram.py`, `tests/test_api_videos.py`, `tests/test_api_events.py`, `tests/test_ratelimit.py`; SSE ordering test for the new `topic` event in the `test_api_v2.py` style; existing `tests/test_api.py`, `tests/test_api_v2.py`, `tests/test_diagrams.py` stay green.
- **Web unit tests (new; there is no web unit runner today: `apps/web/package.json` has only `dev`, `build`, `start`, `lint`, `check`, checked at `e0eec26`)**. Runner: **Vitest** as a new dev dependency (no browser download; added to OQ-12 for the user's yes), Node environment, with `@/` resolved from `tsconfig.json` paths in `apps/web/vitest.config.ts`. Script `"test:unit": "vitest run"`, and G1 runs it. Owner: the lead agent adds the dependency, config and script (it owns `package.json`, §1.3); each workstream writes the tests for its own modules next to them as `*.test.ts`. First files: `web/components/landing/facts.test.ts` (WS-L, L-7), `web/lib/atlas-store.test.ts` (WS-A, female fetch failure with a cached male manifest stays on Male, F-1a; per-sex cache keys), `web/lib/atlas-reset.test.ts` (WS-A, §4.4), `web/lib/copy/diagram.test.ts` and `web/lib/features.test.ts` (WS-X, §4.1), the related-topics turn helper (WS-X, V-9), the long-press handler (WS-K, T-4). **If Vitest is declined**: the same files run under `node --test` with Node's built-in TypeScript type stripping (Node 26.12.1 locally; the version on any CI is UNKNOWN), which needs those modules to use relative imports with explicit `.ts` extensions instead of `@/`; the lead decides per module in P0.
- **Web**: `pnpm --dir apps/web check` (`tsc --noEmit && node scripts/check-tips.mjs`) and `build`. Add **Playwright** (new dev dependency; installing it downloads browser binaries, so it needs the user's yes, OQ-12) for: atlas reset and undo (R4), `/?q=` and cookie redirects (Landing), tooltip keyboard behaviour (R3), female switch (R5). Kept small on purpose. **If Playwright is declined (OQ-12)**: G1 still runs `pytest -q`, `check`, `test:unit` (including the model-free R4 test above) and `build`; the redirect checks (§4.L) run as a small Node `fetch` script against `next start` with no new dependency (`apps/web/scripts/check-redirects.mjs`, WS-L); and the browser-only checks (R4 camera after the tween, R5 switch, tooltip keyboard) move to a written G2 checklist in the PR with screenshots. No regression test then guards the R4 WebGL path; that is recorded as an accepted gap in the PR.
- **Browser QA** (G2): 390 px and 1440 px, light and dark, reduced motion, WebGL off and Save-Data for the landing, VoiceOver spot checks; screenshots in the PR.
- **Lighthouse** (G3): run with `npx lighthouse` (a download; approval with OQ-12).
- **CI**: none exists today (no `.github/`). Recommend adding the GitHub Actions job from strategy item C1 in P0 so the tooltip check really fails CI. Until then, the gate is the agent running G1 locally.

### 5.6 Rollout
- **Feature flags (revised mechanism)**: flags live in a small JSON file on the VM **outside the rsync payload**, `~/v2-state/features.json` (`{"diagram": false, "videos": false, "female_atlas": false}`), mounted read-only into the API container. `GET /api/features` reads it with an mtime cache on each call, so a flip needs **no restart and no deploy**. Why not `.env`: `push.sh` rebuilds the VM `.env` on every deploy from a grep of the local `.env` and rsyncs with `--delete` (`push.sh:27, :48`), so a hand-edited flag would be silently reverted; `docker compose restart` does not re-read `env_file`; and `API_SHA` hashes the bundled `.env`, so a flag change through `push.sh` would recreate the API and pay the warm-up.
  - Flip: `ssh <vm> 'jq ".videos=true" ~/v2-state/features.json > /tmp/f && mv /tmp/f ~/v2-state/features.json'`; rollback is the same with `false`. Each flip needs the user's yes and is followed by `curl /api/features` (G6).
  - Missing or unreadable file means all flags false.
  - The landing reads flags on the server (server component fetch to the API, 1 s timeout, short revalidate), never by client-side insertion.
  - `/ask`, `/a/[id]` and `/atlas` get the same server-fetched flags through the root layout's `FeaturesProvider` (D-15); no browser fetch of `/api/features`. Every flag-gated control (Flowchart chip, videos section, Male/Female toggle) is **absent** when its flag is false or the fetch failed. A flag flipped to false while a page is open is caught by the endpoint's 503 (diagram, videos) or, for `female_atlas`, takes effect on the next load (model files are static, so a loaded female model stays usable until then; ASSUMPTION accepted as harmless).
- The landing itself is not flagged (route change); rollback is redeploying the previous commit.
- **Rollback per phase (unflagged changes).** Rollback for anything not behind a flag is `deploy/v2/push.sh` from the previous commit (user yes), followed by G6. Per phase:
  - **P0**: R4 (Reset + Undo), the toast `action`, C1 credit lines and `/credits`, the tooltip primitive and sweep, the shared rate limiter and `--forwarded-allow-ips` are all unflagged. Rollback = redeploy the last pre-P0 commit (recorded in the PR before deploy). Special case: if the limiter misbehaves (for example every user throttled because client IPs are wrong), the G6 check catches it; the fast mitigation is a proposed `ratelimit` key in `~/v2-state/features.json` (new; default true; false = limiter off), read the same way as the flags, so the limiter can be turned off without a deploy. `--forwarded-allow-ips` itself rolls back only by redeploy (it is in `Dockerfile.api`).
  - **P1**: R1 and R2 roll back by flag (`diagram`, `videos` false). Unflagged in P1: the `/ask` alias, the `mm_asked` cookie write, the `topic` SSE event and related topics, `graph_citations`/`answer_sig` on the answer event, `/privacy`, `/terms`. All are additive (old clients ignore new events and fields), so rollback = redeploy the previous commit; a cookie already set is harmless before the landing ships (nothing reads it).
  - **P2**: the landing switch rolls back by redeploying the previous commit (`/` becomes the chat again; the `/?q=` redirect goes with it, and old links still work because `/` handles `?q=` itself as today).
  - **P3**: the female atlas rolls back by flag (`female_atlas` false hides the toggle); the female model files and crosswalk rows can stay deployed (unreferenced). A bad crosswalk row is rolled back by the eka-app image rebuild from the previous commit (its own runbook, §4.5).
- **Staging caveat**: `mentor.medevolv.in` and `v2.130-210-60-153.sslip.io` are served by the **same** Caddy site block and the same containers (`deploy/v2/Caddyfile.v2-block:3`). Deploying "to the sslip host first" therefore deploys to production too. Options: (a) ship with flags off, verify on the live hosts, then flip flags (recommended; no infra change); (b) add a separate staging compose project and host (the VM has 1 CPU per `push.sh`; capacity UNKNOWN). See OQ-9.
- **Sequence per phase**: local production build + G1-G4 → user yes → `deploy/v2/push.sh` with flags off → G6 smoke → user yes → flip flag → watch events and feedback for 48 h → write wiki entry. Atlas files and the crosswalk follow their own runbooks (§4.5).
- **Password gate and rights**: the strategy review recommends re-gating the public site after the demo [`docs/gtm/04_regate_site.md`]. The landing ships in `pilot` mode behind whatever gate exists until OQ-1 is decided (§4.L).

### 5.7 Wiki updates (lead agent, same PR as each feature)
- `docs/wiki/subsystems/answer-extras.md` (flowchart grounding, kinds and validator; videos cache and policy).
- `docs/wiki/subsystems/tooltips.md` (primitive, tip files, check script, baseline, coach marks).
- `docs/wiki/decisions/ADR-00x-diagram-grounding.md`, `ADR-00x-landing-and-ask-route.md` (scope already recorded in ADR-002).
- Record measured sizes (route JS, `chiasm.bin`, female chunks) and the verbatim YouTube clause re-read.
- Update `docs/wiki/index.md`; update `deploy/atlas/README.md` and `ATTRIBUTION.md` for the female set; update `api/README.md` for every new endpoint and event.

### 5.8 Not in scope
i18n and Hinglish, accounts, paywall, password-gate implementation, CSP, video embedding, retrieval changes, the drug-advice safety fix itself, changes to the `/how` journey (OQ-16).

---

## 6. Risks, open questions, decisions

### 6.1 Risk register
| # | Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| K1 | Changes leak into the 17 Nov demo | Low | High | Freeze; nothing merged to the deploy path before 17 Nov without a yes | User, lead |
| K2 | Public landing contradicts the content-rights position or ships before the patient-specific drug-advice safety gate (12/18 hard cases "major" [strategy line 29, 381]) | Medium | High | OQ-1 hard gate (rights decision **and** safety gate); `pilot` mode by default; noindex; no excerpts; exam-style journeys only | User |
| K3 | Diagram adds an unsupported claim or relation | Medium | High | V1-V6, E1-E5, decline, offline eval gate, report button | WS-X |
| K4 | YouTube quota exhausted or policy breach | Medium | Medium | Cache, lazy fetch, rolling-window degrade, fallback link, `/privacy`, `/terms`, no API data outside the cache, verbatim clause re-read | WS-X, user |
| K5 | Poor-quality medical videos shown | Medium | Medium | Strict safe search, filters, verified allowlist, at most 2 unvetted cards, blocklist, honest label | Team |
| K6 | Landing slow on student phones | Medium | High | Budgets, SSR LCP, lazy three.js, Save-Data and time fallbacks, `chiasm.bin` | WS-L |
| K7 | Old `/?q=` links break | Low | Medium | Redirect + test | WS-L |
| K8 | Female id mapping wrong | Medium | Medium | Hand review, reviewed-only crosswalk | WS-A |
| K9 | Female model too large / VM disk full | Medium | Medium | Budget, brain split, check disk first | WS-A, user |
| K10 | Parallel agents conflict on shared files | Medium | Low | Ownership table 1.3, per-feature tip files, optional `tip` prop with baseline | Lead |
| K11 | No staging host; flags are the only safety net | High | Medium | Flags off on deploy; file-based flags; OQ-9 | Lead, user |
| K12 | Tooltip work ignored on touch, main audience | High | Low | Coach marks, accessible descriptions, "?" toggle | WS-K |
| K13 | The strategy review freezes "v2, the 3D atlas and graph expansion until pilot data shows repeat use" [strategy line 81]; this whole release is v2 expansion | High | High | OQ-8: one user decision for the whole release before work starts | User |
| K14 | Per-IP limits act site-wide behind Caddy | High (today) | Medium | `--forwarded-allow-ips` fix and test (P0) | WS-X |
| K15 | CC BY credit missing for meshes already served | High (today) | Medium | C1 credits (P0) | WS-L |
| K16 | Fabricated shared answers on our domain | Low | Medium | Known issue recorded; diagrams in shares server-issued | Lead |

### 6.2 Open questions for the user (each with our recommended answer)
1. **OQ-1 Public landing vs rights and safety (hard gate).** The strategy review says do not claim "trusted textbook answers" publicly until content rights are settled, that the 12/18 drug-advice leak "blocks any public growth", and that the safety gate "must pass before anything public" [strategy lines 154, 381, 399]. *Options*: (A) landing and app both behind the same gate, `pilot` copy; (B) landing and `/privacy` public in `pilot` mode, `/ask` gated with an access-code screen whose copy matches the landing (a reviewer's suggestion, better for first-time visitors); (C) fully public in `public` mode. *Recommended*: **A** until the user records a rights decision and the safety gate passes; then B or C. Also decide whether book titles are shown on the landing.
2. **OQ-2 Returning users.** Redirect returning askers from `/` to `/ask` via the `mm_asked` cookie and middleware? *Recommended*: yes, only after their first answered question, with `?tour=1` to see the landing.
3. **OQ-3 Landing copy and captures.** Approve the two headline sets, the coverage strip, the five-scene direction, the new exam-style hero question and decline question, and the capture run (DeepSeek calls)? *Recommended*: approve the direction and the capture run; final copy and the chosen questions reviewed by the user in the PR.
4. **OQ-4 Pre-demo Reset fix.** Ship R4 before 17 Nov? *Recommended*: no; ship on 18 Nov. The demo flow is rehearsed and the bug is cosmetic.
5. **OQ-5 Video loading.** Auto-load thumbnails when the section scrolls into view, or require a "Show videos" tap? *Recommended*: auto-load on scroll (better discovery), disclosed on `/privacy` and `/terms`; switch to the tap if the verbatim III.A re-read says users must actively agree.
6. **OQ-6 Diagram request.** *Resolved by this revision*: stateless with a server-issued `answer_sig` (HMAC); no stored answers needed. Confirm.
7. **OQ-7 Related-topic chips.** *Resolved*: append a new turn to the current thread; the concept page stays reachable from the answer's concept chips. Confirm.
8. **OQ-8 The v2 freeze, for the whole release.** The strategy review: "Freeze v2, the 3D atlas and graph expansion until pilot data shows repeat use" [strategy line 81]. Proceed with any of this release before pilot data? *Options*: (A) lift the freeze for the whole release; (B) only the trust fixes and small items (R4, C1, R3, the proxy fix) now, the rest after pilot data; (C) B plus offline-only R5 work (the 202 MB download and the converter, no ship). *Recommended*: **B now**, decide on R1/R2/Landing/R5 when the pilot's first repeat-use data arrives; the plan is ready either way.
9. **OQ-9 Staging.** The sslip host and mentor domain share containers. Accept "deploy with flags off, then flip"? *Recommended*: yes; revisit a real staging host if the pilot grows.
10. **OQ-10 YouTube key.** Will you create a Google Cloud project and YouTube Data API key (restricted to the API and the VM IP), and add `YOUTUBE_API_KEY` to `.env`? *Recommended*: yes, after the `/privacy` and `/terms` text is approved; we cannot do this step for you.
11. **OQ-11 Channel allowlist.** Who verifies channel ids? *Recommended*: one team member verifies 5-10 channels from the note's candidate list in an hour; ship with whatever is verified, even an empty list (then 2 cards show).
12. **OQ-12 Playwright, Vitest and Lighthouse.** Approve adding Playwright as a dev dependency (download of browser binaries), Vitest as a dev dependency (web unit tests, no browser download), running Lighthouse via `npx`, and fetching the local models (about 90 MB) for E2E? *Recommended*: yes to all. If Playwright or the model fetch is declined, §5.5 says what G1 runs instead.
13. **OQ-13 Privacy and terms contact.** Which contact email, entity name and grievance contact go on `/privacy` and `/terms`? *Recommended*: the team email already used for the project; we draft, you approve.
14. **OQ-14 Reassurance line.** Which of "Free during the pilot", "No sign-up", "English only for now" are true and may be shown under the CTA? *Recommended*: show only what you confirm.
15. **OQ-15 DPDP and minors.** Which DPDP obligations apply now; is the service for users aged 18+, or do we need a parental-consent position for under-18 first-year students? *Recommended*: get a short review; until then state on `/privacy` that the pilot is meant for enrolled MBBS students and give a grievance contact. Not legal advice.
16. **OQ-16 `/how` journey.** `/how` still replays the pheochromocytoma patient-management journey. Re-record it with the landing's exam-style journey? *Recommended*: yes, in a separate small change after the landing (it touches `/how`, so it needs `/how` QA).
17. **OQ-17 Female model scope ("very similar") and reviewer.** The request was a "very similar" female model. The only open candidate (HRA VH_F v1.5) is an **organs-only female reference**: no skull, ribs, sternum, clavicle, scapula, arm, hand or foot bones were found, only about 20 muscle names, no vulva, clitoris or labia, and no mesh-level ids [fem §3.1]. Alternatives the female note looked at and why they were not chosen [fem §3.2-3.6]: **Z-Anatomy** (BodyParts3D-derived, licence CC BY-SA 4.0 unverified, female content unverified, Blender/FBX without ids); **BodyParts3D** (male only); **Visible Korean** female (licence not stated, 3D PDF only, no ids); **Open Anatomy / AnatomyTOOL** (licence and female content unverified); commercial sets and IT'IS Virtual Population (not open for redistribution). *Question*: do you accept "Male | Female (organs)" with the stated gaps as meeting R5, or should R5 wait for a fuller model (for example a manual check of Z-Anatomy's .blend, which would also bring share-alike obligations)? Also: who is the anatomy reviewer for `id_map.csv` and the 20-structure QA (about half a day)? *Recommended*: accept organs-only for this release with the honest label and note, and name one reviewer before P3 starts.

### 6.2a User decisions (recorded 2026-11-15, late evening)
The user answered the four headline questions: "1 public 2 yes 3 ok 4 ship asap". Recorded as:
- **OQ-1 → C, fully public**, `public` copy mode. Guardrails that stay regardless: noindex, no textbook excerpts on the landing, internal evals labelled internal, study-aid/not-medical-advice framing, exam-style journeys only (no patient-management hero).
- **OQ-8 → A, the freeze is lifted for the whole release**, and the HRA VH_F v1.5 download (211,624,968 bytes, CC BY 4.0, `https://cdn.humanatlas.io/digital-objects/ref-organ/united-female/v1.5/assets/3d-vh-f-united.glb`) is approved.
- **OQ-10/11 → yes**: the user will create the restricted `YOUTUBE_API_KEY`; until it exists, R2 ships in its keyless mode (the youtube.com/results fallback link). Channel allowlist ships empty until a team member verifies ids.
- **OQ-4 → ship ASAP**: R4 and the rest of the release ship as soon as each passes its gate, including before the 17 Nov demo, with flags off by default for anything not yet QA'd on the live host, and the demo flows (Ask, Why, Explore, 3D, /how) re-checked after every deploy.
- Unanswered questions take the recommended answer where it needs nothing from the user: OQ-2 yes, OQ-3 approve direction + capture run, OQ-5 auto-load on scroll, OQ-6/7 confirmed, OQ-9 yes, OQ-16 later, OQ-17 accept "Male | Female (organs)" with the honest note (anatomy reviewer: still to be named; automated id mapping ships flagged off until reviewed).
- Need the user, so deferred: OQ-12 Playwright browser-binary download and the ~90 MB local model fetch (not approved; QA uses the built-in browser and `pnpm check`/pytest; Vitest is allowed as an npm dev dependency); OQ-13 contact details (privacy/terms pages point to the in-app feedback channel until a contact is given); OQ-14 reassurance line (none shown); OQ-15 DPDP (state "for enrolled MBBS students", grievance via feedback, not legal advice).

### 6.3 Decision log
| # | Date | Decision | Rationale | Status |
|---|---|---|---|---|
| D-1 | 2026-11-15 | Flowchart grounding: ontology path only with answer overlap, else answer-derived graph of one `kind` with node and edge validators, else helpful decline; namespaced passage/fact citations | Keeps cite-or-decline; avoids citation collisions and off-topic charts | Proposed |
| D-2 | 2026-11-15 | Renderer: versioned JSON graph (groups, kinds) + dagre + React SVG, lazy | No markup injection, small lazy chunk, citation chips and theming under our control | Proposed |
| D-3 | 2026-11-15 | Videos fetched lazily on scroll; query from ontology topic label only; topic via a new `topic` SSE event; no YouTube data outside the cache; shared pages re-fetch | Quota, privacy, III.E.4 | Proposed |
| D-4 | 2026-11-15 | "Default view" = fresh `/atlas` goal pose for current layers and inset: no selection, Isolate off; layers and sex unchanged; Undo toast; per-model default (female: torso/pelvis) | Matches student expectation; recoverable | Proposed |
| D-5 | 2026-11-15 | Returning askers skip the landing via `mm_asked` cookie + middleware; `?tour=1` escape | No flash on slow phones; burst usage | Proposed (OQ-2) |
| D-6 | 2026-11-15 | Ask moves to `/ask` (alias in P1, `/` switches with the landing); `/?q=` redirect keyed on `q`; 404 to landing; landing not a tab; logo to `/ask` | Never a blank `/`; keeps four tabs | Proposed |
| D-7 | 2026-11-15 | `tip` optional + `check:tips` with a shrinking baseline in `pnpm check`; required when the baseline is empty; per-feature tip files | Pit of success without a big-bang break or merge hotspot | Proposed |
| D-8 | 2026-11-15 | Female atlas = HRA VH_F v1.5 behind "Male / Female (organs)"; never mixed in one scene; confirm before download; behind the `female_atlas` flag | Only candidate with an open licence, per-structure meshes and female anatomy [fem §1]; Z-Anatomy, Visible Korean, Open Anatomy/AnatomyTOOL rejected on licence, format or ids [fem §3.2-3.6] | Proposed (OQ-8, OQ-17) |
| D-9 | 2026-11-15 | Runtime feature flags from a VM JSON file read by `/api/features`; flags off at deploy | No staging; `.env` is rebuilt on every deploy | Proposed (OQ-9) |
| D-10 | 2026-11-15 | No scraping or unofficial YouTube clients | ToS and reliability [yt §3] | Proposed |
| D-11 | 2026-11-15 | Landing: five scenes, hero = SSR answer card with page pointers, Why-was-I-wrong second, exam-style recorded journey, `pilot`/`public` copy modes, inside the app shell | Utility in 5 seconds; strategy wedge; safety and rights positions | Proposed (OQ-1, OQ-3) |
| D-12 | 2026-11-15 | Video ranking: at most 4 cards, at most 2 non-allowlisted, allowlisted first | One testable rule that works with an empty allowlist | Proposed |
| D-13 | 2026-11-15 | YouTube degrade on a rolling 24 h window of 80 searches | Reset time unknown; rolling window is safe for any reset time | Proposed |

---

## Review log (2026-11-15)

Four reviewers (lenses: accuracy, engineering, student-ux, trust-policy) returned 84 findings. Ids: `ACC-n`, `ENG-n`, `SUX-n`, `TP-n` in the order received. Facts were re-checked against the repo and notes before changing them (for example: no credit strings in `apps/web`; `lint` is `next lint` with no ESLint; `push.sh:27` grep; `Dockerfile.api:13` has no `--forwarded-allow-ips`; `atlas.json` 1,335,285 B and `body-6.bin.gz` 2,378,951 B in the local human-atlas build; `story.json` journey is the pheochromocytoma question; `data.ts:86` mobile subsample; `rag/diagrams.py:29, :102-111, :212`; `rag/answer.py:150-158`; `atlas-store.ts:35-55`; `optimize-anatomy.mjs:4`; `ATTRIBUTION.md:16, :20, :27, :29`; strategy lines 81, 128-130, 140, 154-155, 381, 399, 420, 519; eval file lines 12-17, 63).

"Fixed" means applied as suggested or with a recorded variant; "Fixed, part declined" means the finding was applied but one specific suggestion was not, with the reason.

| Id | Finding | Action |
|---|---|---|
| ACC-1 | YouTube data kept in share payload past 30 days | Fixed: share payload stores `topic` only; V-3 covers every table; V-12 test |
| ACC-2 | False "already credited" claim | Fixed: restated as a gap; C1 in P0 |
| ACC-3 | Label called verbatim but reworded | Fixed: note copy verbatim in info tip and `/terms`; one-line version marked "adapted" for user approval; single shared copy file for UI and API |
| ACC-4 | Freeze treated as atlas-only; safety gate missing | Fixed: §1.1 precondition, K2, K13, OQ-1, OQ-8 widened and quoted |
| ACC-5 | Chiasm size marked UNKNOWN but measurable | Fixed: 3.7 MB measurement recorded; `chiasm.bin` is the plan; manifest in budget table |
| ACC-6 | Mobile subsample does not reduce download | Fixed: budget and copy state full 477 KB download and about one-third rendering; acceptance reworded |
| ACC-7 | `pnpm lint` gate unsupported | Fixed: `check:tips` chained into `check`; ESLint not added |
| ACC-8 | "Full skeleton and muscles" unsupported | Fixed: male tip "(2,234 parts)" |
| ACC-9 | Units/axes conflict reported one-sided | Fixed: marked UNKNOWN with both sources; converter bounds check first |
| ACC-10 | "One reference body" vs ATTRIBUTION | Fixed: conflict recorded; "A reference assembly; real anatomy varies." until verified |
| ACC-11 | Credit text missing source link; title differs | Fixed: source link kept; title UNVERIFIED with both candidates |
| ACC-12 | Ranking cap contradicts empty-allowlist fallback; maxResults attribution | Fixed, part declined: maxResults marked as our choice; contradiction removed by a single rule (D-12). The suggested "cap applies only when the allowlist is non-empty" was not used, because with the default empty allowlist it would show 4 unvetted videos; we chose "at most 2 non-allowlisted" (TP-18) |
| ACC-13 | "Midnight Pacific" unsupported | Fixed: rolling 24 h window (D-13) |
| ACC-14 | Search params not in an FR | Fixed: V-0 with test |
| ACC-15 | III.A.1 "bound by" statement missing | Fixed: terms line in videos section and `/terms`; acceptance criterion |
| ACC-16 | 26k facts and eval caveats | Fixed: glossary labels 26k internal/unaudited; eval dated 13 Nov 2026 with scope; 90.8% not shown to students or shown with Tripathi-only scope |
| ACC-17 | Effort sum wrong | Fixed: recomputed for the revised plan, 25.5-33 days, no buffer |
| ACC-18 | Ontology sources cited to wrong source | Fixed: cites `rag/diagrams.py:102-111, :255` |
| ACC-19 | "67 of 82" treated as exact | Fixed: "about 82 / about 67, approximate"; script's first run is the baseline |
| ACC-20 | Female manifest name mismatch | Fixed: `female.json` + `female-N.bin` per `optimize-anatomy.mjs:4` |
| ACC-21 | Scene 1 journey is a patient-management question | Fixed: new exam-style capture (L-7a), user approves |
| ENG-1 | Ontology path cannot meet the contract | Fixed: contract v2 with groups and namespaced cites, `_Dot` refactor, caps, answer-overlap condition, fact drawer, structured pointers |
| ENG-2 | Per-IP limits site-wide behind Caddy | Fixed: `--forwarded-allow-ips`, shared limiter, global daily caps, G6 check |
| ENG-3 | Required `tip` prop breaks build; ownership conflicts | Fixed: optional prop + baseline, required at the end; R4 before AtlasView tips (WS-A); per-feature tip files |
| ENG-4 | Ask move gap and ownership contradiction | Fixed: `/ask` alias in P1 by WS-X (owns `SharedAnswer.tsx`), `/` switches with the landing; cookie from first `/ask` release |
| ENG-5 | `[G#]` citations unhandled | Fixed: `graph_citations` on `AnswerEvent`; V3/V4/E-rules cover `[G#]`; test |
| ENG-6 | Flag flip needs only a restart: false | Fixed: VM JSON flags file outside rsync, mtime-cached; push.sh grep extended for keys; G6 check |
| ENG-7 | No timeouts; thread-pool starvation | Fixed: D-13 timeouts and dedicated executor; async httpx for YouTube; hung-LLM test |
| ENG-8 | Open LLM endpoint | Fixed: `answer_sig` HMAC (settles OQ-6) and daily cap |
| ENG-9 | Share payload stores YouTube data | Fixed: same as ACC-1 |
| ENG-10 | Topic on `answer` event impossible | Fixed: new `topic` SSE event after `spatial`; README and parser update; ordering test |
| ENG-11 | Chiasm over budget | Fixed: same as ACC-5; `chiasm.bin` script; `.json.gz` manifests recommended |
| ENG-12 | Manifest cache collides across sexes | Fixed: F-1/F-1a per-sex store and cache keys; test |
| ENG-13 | Missing deploy paths and file ownership | Fixed: P3 runbook (human-atlas build + `push_atlas.sh`; eka-app crosswalk rebuild); 1.3 table updated with hand-over |
| ENG-14 | check-tips enforcement gaps | Fixed: exact rule, non-button roles, Markdown delegated tooltip, fixtures, no next lint |
| ENG-15 | RV-3 test cannot pass | Fixed: compare goal poses at 1e-6; RV-3 redefined for current layers and inset; E2E run recipe |
| ENG-16 | Landing vs AppShell | Fixed (variant): landing inside the shell with CTA above the tab bar and canvas inside `<main>`; story modules imported unedited; `/how` QA on any story change. Route-group option not chosen (more file moves) |
| ENG-17 | Metrics not computable | Fixed: once-per-load guard, `from_landing` marker, enums, route-size baseline in P0 |
| ENG-18 | Share before diagram | Fixed: `shareId` cleared when a diagram is added; acceptance criterion |
| ENG-19 | Ontology cache location | Fixed: `diagram_cache` in `$APP_DB`, `use_cache=False` |
| ENG-20 | Quota timezone, purge scheduler, safeSearch, feedback target | Fixed, part declined: purge on write and startup; safeSearch strict vs moderate measured; `target_id` added. Keying the day by America/Los_Angeles was declined in favour of a rolling 24 h window, because the reset time is unverified (ACC-13) |
| ENG-21 | Coordinate frame and synthetic id format | Fixed: bounds check that fails; uppercase ids without spaces or commas; matcher tests |
| ENG-22 | Tooltip primitive details | Fixed: persistent description, `aria-disabled`, `'use client'`, serialisable `tip`, `Chip` `...rest` fix |
| ENG-23 | Save-Data on iOS, features failure, Lighthouse approval | Fixed: 6 s time fallback; features failure = all false; Lighthouse in OQ-12 |
| SUX-1 | Patient drug question as landing demo | Fixed: same as ACC-21; L-7a rule |
| SUX-2 | Gate makes the landing invisible; headline needs rights | Fixed, part declined: gate settled before WS-L via OQ-1; two headline sets behind `LANDING_MODE`; honest CTA under a gate. "Landing public, `/ask` gated" is kept as option B, not the default, because the strategy says the safety gate must pass "before anything public" |
| SUX-3 | Hero shows the pipeline, not the utility | Fixed: SSR answer card with page chips and 3 example chips; galaxy is the payoff with student-facing book names |
| SUX-4 | "Every dot is one passage" false on mobile | Fixed: caption from rendered N (L-12) |
| SUX-5 | No coverage statement | Fixed: coverage strip with "Not yet" list and editions; P4 notes no OBG book |
| SUX-6 | Scene order vs wedge; cricket strawman | Fixed: five scenes, Why-was-I-wrong second, near-miss medical decline, Explore dropped |
| SUX-7 | Flags resolved client-side; YouTube branding in marketing | Fixed: server-resolved flags; placeholder video cards, no YouTube marks |
| SUX-8 | Client redirect flashes; logo dead link | Fixed: cookie + middleware; logo to `/ask`; "Take the tour" link |
| SUX-9 | Diagram types students draw | Fixed: `kind` classification/pathway/sequence with verbs and caps; eval across kinds with decline rate by kind |
| SUX-10 | Diagram placement and dead-end decline | Fixed (variant): skeleton scrolled into view and focused; progress copy; helpful decline with a tap-to-ask chip; chip shown only with 3+ cited sentences (client-side count instead of a server pre-check); "Flowchart" label with `Workflow` icon |
| SUX-11 | Export unusable for students | Fixed: "Save image" via share sheet, white light-palette render, SVG under More, Full screen instead of in-card pinch |
| SUX-12 | Female first impression | Fixed, part declined: torso/pelvis default, skin off by default, honest note. The label "Male (full body)" was declined because the male model is not complete (ACC-8); used "Male \| Female (organs)" |
| SUX-13 | Female download on mobile data | Fixed: confirm sheet with size, Save-Data default, cancellable/resumable, symmetric auto-switch, toast action |
| SUX-14 | Tooltips on touch | Fixed: coach marks on 5 controls, "?" toggle, long-press only for icon-only buttons, touch callout never disabled on links |
| SUX-15 | Tooltip copy quality | Fixed, part declined: copy rules, data tooltips for citation chips and rail dots, two-tier approval. "Obvious controls get a purpose only, effect omitted" was declined because the user asked for purpose **and** effect on every option; obvious controls get one combined sentence instead |
| SUX-16 | Video card nesting, related topics, label fatigue | Fixed: link and sibling report button; related chips append to the thread; one-line label + info tip; "Quick revision" caption |
| SUX-17 | Reset loses selection | Fixed: Undo toast (RV-6); honest tip |
| SUX-18 | Poster weight | Fixed: SVG first, posters at most 25 KB lazy, SVG-only on Save-Data |
| SUX-19 | CTA microcopy and eval jargon | Fixed: reassurance line from user-confirmed facts only (OQ-14); student-readable eval line; example chips one per prof year |
| SUX-20 | Light theme and default | Fixed: follows `prefers-color-scheme`; light hero QA; SSR card readable in both |
| TP-1 | Credits missing everywhere | Fixed, part declined: C1 in P0 (`/credits`, credit lines on every mesh surface, G4 check); false sentence corrected. Shipping it *before* the release (pre-demo) was declined because of the demo freeze; it is recommended as the first change after 17 Nov |
| TP-2 | YouTube data in share payload | Fixed: same as ACC-1 |
| TP-3 | Citation number collision on ontology path | Fixed: namespaced chips (`F1`...), Diagram sources list, D-11 test, browser QA step |
| TP-4 | Badges spoofable in shares | Fixed: server-issued `diagram_id`; "cannot be spoofed" claim removed; unsigned-share known issue recorded (K16) |
| TP-5 | Validator ignores edge claims | Fixed: E1-E5, V6 as a ceiling, offline eval as a 0-unsupported gate, mocked tests |
| TP-6 | Diagrams look like clinical protocols | Fixed: revision title, study-aid line on card and export, no doses, no diagrams or videos on patient-scoped questions, G4 line |
| TP-7 | Proof scene selective | Fixed: "What we've measured so far", `/how` caveat verbatim, sample sizes and scope, limitation line, caveats in `facts.ts` (L-7) |
| TP-8 | Hero copy and book list before rights | Fixed: OQ-1 hard gate, `pilot` variant, L-11 noindex test, book titles as a G5 decision |
| TP-9 | Scene 1 patient journey | Fixed: same as ACC-21 |
| TP-10 | III.A.1 needs Terms | Fixed: `/terms` page (P1, blocks R2), V-10/V-11, verbatim re-read includes it |
| TP-11 | Topic in query string logged with IP; privacy page gaps | Fixed: `POST /api/videos`; log test; full storage list on `/privacy`; events enums exclude topic and ids |
| TP-12 | Real thumbnails in marketing scene and posters | Fixed: placeholder cards, L-10 never captures YouTube data, visual separation |
| TP-13 | Videos inside the cited article; label lost in fallback | Fixed: sibling section outside the article; header/label/terms in every shown state; V-11 |
| TP-14 | Tooltip accessibility gaps | Fixed: `aria-disabled`, persistent description, long-press limits, no overlap with trigger or video thumbnail/title, VoiceOver/TalkBack in G2 |
| TP-15 | Female attribution incomplete | Fixed, part declined: full change list, move out of "Historical", genitalia gap in UI note, Allen licence verify-or-drop. The suggested line "Derived from one donated body" was declined for now because `ATTRIBUTION.md:29` says the set is not a single-person scan; it waits for the DOI/metadata check (ACC-10) |
| TP-16 | 26k and latency claims | Fixed: count removed from landing and labelled internal; Explore scene dropped; latency shown only with its measurement or not at all |
| TP-17 | YouTube branding and hover zoom | Fixed: official icon file, no hover zoom at any motion setting |
| TP-18 | Ranking contradiction | Fixed: D-12 (at most 2 non-allowlisted, blocked videos never shown) |
| TP-19 | Data minimisation | Fixed: hashed cache key, 90-day TTL disclosed, III.E.4 id question in the re-read |
| TP-20 | DPDP and minors | Fixed: OQ-15, `/privacy` items, flagged as not legal advice |

**Totals**: 84 findings. 77 fixed (including recorded variants), 7 fixed with one specific suggestion declined (ACC-12, ENG-20, SUX-2, SUX-12, SUX-15, TP-1, TP-15), 0 declined outright.

**Reviewer conflicts and how they were decided**
- Video ranking (ACC-12 vs TP-18): one rule, at most 2 non-allowlisted cards, so the feature works with an empty allowlist and stays bounded.
- Quota day (ACC-13 vs ENG-20): rolling 24 h window, safe for any reset time.
- Video label (ACC-3 vs SUX-16 vs TP-13): short adapted line always visible (needs user approval), the note's full copy verbatim in the info tip and on `/terms`, one shared copy file.
- Landing gate (SUX-2 vs TP-8 vs ACC-4): strategy positions win by default (`pilot`, gated); the reviewer's public-landing option is kept as OQ-1 option B.
- Female subject wording (TP-15 vs ACC-10): no "one body" claim until the DOI/metadata check.
- Male toggle label (SUX-12 vs ACC-8): no "full" claim.
- Tooltip copy (SUX-15 vs the user's requirement): purpose and effect always, compressed for obvious controls.
- Touch tooltips (SUX-14 vs TP-14 vs the draft): long-press only on icon-only buttons and never for assistive setups; coach marks carry the touch explanation.

**Completeness pass (2026-11-15, after the review).** Eleven gaps found by a completeness check were filled in place. Facts re-checked at `e0eec26`: `store/ui.ts:10, :17-20` (`toast(text, ms = 2600)`, no action) and `ui/Toast.tsx` (renders text only); `store/chat.ts` has no `localStorage` or `persist` (no restored history exists); `apps/web/package.json` scripts are `dev, build, start, lint, check` with no unit runner; `api/main.py:111` is `POST /api/chat/stream`; `AtlasScene.tsx:298` (`frame3`) and `:502-506` (reset branch); P0/P1/P2 working days counted from the calendar (18 Nov is a Wednesday); female alternatives from [fem §3.2-3.6].

| Id | Gap | Action |
|---|---|---|
| GAP-1 | R1 decline copy was wrong for `generator_error` and `budget`; no UX for 429, 403, 503; no reason-to-copy map | Fixed: R1 UX table now has one row per `reason` and status (validator decline without retry; `generator_error` and client abort "Couldn't draw it right now." with Retry; `budget` "Flowcharts are paused for today." no retry; 429 "Too many requests, try again in a minute."; 403/503 hide the chip); D-17 single copy map `web/lib/copy/diagram.ts`; one acceptance criterion per row; unit test for the map |
| GAP-2 | Client pages had no way to learn the `diagram`, `videos`, `female_atlas` flags | Fixed: D-15 root-layout server fetch into a `FeaturesProvider` (all false on failure; ASSUMPTION on dynamic rendering, with a client-fetch fallback); V-13 for videos; F-9 for the female atlas; flag-off rows in the R1 and R2 UX tables and R5 flag gating; Given/When/Then for each; §5.6 updated; owner WS-X in P0 |
| GAP-3 | Related topics rode on `/api/videos`, so they vanished with the videos flag, key, quota or lazy fetch | Fixed: `related` moved to the `topic` SSE event and removed from the `/api/videos` response; rendered by `RelatedTopics.tsx` inside the answer, independent of videos; shares store `related` with `topic`; V-9 reworded; V-9 seam test in `test_api_v2.py` (certified only, max 6, ordering) and a unit test for the append-turn helper; acceptance criterion with the videos flag off |
| GAP-4 | `answer_sig` serialisation undefined; shared and restored answers had no sig | Fixed: canonical serialisation (documented keys only, NFC, `\n` line endings, sorted keys, compact separators, UTF-8, integer indices, citations sorted by index, one server implementation for sign and check); D-16: sig in memory only, not in the share payload, chip hidden without a sig and on shared pages; no restored history exists today (verified); round-trip test and acceptance criterion |
| GAP-5 | No web unit test runner; R4's only test needed Playwright and 90 MB of models | Fixed: §5.5 names Vitest (new dev dependency added to OQ-12; lead owns config and script; workstreams own their `*.test.ts`), with `node --test` plus Node type stripping as the fallback if declined; G1 runs `test:unit`; model-free R4 unit test over extracted `resetIntent` and `computeGoalPose` (ASSUMPTION that the `frame3` math extracts cleanly); what G1 runs if Playwright is declined |
| GAP-6 | Many new or shared files had no owner; `package.json` hotspot; C1 lines in WS-A files; cookie and Videos placement unassigned | Fixed: §1.3 extra ownership table (all listed files); `package.json` and lockfile owned by the lead, changes by request; C1 atlas and `Concept3D` lines by WS-A after R4, `/how` line by WS-L with `/how` QA; WS-X writes `mm_asked` in `store/chat.ts` and renders `<Videos>` from `AnswerCard.tsx` as a sibling of the `<article>`; `/privacy` and `/terms` moved to WS-L |
| GAP-7 | Phase dates did not fit the per-workstream load and contradicted OQ-8 = B | Fixed: new §1.2a with trigger-based dates, 25% buffer, re-estimates (R3 primitive M 2 d, toast action, `safety_cues`, hallway test), P1 and P2 in parallel on disjoint files, P3 built in parallel and shipped last, and an explicit OQ-8 = B schedule (P0 only, then a hold point); the old block's dates marked superseded |
| GAP-8 | No test of "awe-inducing" utility; no performance or a11y bar for the landing | Fixed: pre-release hallway test (3-5 students, 60 s, two questions, pass at 4 of 5 or 3 of 3) as a P2 release gate; at least 50 fps median scroll on a named mid-range Android (device ASSUMPTION) with a static fallback for that class if missed; §5.2 row; keyboard and VoiceOver Given/When/Then over the five scenes |
| GAP-9 | "Very similar" female model not reconciled with an organs-only set; no flag; no a11y spec; reviewer unnamed | Fixed: OQ-17 asks the user to accept "organs-only female reference", with the rejected alternatives from [fem §3.2-3.6]; D-8 updated; flag gating and F-9; accessibility table (radiogroup, roving tab stop, arrow keys, dialog focus trap and return, progressbar and quarter-step announcements) and F-10 with acceptance criteria; reviewer named by the user via OQ-17 (UNKNOWN today), about half a day of reviewer time on P3's critical path |
| GAP-10 | Touch long-press relied on screen-reader detection; coach marks for features WS-K does not own; primitive under-estimated | Fixed: testable rule (touch pointer, 500 ms, under 10 px, icon-only buttons only, `click` never cancelled so assistive double-tap always activates); T-4 rewritten with a unit test; coach marks owned by each feature's workstream and rendered only when the feature is live (T-9); primitive re-estimated M 2 d |
| GAP-11 | Reset had no loading state; the toast's action support was assumed; no rollback for unflagged P0 changes | Fixed: R4 states table with "Atlas still loading" (`aria-disabled`) and RV-7 plus a criterion; toast action support **verified absent** and assigned to WS-K before R4 (R4 ships without Undo only with the user's yes); §5.6 rollback per phase (P0 by redeploy, with a proposed `ratelimit` kill-switch key in the flags file; P1 and P3 by flag plus redeploy for additive unflagged parts; P2 by redeploy) |

**Superseded review-log wording**: the "Touch tooltips" conflict line above ("never for assistive setups") is replaced by GAP-10's rule; the §1.2 block's dates are replaced by §1.2a.
