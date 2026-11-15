# Next-release code audit (requirements A-F)

As of e0eec26 (2026-11-15). Read-only audit; every line reference is to that commit. Paths are relative to the repo root; `apps/web/src` is abbreviated `web/`.

## A. Landing page at `/`

### Today
- `/` is the Ask page: `web/app/page.tsx:1-5` renders `<ChatView />` (As of e0eec26).
- Nav is a static list in `web/components/shell/nav.ts:13-19`; Ask is `{ href: '/', ... tab: true }` (nav.ts:14). `isActive` special-cases `/`: active for `pathname === '/'` or any `/a/*` (nav.ts:21-24). Used by the desktop rail and the mobile tab bar in `web/components/shell/AppShell.tsx`.

### Every link or navigation to `/` or `/?q=`
| Where | What |
|---|---|
| `web/components/shell/nav.ts:14` | Nav item "Ask" `href: '/'` (feeds rail and tab bar) |
| `web/components/shell/nav.ts:22` | `isActive` rule for `/` and `/a/` |
| `web/components/shell/AppShell.tsx:25` | Desktop rail logo link `href="/"` |
| `web/components/shell/AppShell.tsx:61` | Mobile top-bar logo link `href="/"` |
| `web/components/why/VerdictCard.tsx:13` | `askHref(q, go=true)` builds `/?q=<enc>&go=1`; used at :45 (`go=false`, sub-question chip) and :99 (viva links, `go=true`, or `go=false` when `readOnly`) |
| `web/components/chat/ChatView.tsx:70-85` | `QueryPrefill` reads `?q=` and `go=1`, then `history.replaceState(null,'','/')` (:81) |
| `web/components/chat/SharedAnswer.tsx:87` | Share page CTA `LinkButton href="/"` |
| `web/app/how/HowClassic.tsx:116` | CTA `LinkButton href="/"` ("Ask" at end of the classic how page) |
| `web/components/story/Story.tsx:243` | CTA `LinkButton href="/"` ("Ask a question") at end of the /how story |
| `web/app/not-found.tsx:9` | 404 CTA `LinkButton href="/"` |

Not found: no `router.push('/')`, `redirect(` or `'/?q='` in `apps/web/src` or `next.config.mjs`. The only `router.push`/`replace` calls are explore/concept/atlas paths (`ExploreView.tsx:95`, `ConceptView.tsx:121`, `LocalGraph.tsx:144,233`, `AtlasView.tsx:54`). The API does not emit `/?q=` links (grep of `api/`, `rag/` found none). Share links are generated client-side as `${origin}/a/${id}` (`web/components/chat/Actions.tsx:17`) and are unaffected by moving Ask.

Other things tied to `/`: `web/store/chat.ts` (chat state is a zustand store, so moving the page does not lose thread state across in-app nav; not read in depth), the `/a/[id]` page being "owned" by the Ask nav item (nav.ts:22), and `web/app/layout.tsx:9-13` metadata (title template, `robots: noindex`).

### What moving Ask to `/ask` requires
1. Create `web/app/ask/page.tsx` rendering `<ChatView />`; make `web/app/page.tsx` the landing page.
2. nav.ts: Ask `href: '/ask'`; fix `isActive` (`/ask` and `/a/*`); decide whether Home/landing is a nav item or only the logo link (AppShell.tsx:25,61 can stay `/`).
3. Update the Ask-bound CTAs to `/ask`: SharedAnswer.tsx:87, HowClassic.tsx:116, Story.tsx:243; keep not-found.tsx:9 on `/` or switch (product call).
4. VerdictCard.tsx:13: change prefix to `/ask?q=`.
5. ChatView.tsx:81: `replaceState` to `/ask`, not `/`.
6. Old links: `/?q=...&go=1` already circulate (viva links from /why, any pasted URLs). `next.config.mjs` has only a `rewrites()` for `/api/*` (next.config.mjs:13-17), no `redirects()`. A server redirect cannot be keyed purely on the path `/` because `/` becomes the landing page; use `redirects()` with `has: [{ type: 'query', key: 'q' }]` from `/` to `/ask` (Next forwards the query string), or do it client-side in the landing page. Either keeps `?q=&go=1` working. No Caddy change needed: Caddy proxies all non-`/api`, non-`/models` paths to `v2-web:3000` (`deploy/v2/Caddyfile.v2-block:15-18`).
7. `isActive` for `/` on the landing page; mobile tab bar has four `tab: true` items (nav.ts:14-17); adding Home would make five.

