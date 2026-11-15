# MedEvolv Mentor API

`uvicorn api.main:app --port 8000` (run from the repo root; settings and `.env` come from `rag.config`).
CORS allows `http://localhost:3000` and `http://127.0.0.1:3000` only. No auth. Wire types live in `api/schemas.py`.

## SSE framing

Streaming endpoints return `text/event-stream`. Each message is exactly:

    event: <name>\ndata: <one-line JSON>\n\n

`POST` bodies are JSON, so use `fetch` + a stream reader (not `EventSource`).

### POST /api/chat/stream
Body `{question: str (1..2000)}`. Order: `step`* -> `answer` -> `spatial` -> `topic` -> `done`. `error` ends the stream early.

### POST /api/why/stream  ("Why was I wrong?")
Body `{question: str (1..3000), options: str[] (2..6), chosen: int}`; `chosen` indexes `options`
(out of range -> HTTP 422 before streaming). Order: `step`* -> `verdict` -> `done`. `error` ends the stream early.

### Events
| event | data |
|---|---|
| `step` | `{stage, title, detail, status: "ok"\|"warn"\|"stop", ms}` |
| `answer` | `{text, status, route, citations: AnswerCitation[]}` (chat only) |
| `spatial` | `{actions: [{action:"highlight", fma_ids, label, tier:"navigation"}]}` (chat only) |
| `topic` | `{topic: str \| null, related: [{id, label, predicate, tier: "certified"}]}` (chat only), below |
| `verdict` | `VerdictEvent` (why only), below |
| `done` | `{ms}` |
| `error` | `{message, error_type}` (no internals leaked) |

`topic` (additive; old clients ignore it) is emitted after `spatial`, before `done`. `topic` is a structured label,
never question or answer prose: the ontology condition or drug the question is about (`rag.diagrams.pick_subject`),
else the first `spatial` highlight label, else the first concept in the question or answer that resolves exactly to an
ontology concept (`api/topic.py`). `related` is at most 6 certified `links_out` of that concept (most books first).
Declined answers (`status != "answered"`) and patient-scoped questions (`api/safety_cues.patient_scoped`, which also
includes the `rag.answer.PERSONAL` regex) always get `{topic: null, related: []}`. A failure computing it also gives
that; it never turns an answer into an `error`.

`AnswerCitation`: `{index, cited, book, edition, chapter, pages, section_id, excerpt}`. `index` is the `[n]` used in the
text; `excerpt` is at most 300 chars (+ an ellipsis). Pointers only, never full passages.

`VerdictEvent`:

    {status: "verdict" | "insufficient",
     correct_option: int | null,          // index into options; null when insufficient
     chosen_wrong_because: str,           // if chosen == correct_option it says the choice was correct
     explanation: str,                    // markdown with [n] markers into citations
     citations: AnswerCitation[],
     viva_questions: str[]}               // exactly 3 when status == "verdict", [] otherwise

`status: "insufficient"` means the retrieved passages did not ground a verdict (nothing relevant, the model said so, no
valid `[n]` citations, bad option letter, malformed JSON after one retry). `explanation` is then
"The textbooks in the library don't settle this." A model/backend failure is an `error` event, never a traceback.

## REST

### GET /api/concepts/{label_or_id}
Label (case-insensitive) or ontology id; ids may contain `/`. 404 `{"detail": "Unknown concept"}` if unknown.
`GET /api/concepts/search?q=prefix&limit=20` (unchanged) -> `[{id,label,type,degree}]`.

`ConceptPage`:

    {id, label, type, aliases[], books[] (book ids), degree,
     sections: [{section_id, book_id, title, path, primary, tier:"navigation"}],   // primary first
     links_out: [{id,label,type,predicate,tier}], links_in: [...],                  // capped at 100 each
     links_out_total, links_in_total,
     hubs: [{hub_id,label,type,tier}],                                              // "Part of"
     see_also: [{id|null,label,score,books[],section_id,tier:"suggested"}],         // co-mention
     bodhi: [{bodhi_id,name,type,relation,tier}],
     atlas: {link: str|null, structures: [{label,atlas_name,url}]},
     graph: {nodes:[{id,label,type,center}], edges:[{source,target,predicate,tier}]}}  // 1 hop, <= 40 nodes

Tiers: `links_out` are `certified` (quote-checked facts); `links_in` are `derived` (the same fact read backwards;
`predicate` is the inverse wording, e.g. "treats"); `see_also` is `suggested`; sections, atlas and heading data are
`navigation`. Nothing but `certified` is a clinical claim. `atlas.link` is null when unlinked or `ATLAS_URL` is unset;
`structures` is `[]` unless the condition is local and atlas-linked. Graph edges point source -> target in the fact's
direction.

### GET /api/spatial/resolve ?fma= | ?label=
Unchanged: concept + atlas links + pointer citations + related concepts.