### Reusable three.js assets for a landing hero (As of e0eec26)
- `web/components/story/*` (2031 lines total): `Story.tsx` (255), `controller.ts` (977, the three.js scene driver), `shaders.ts` (150), `engine.ts` (33), `math.ts`, `palette.ts`, `chiasm.ts` (52, loads atlas.json via `modelUrl('/models/atlas.json')` at chiasm.ts:7), `data.ts` (119), `story.css` (182), `StoryEntry.tsx` (26). `StoryEntry` is the pattern for lazy loading: `next/dynamic` with `ssr: false`, plus an error boundary that falls back to `HowClassic` (StoryEntry.tsx:7-24); its comment says three.js "only ever loads here, on /how".
- Library map data: `apps/web/public/story/story.json` (10,139 bytes) and `library.bin` (477,441 bytes). Loaded by `loadStory` in `data.ts:36-45`. LIB2 format (`data.ts:52-55`): 16-byte header (magic "LIB2", uint32 N at offset 4, float32 scale at offset 8), then Int16 x3 galaxy positions, Int16 x3 cluster positions, Uint8 book id per point (13 bytes per point; size check at data.ts:54). Position decode: value * scale/32767 (data.ts:57). `story.json` carries `n` plus book/cluster metadata. Mobile uses an optional subsample (`loadStory(mobile, ...)`).
- `web/components/canvas/*` (1222 lines): `AtlasScene.tsx` (579, WebGL renderer, OrbitControls, RoomEnvironment, merged-geometry per system, custom state texture), `AtlasCanvas.tsx` (27 lines, wrapper), `model-download.ts` (chunk fetch + gzip decode + IndexedDB cache), `explosion-layout.ts`, `pointer-tap.ts`. A `compact` mode already exists (non-interactive embed: no zoom/pan, loads only the selected parts: AtlasScene.tsx:111-114, 207): usable for a hero body, but the full body is ~33 MB of models (`docs`: `deploy/atlas/README.md` says models ~33 MB gzip-served), so a landing hero should not load it eagerly.
- Models: served same-origin at `/models` by Caddy from `/srv/atlas` with `precompressed gzip`, `Cache-Control public, max-age=604800` (Caddyfile.v2-block:9-14). Models are excluded from the web build (`deploy/v2/push.sh:14-21`; `NEXT_PUBLIC_MODELS_BASE=/models`). Note: neither models nor `atlas.json` are in the repo; they come from the human-atlas build (`deploy/atlas/build_atlas.sh`).
- three version: `three ^0.159.0` with `transpilePackages: ['three']` (apps/web/package.json; next.config.mjs:8). No postprocessing library is installed (no `@react-three/*`, no `postprocessing`); everything is hand-rolled shaders.

## B. Diagram maker

### What exists (Streamlit only)
- `rag/diagrams.py` (As of e0eec26) builds **Graphviz DOT text** (module docstring :1-17; `build()` returns `{"kind","subject","dot","sources"}`, diagrams.py:251-281). Two kinds: `case` flowchart (condition -> presentation -> differentials -> workup -> treatment, with contraindication warnings) and `drug` mechanism (drug -> targets -> treats / adverse / contraindicated). Output is DOT, not Mermaid, not an image.
- Inputs: `build(question, answer_text="", condition=None, drug=None, use_cache=True)` (diagrams.py:251-252). `pick_subject` (diagrams.py ~:60-75) chooses a drug or condition by matching the question text against ontology labels; `answer_text` only bolds boxes whose words appear in the answer (`highlight`, `penwidth 2.5`, in `_Dot.node`).
- Grounding: every box is a **certified ontology fact's object label** with a numbered source `[n]` carrying book/chapter/page (`_Dot.source`, `onto.cite(f)`); docstring states "Nothing is generated by an LLM". So it is grounded in **certified ontology facts**, not in the answer's cited retrieval passages. A question whose topic is not in the ontology returns `None` (diagrams.py:258-262, 272-273, 282-283; "never raises"). Cache: `data/ontology/diagrams/<sha>.json`, keyed on VERSION + ontology mtime + subject + answer words (diagrams.py:264-268); git-ignored because it derives from copyrighted corpus (docstring).
- Streamlit hook `render()` (diagrams.py:286-308) draws via `st.graphviz_chart`; called from `app.py:404` (`diagrams.render(st, question, res.text, condition=(conds or [None])[0], ...)`). `docs/diagram_evaluation.md` records that image-model diagrams (PaperBanana) were evaluated and not used.

### v2 exposure: none
- `api/main.py` routes: `/api/chat/stream` (:111), `/api/why/stream` (:151), `/api/spatial/resolve` (:159), `/api/concepts/*` (:169,174), `/api/answers` (:182,190), `/api/feedback` (:198), `/api/health` (:204), plus `story.router` (:210). No diagram route; grep for "diagram" in `api/` and `apps/web/src` returns nothing.
- `apps/web/package.json` dependencies: clsx, d3-force, lucide-react, marked, next, react, react-dom, tailwind-merge, three, zustand. No mermaid, no graphviz/viz.js/d3-graphviz, no react-flow. (d3-force 3.0.0 is used by `explore/LocalGraph.tsx` for concept graphs.)

### Implications
Cheapest path: add `GET/POST /api/diagram` that calls `diagrams.build(question, answer_text, condition)` (it is pure Python, no Streamlit dependency apart from `render`) and render DOT in the browser with a client-side Graphviz WASM package (new dependency) or convert DOT to a small JSON node/edge list and lay it out with the existing `d3-force`/SVG (no new dependency but lower quality than Graphviz layout). Coverage gap: only topics with certified ontology facts get a diagram; a "flowchart of the answer's topic" for any question would need either a new grounded generator over the cited passages (new work, LLM, must be validated against passages) or accepting `None` for uncovered topics. Decision for the PRD.

## C. YouTube videos after an answer

- Nothing exists. `grep -i "youtube|ytimg|video|iframe"` over `apps/web/src`, `api/`, `rag/`, `app.py` finds one hit, `app.py:1183`, an unrelated Streamlit iframe for the 3D atlas. No API route, no types in `web/lib/api.ts`.
- Where a "Videos" section goes: `web/components/chat/AnswerCard.tsx`, inside the `<article>` after `<SourceList .../>` (AnswerCard.tsx:97) and `<SpatialChips actions={turn.spatial} />` (:98), before the trace disclosure (:99), i.e. gated on `a.status` not declined. Alternatively below the action row (:101-113) but that row sits after a `border-t`; Videos belong above it. `Actions.tsx` (`ShareButton`, `FeedbackButton`, :17 and :73-113) is the action row, not content; it would only host a "Show videos" trigger if lazy-fetching on demand. The persisted share payload is `saveAnswer('chat', turn.question, { answer: a, spatial: turn.spatial })` (AnswerCard.tsx:106), so videos should be added to that payload (and `SharedAnswer.tsx`) if shared pages should show them.
- New pieces needed: a backend route (YouTube Data API key, query derived from the question or the concept label, server-side so the key is not exposed; filter to educational channels and cache), a `videos` field on the turn in `web/store/chat.ts`, a `Videos` component. Medical-safety note: videos are outside the "every claim cites the textbook" contract (layout.tsx:11 description); label them as external, not part of the cited answer.
- CSP / headers: **none exist to block thumbnails.** `apps/web/next.config.mjs` defines no `headers()` and no `images` config (whole file read, 22 lines). `deploy/v2/Caddyfile.v2-block` sets only `X-Robots-Tag` (:4), a robots.txt response (:5-8), `Cache-Control` for `/models` (:14), and gzip. No `Content-Security-Policy` anywhere in `apps/web`, `deploy/v2`. So plain `<img src="https://i.ytimg.com/vi/<id>/hqdefault.jpg">` works as-is. If `next/image` is used instead, `images.remotePatterns` must allow `i.ytimg.com`. If an embed player is used instead of thumbnail-then-link, `youtube-nocookie.com` iframes also work with no change today. Risk: adding a CSP later would need `img-src https://i.ytimg.com` and `frame-src https://www.youtube-nocookie.com`. Privacy note: loading ytimg thumbnails leaks the student's IP to Google; the app currently makes no third-party requests except Google Fonts via `next/font` (which self-hosts at build time).

## D. Hover tooltips on all buttons