### POST /api/answers  ->  `{id}`
Body `{kind: "chat"|"why", question: str (<=3000), payload: object}`. Payload over 200 KB -> 413. `id` is a short
url-safe token (`secrets.token_urlsafe(6)`).
### GET /api/answers/{id}
`{id, kind, question, payload, created_at (unix seconds)}`, or 404 `{"detail": "Unknown answer"}`.

### POST /api/feedback  ->  `{ok: true}`
Body `{answer_id?: str, question?: str, kind: "wrong_citation"|"unhelpful"|"other", note?: str (<=1000)}`. Bad input -> 422.

### GET /api/health
`{status:"ok", llm_backend, atlas_enabled, ontology_loaded}`

### GET /api/features  (api/features.py)
`{diagram: bool, videos: bool, female_atlas: bool}`, read on every call from the JSON file `$FEATURES_FILE`
(default `var/features.json`; on the VM `~/v2-state/features.json`, mounted read-only into the container as a
directory, outside the `push.sh` rsync payload) with an mtime/size cache, so a flip needs no restart and no deploy:

    ssh <vm> 'jq ".videos=true" ~/v2-state/features.json > /tmp/f && mv /tmp/f ~/v2-state/features.json'

A missing, unreadable or non-object file means every flag is false; only a literal JSON `true` turns one on; unknown
keys are never returned. `push.sh` creates the file once with everything off and never overwrites it. Server-only key
`ratelimit` (default true; false = limiter off) is read by `api/ratelimit.py` and never returned here.
The web app reads the flags in the root layout (`apps/web/src/lib/features.ts`, `useFeature()`), never from the browser.

### POST /api/events  ->  204  (api/events.py)
Body `{name: <enum>, props?: {<key>: <value>}}`. Counts one anonymous event: SQLite `events(day, name, key, count)`,
UTC day, one row for the bare name (`key` empty) and one per prop (`kind=pathway`). No user id, IP, cookie, question,
topic or video id is stored. `name`, each props key and each value must come from the registry `EVENTS` in
`api/events.py`; anything else is 422 (so no free text). Rate limit 60/min per client IP (429 `rate_limited`).
`GET /api/events/summary?days=30` (1..366) -> `{days, rows: [{day, name, key, count}]}` with
`Authorization: Bearer $EVENTS_TOKEN`; 404 while `EVENTS_TOKEN` is unset, 401 on a wrong token (never read from the URL).

### Rate limiting and client IPs  (api/ratelimit.py)
`limit(name, per_minute)` is a FastAPI dependency: one in-process token bucket per (name, client IP), 429
`{"detail": "rate_limited"}` with `Retry-After`. `DailyCap(n)` is a global per-day counter for costly upstreams
(diagram LLM calls, YouTube searches). Client IP is `request.client.host`. In `deploy/v2/Dockerfile.api` uvicorn runs
with `--proxy-headers --forwarded-allow-ips 172.16.0.0/12,10.0.0.0/8,192.168.0.0/16`: `X-Forwarded-For` from Caddy is
trusted only from those private ranges, and uvicorn takes the right-most address outside them, so a client-supplied
header cannot choose its own bucket. Port 8000 is never published. Check after deploy that logged client IPs are real.

### POST /api/story/explore  (api/story.py)
"Try your own question" chapter of the /how scroll story. Places a visitor's question on the story map.
Body `{question: str}` (1..300 characters after trimming; blank or longer -> 422).

    {question, refused: bool, neighbours: [{i, sim, book}], best: float | null, min_similarity: float,
     passes_floor: bool, narration: str}

- `neighbours`: the 12 nearest passages. `i` is the passage's index in the story map (the order
  `scripts/build_library_map.py` writes, paging Chroma from offset 0). `sim` is cosine similarity (1 = identical);
  `book` is the textbook display name. No passage text is returned.
- `refused: true` is the personal-advice guard (`rag.answer._guard`), checked before any search: `neighbours` is `[]`,
  `best` is null, and `narration` is the fixed study-aid refusal.
- `passes_floor` is `best >= min_similarity` (`MIN_SIMILARITY`, default 0.60). Below it the story says the question
  was not found in the textbooks.
- `narration`: two short second-person sentences from `rag.backends.chat` (temperature 0.3, max 160 tokens), given a
  facts sheet (question, floor pass/fail, best similarity, floor, neighbours per book). Every number in the draft must
  appear in the facts; one retry, then a deterministic template built from the same facts. Any LLM exception also
  falls back to the template.
- Results are cached in-process (`lru_cache`, 256 entries) by the question with whitespace collapsed. The
  id-to-index map is built once, lazily, from Chroma.

## Storage
SQLite at `$APP_DB`, default `var/app.db` in the repo root (gitignored; never under the symlinked `data/`).
Tables `answers` and `feedback` are created on first use.

## Tests
`pytest -q tests/test_api.py tests/test_api_v2.py tests/test_api_features.py tests/test_api_events.py tests/test_ratelimit.py tests/test_safety_cues.py` (LLM and retrieval are mocked; the concept-page tests read the real
ontology and skip if it is missing).