### UI kit
No Tooltip primitive. `web/components/ui/index.ts` exports Button/LinkButton/buttonClass, Chip/Tag, StatusPill, Skeleton, CitationChip, Markdown, Drawer, Toaster. Only "tooltip" in `apps/web/src` is `role="tooltip"` on the 3D hover label created imperatively in `AtlasScene.tsx:384`. `ui/README.md` documents no tooltip. `Button` and `Chip` spread `...rest` onto the DOM element, so `title=` passes through (Button.tsx:32-36).

### Inventory (regex scan of JSX tags `Button | LinkButton | Chip | button | Link | a | CitationChip` in `apps/web/src/**/*.tsx`, As of e0eec26)
Total **82 JSX sites**, of which **15 already carry `title=` or `aria-label=`** in the opening tag; **67 have neither**. Caveats: the count is by JSX site, not runtime instances (e.g. the story rail renders one `<button>` per chapter from a `.map`, Story.tsx:195; the 3D atlas layer toggles and `KINDS` radio buttons also come from `.map`s); it includes the 4 definitions inside `ui/Button.tsx` and `ui/Chip.tsx`; plain `<a>`/`<Link>` nav items count. Controls built in imperative three.js code (the hover label) are excluded. Treat "about 80" as the working number and 62-65 as the real set needing new tooltips once definitions and already-labelled controls are removed.

| File | Sites | Already labelled | Unlabelled line numbers |
|---|---|---|---|
| components/canvas/AtlasView.tsx | 11 | 1 | 183, 194, 197, 206, 214, 236, 266, 280, 289, 304 (Isolate :183-193 has `title`; Reset view :194, Layers :197, "Default" :206) |
| components/explore/ConceptView.tsx | 10 | 0 | 57, 63, 127, 150, 154, 243, 267, 277, 293, 302 |
| components/shell/AppShell.tsx | 6 | 3 | 16, 33, 89 (nav links; logo links have aria-label) |
| components/chat/Actions.tsx | 5 | 1 | 73 (Report a problem chip), 80 (radio buttons), 105, 108 (Cancel, Send) |
| components/explore/ExploreView.tsx | 4 | 1 | 155, 200, 229 |
| components/story/Story.tsx | 4 | 2 | 243, 244 (rail dots at :195 have aria-label) |
| components/why/VerdictCard.tsx | 4 | 0 | 45, 48, 98, 112 |
| components/why/WhyForm.tsx | 4 | 0 | 33, 89, 103, 110 |
| components/chat/Cards.tsx | 3 | 0 | 17, 52, 58 |
| components/chat/ChatView.tsx | 3 | 1 | 29, 119 |
| components/chat/SourceList.tsx | 3 | 0 | 15, 35, 56 |
| components/canvas/SelectionPanel.tsx | 2 | 0 | 122, 157 |
| components/chat/Composer.tsx | 2 | 2 | none (send and stop labelled) |
| components/story/TryQuestion.tsx | 2 | 0 | 79, 86 |
| components/why/WhyView.tsx | 2 | 0 | 46, 49 |
| components/ui/Button.tsx, Chip.tsx | 2 + 2 | 0 | definitions (Button.tsx:36,52; Chip.tsx:17,23) |
| app/how/HowClassic.tsx | 2 | 0 | 116, 119 |
| components/ui/Markdown.tsx | 2 | 2 | none |
| components/ui/CitationChip.tsx | 1 | 0 | 16 (numbered source markers; they have visible number only) |
| components/ui/Drawer.tsx, shell/ThemeToggle.tsx | 1 + 1 | 2 | none |
| components/chat/AnswerCard.tsx (:31 view-in-3D chips), chat/SharedAnswer.tsx (:87), chat/StepTrace.tsx (:72), explore/Concept3D.tsx (:77), app/not-found.tsx (:9), app/error.tsx (:11) | 1 each | 0 | listed |

**Total: 82 sites (15 labelled, 67 not).** The 3D atlas toolbar is `AtlasView.tsx:183-199` (Isolate, Reset view, Layers) plus the layer panel toggles; Isolate is the only one with a `title`. Story rail dots: `Story.tsx:195`, one site, `aria-label="Chapter N: ..."`, no hover title.

### Implementation sketch
Cheapest consistent approach: add a small `Tooltip` (or `title` pass-through convention) to the UI kit and apply it in `Button`, `Chip`, `LinkButton` via a `tip` prop so the ~60 call sites change by one prop; icon-only controls first. Native `title` is zero-dependency but not touch-accessible (mobile has no hover), appears after ~1 s delay, and is not styled for dark mode; a custom primitive needs focus/hover handling, `aria-describedby`, and a portal to avoid clipping inside `Drawer` and the `overflow` containers. Mobile is the main audience; flag that tooltips will not show on touch.

## E. 3D atlas "Reset view"

### What it does today (confirmed bug)
- Button: `web/components/canvas/AtlasView.tsx:194-196`: `<Button ... onClick={reset}>` where `reset` comes from `useAtlasStore()` (AtlasView.tsx:24).
- Store: `web/lib/atlas-store.ts:61`: `reset: () => set((s) => ({ resetNonce: s.resetNonce + 1, isolate: false }))`. So it bumps a counter and turns Isolate **off**. Nothing else.
- Scene: `AtlasScene.tsx:502-506`: when `resetNonce` changes, `userMoved = false; frame3(partIdxRef.current, true)`. `partIdxRef.current` = the currently **selected** parts (`AtlasScene.tsx:79-80`, from the URL `?select=` via `AtlasView.tsx:14-18,54`). `frame3` with a non-empty list frames **the selection** at distance `* 2.1` (AtlasScene.tsx:298-324), not the whole body.
- Result: with a structure selected (the state where users press Reset), Reset un-isolates and re-frames the *same selected structure*; the selection stays in the URL and the ghosted context stays. The user-visible effect is "it only toggles Isolate off". With nothing selected it does re-frame the whole body, but with `useAll` branch only after the user had moved (works), so the bug only appears when something is selected. This matches the report.

### Default camera pose
- Constructor/initial: `PerspectiveCamera(FOV = 34, ...)` (AtlasScene.tsx:48,123); `goalTarget = (0, 0.85, 0)`, `goalPos = (1.2, 1.1, 3.4)` (AtlasScene.tsx:280-281), but these are overwritten by the first `frame3` call on load (:372, `frame3(partIdxRef.current, false, true)`, instant).
- The real default whole-body pose is computed, not fixed: `frame3([], true)` -> bounding box of all non-integumentary wanted parts, direction `(0.32, 0.08, 1)` normalised (slightly right of front, near eye level), `dist = max(fitH, fitW, size.z*0.9) * 1.18 + size.z/2`, min 1 (AtlasScene.tsx:298-324), further shifted by the panel `inset` through `setViewOffset` (:288-296). `controls.maxDistance = max(30, dist*3)`.

### Minimal correct fix
Reset should clear the selection and isolate, then frame the whole body:
1. In `AtlasView.tsx:194`, `onClick={() => { reset(); setSelection([]); }}` (`setSelection` is defined at AtlasView.tsx:51-56 and strips `?select=` via `router.replace`). That makes `partIdxRef.current` empty, so the existing `resetNonce` branch (AtlasScene.tsx:502-506) and the highlight-change branch (:489-494) call `frame3([], true)`, the whole-body pose above.
2. Keep `isolate: false` in the store (:61) and keep the `layers` selection (Layers has its own "Default" button, :206 / `resetLayers`).
3. Optional hardening: pass an explicit flag so the scene always uses `useAll` on reset (e.g. `frame3([], true)` in the reset branch at :502-506) so it still works if a parent keeps a selection controlled elsewhere (e.g. embeds). Edge case to test: pressing Reset twice in a row while no selection exists (nonce still increments, framing runs; fine), and mobile with the bottom sheet inset (the inset logic runs in `frame3`, so the default pose respects it).
Size: S (2-4 lines plus a manual check on desktop and mobile). No tests exist for it in the repo (no test files under `apps/web`).

## F. Female anatomy

### How the male atlas loads
- Manifest: `atlas.json` fetched from `modelUrl('atlas.json')` (`web/lib/atlas-store.ts:42`), cached in IndexedDB as `'atlas.json'` (:45,49 via `web/lib/idb.ts`). `modelUrl` re-roots to `MODELS_BASE` = `NEXT_PUBLIC_MODELS_BASE || '/models'` (`web/lib/anatomy.ts:180-186`). The story chiasm also hard-codes `/models/atlas.json` (`story/chiasm.ts:7`).
- Schema (`web/lib/anatomy.ts`): `Atlas { version, sex?: 'male', source?, scope?, parts[], concepts[], chunks[], triangles }` (:68-77). `Part { id, name, conceptId, system, chunk, positions, normals, indices, vertexCount, indexCount, bounds }` (:42-54), where `positions/normals/indices` are **byte offsets** into the chunk `ArrayBuffer`. `Concept { id (FMA id), name, elements[] }` (:56-60). `ChunkMeta { url, bytes, gzip?, gzipBytes? }` (:62-67); chunk files are `body-N.bin` with `body-N.bin.gz` variants.
- Binary layout (read in `AtlasScene.tsx:215-221`): per part, `Float32Array(buffer, p.positions, vertexCount*3)`, normals `Int16Array(..., vertexCount*3)` normalised, indices `Uint32Array(..., indexCount)`; geometry per system is merged (`mergeGeometries`) into one mesh with a `partIndex` attribute; visibility/selection is driven by a per-part state texture (AtlasScene.tsx:340-358). Chunks load 3 at a time with progress, decompressed with `DecompressionStream` and cached per `version:url` in IndexedDB (`canvas/model-download.ts:21-37`).
- Systems are a fixed 15-id enum with colours (`anatomy.ts:1-60`); `DEFAULT_VISIBLE` excludes integumentary (:94-109).
- FMA ids link everything: `rag.atlas`/the crosswalk `data/graph/atlas_crosswalk.jsonl` maps ontology structure labels to FMA ids (`deploy/atlas/README.md`), `/api/spatial/resolve` returns `fma_ids` (`api/schemas.py:95-103`), and the web uses `atlasHref(fmaIds)` -> `/atlas?select=FMA...` (`web/lib/format.ts:23-25`).
- Provenance: BodyParts3D 4.0, adult **male** reference, CC BY 4.0 (`deploy/atlas/ATTRIBUTION.md`); 2,234 meshes, 3,432 FMA concepts. The same file records a **historical female set**: HuBMAP "3D Reference Organ Set for Female v1.5" (CC BY 4.0), "Earlier repository revisions included" it, 888 meshes, 1,073 source nodes, "skeleton and muscle coverage is partial", with placenta/umbilical structures to hide by default, and gives the DOI and the GLB URL (`ATTRIBUTION.md:17-26`). The processing recipe it describes (Y-up metres onto the stage, weld coincident vertices, average normals, meshoptimizer 0.2% relative error, quantise normals to 16 bit, curated systems and colours) is the format a new set must reach. The build scripts for that set are not in this repo (the atlas build is in the external clone, `build_atlas.sh` clones `human-atlas` at a pinned commit and applies `deep-link.patch`).
- Hosting: files live under `/srv/atlas` on the VM, served at `/models/*` (Caddyfile.v2-block:9-14); not in git, rsync-excluded from the web bundle (`deploy/v2/push.sh:21`).

### What a female set needs
1. Same manifest shape: a second `atlas-female.json` (or `models/female/atlas.json`) plus `body-N.bin(.gz)` chunk files in the exact layout above, `sex: 'female'` (extend the type at anatomy.ts:72, currently `'male'`).
2. **FMA ids must be shared** with the male set wherever the structure is the same, otherwise `?select=FMA...`, the crosswalk, spatial resolution and the "View in 3D" chips (AnswerCard.tsx:31) break. HuBMAP organs use different ids (UBERON/ASCT+B) from BodyParts3D (FMA), so a mapping table HuBMAP node -> FMA id is the real work; structures with no match need new concept ids and will not be reachable from answers. The historical female set contained "selectable individual or compound concepts".
3. Coverage: no female-specific anatomy exists today in the male set (the atlas has "no uterus or thyroid", `deploy/atlas/README.md`). The `reproductive` system exists but is male-biased. A female model adds uterus/ovaries/breast etc. but, per the attribution file, partial skeleton and muscle: a mixed approach (shared male skeleton/muscle + female organ set) would need a common coordinate frame, which the attribution file does not promise.
4. Licence: CC BY 4.0 for both, add the HuBMAP credit to the footer and `ATTRIBUTION.md`.

### Where a Male / Female switch lives
- State: `web/lib/atlas-store.ts` (add `sex: 'male' | 'female'`, change `loadManifest` to key the fetch and the in-memory `atlas` by sex; the `inflight` guard at :28 and `if (get().atlas) return` at :37 assume one atlas). `buildIndex` and `useAtlasStore().atlas/index` are used by `AtlasView`, `Concept3D` (explore embed), and `canvas/model-download.ts` (memo/IndexedDB key `${atlas.version}:${chunk.url}` already differs by version, so female chunks will not collide if `version` differs; make sure it does).
- UI: toolbar in `AtlasView.tsx:183-199` (next to Isolate / Reset view / Layers) is the natural place; also persist as `?sex=female` in the URL, which `AtlasView.tsx:51-56` currently rewrites to drop on every selection change (it only writes `?select=`), so the helper must preserve other params.
- Scene: `AtlasScene` keys its effect on `atlas`; switching sex rebuilds the scene (disposal paths exist: `disposed`, `geometries`). The concept-page embed `Concept3D.tsx` should default by the same store.
- Backend: none required, if FMA ids are shared. `?select` links stay valid.
- Risk to flag: the per-part state texture and `partIdx` are indices into one `atlas.parts`, so selection must be re-resolved by FMA id after a switch (`resolveSelection` in AtlasCanvas/AtlasView; not read in depth).

## Summary table

| Req | Files touched | Size | Risks |
|---|---|---|---|
| A. Landing at `/` (three.js), Ask to `/ask` | new `app/page.tsx` + `app/ask/page.tsx`; `shell/nav.ts`; `AppShell.tsx` (logo links); `VerdictCard.tsx:13`; `ChatView.tsx:81`; `SharedAnswer.tsx:87`; `HowClassic.tsx:116`; `Story.tsx:243`; `not-found.tsx:9`; `next.config.mjs` (add `redirects()` for `/?q=`); new landing three.js scene reusing `story/*` | L (the page itself); S for the Ask move and redirect | Old `/?q=&go=1` links must keep working (redirect keyed on `q`); landing payload (three.js + library.bin 477 KB, or the 33 MB atlas) hurting first load on student mobile data; WebGL fallback needed (StoryEntry pattern); five-item mobile tab bar; `/a/*` active-state logic |
| B. Diagram maker | new API route in `api/main.py` calling `rag/diagrams.py`; `api/schemas.py`; `web/lib/api.ts`; new `chat/Diagram.tsx`; `AnswerCard.tsx`; new web dependency for DOT rendering (or d3-force); `store/chat.ts`, `saveAnswer` payload | M (reuse existing DOT) to L (if topic coverage must go beyond ontology) | Only ontology-certified topics are covered; diagram is not grounded in the answer's own cited passages; DOT-in-browser dependency size; copyright note: cache is git-ignored because it derives from the corpus; long DOT on mobile |
| C. YouTube videos | new API route (YouTube Data API key, server-side, cached); `schemas.py`; `lib/api.ts`; `store/chat.ts`; new `chat/Videos.tsx`; `AnswerCard.tsx` (after :98); `SharedAnswer.tsx`; `next.config.mjs` only if `next/image` is used | M | No CSP/headers block `i.ytimg.com` today (none configured); API quota/cost and key handling; relevance and quality of results for medical topics; external content outside the cite-or-decline contract (needs clear labelling); thumbnail requests leak IP to Google; adding a CSP later needs `img-src`/`frame-src` |
| D. Hover tooltips on all buttons | `ui/Button.tsx`, `ui/Chip.tsx`, new `ui/Tooltip.tsx` + `ui/index.ts`, then 25-ish call-site files (67 unlabelled sites across 28 files, table in D) | M (primitive S, sweep M) | No hover on touch devices, the main audience; clipping inside `Drawer` and overflow containers; a11y duplication (title plus aria-label); rail dots and nav links need labels not just tooltips |
| E. Atlas Reset view | `components/canvas/AtlasView.tsx:194` (and optionally `AtlasScene.tsx:502-506`) | S | Must also clear `?select=`; verify with bottom-sheet inset on mobile; no tests present |
| F. Female anatomy | `lib/anatomy.ts` (type, URL helper); `lib/atlas-store.ts`; `AtlasView.tsx` toolbar and URL handling; `AtlasScene.tsx` (rebuild on switch); `Concept3D.tsx`; `story/chiasm.ts:7`; new model files under `/srv/atlas` + deploy script; `ATTRIBUTION.md`; a conversion pipeline from HuBMAP GLB (not in repo) | L | Needs FMA-id mapping from HuBMAP nodes (largest cost); partial skeleton/muscle in the HuBMAP female set; new ~30+ MB of models and cache keys; scene rebuild on switch; selection indices differ between atlases; licence credit |
