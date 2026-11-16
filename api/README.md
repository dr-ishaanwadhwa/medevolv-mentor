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
| `answer` | `{text, status, route, citations: AnswerCitation[], graph_citations: GraphCitation[], answer_sig: str \| null}` (chat only) |
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

`graph_citations` (additive) are pointers for the `[G#]` graph facts the text cites: `{n, fact_id, book, edition,
chapter, pages}`, parsed from the fact line's own "(Book, Chapter, pp. a-b)" cite; no fact text. `answer_sig` is
`HMAC-SHA256(DIAGRAM_SIG_SECRET, sha256(canonical_answer_bytes))` in hex, set only on `status == "answered"` and only
when `DIAGRAM_SIG_SECRET` is set (otherwise null, and the web Flowchart chip stays hidden). The client echoes the four
fields to `POST /api/diagram` unchanged; it never computes a signature (one implementation, `api/diagram.py`).

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

### GET /api/spatial/resolve ?fma= | ?label= [&sex=male|female]
Concept + atlas links + pointer citations + related concepts. Optional `sex` is the model the structure was tapped
in; with `sex=male`, female-only crosswalk rows are skipped. The response carries `sex` (`"male"` unless every record
is female-only), and each `atlas[]` link and chat `spatial` action carries `sex: "female"` only for female rows
(otherwise null). Female links add `&sex=female` (PRD R5 F-4).

### POST /api/answers  ->  `{id}`
Body `{kind: "chat"|"why", question: str (<=3000), payload: object}`. Payload over 200 KB -> 413. YouTube metadata
fields (`videos`, `video_id`, `thumbnail_url`, `watch_url`, ...) are stripped at any depth before saving: a chat share
keeps `topic` (and `related`, `diagram_id`), never video data (PRD V-12). `id` is a short
url-safe token (`secrets.token_urlsafe(6)`).
### GET /api/answers/{id}
`{id, kind, question, payload, created_at (unix seconds)}`, or 404 `{"detail": "Unknown answer"}`.

### POST /api/feedback  ->  `{ok: true}`
Body `{answer_id?: str, question?: str, kind: "wrong_citation"|"unhelpful"|"other"|"diagram_wrong"|"video_bad",
note?: str (<=1000), target_id?: str (<=32, the diagram_id or video_id)}`. Bad input -> 422.

### POST /api/diagram  (api/diagram.py, flag `diagram`)
Body `{question, answer_text (<=8000), citations: [{index, book, edition, chapter, pages, section_id}],
graph_citations: [{n, fact_id, book, edition, chapter, pages}], answer_sig, condition?}`: the fields of the `answer`
event, echoed. The server rebuilds the canonical bytes (NFC strings, `\n` line endings, documented keys only, extra keys
dropped) and checks `answer_sig`: mismatch -> 403 `bad_signature`; float or string `index`/`n`, or citations not
sorted -> 422; flag off -> 503 `diagram_unavailable`; over 10/min per client IP -> 429 `rate_limited`.

Response 200 (`version: 2`): `{status: "ok"|"declined", diagram_id, source: "ontology"|"answer"|null, kind, subject,
title, groups: [{id, title}], nodes: [{id, label, role, group, cites: [{kind: "passage"|"fact", n}]}],
edges: [{from, to, label, cites}], fact_sources: [{n, fact_id, book, edition, chapter, pages}], dropped, reason,
version}`. Paths: (1) the certified ontology graph (`rag.diagrams.build_graph`) when the question names a condition or
drug that the answer mentions with at least 3 of its fact labels; (2) else DeepSeek restructures the answer and
`api/diagram_validate.py` keeps only boxes and arrows the cited sentences support (V1-V6, E1-E5). Decline reasons:
`too_few_supported_nodes`, `patient_scoped`, `generator_error` (LLM failure or the 30 s budget; never cached, retry
may work), `budget` (global daily cap `DIAGRAM_DAILY_CAP`, default 300; never cached). Fact and quote text never
leave the server. Results are cached in `diagram_cache` under a hash (the raw question is not stored), 90-day TTL.

### GET /api/diagram/{diagram_id}
The stored `ok` response (shared pages; reading refreshes the TTL), 404 when missing or expired, 503 when the flag is off.

### POST /api/videos  (api/videos.py, flag `videos`)
Body `{topic: str (1..120), subject?: str}`; `topic` is the label from the `topic` event, never question text.
Response `{topic, videos: [{video_id, title, channel_title, channel_id, thumbnail_url, duration_seconds,
duration_label, view_count, watch_url, allowlisted, long_lecture}], fallback_url, fetched_at, source:
"cache"|"api"|"fallback", label}`. Keyless mode: without `YOUTUBE_API_KEY` the response is `source: "fallback"` with
no videos and the `youtube.com/results` link built from the topic label. With a key a cache miss makes exactly one
`search.list` (part=snippet, type=video, q="<topic> lecture MBBS", order=relevance, safeSearch=strict,
relevanceLanguage=en, regionCode=IN, maxResults=15) and one `videos.list`. Filters: 4 min to any length (over 90 min
flagged `long_lecture`), at least 5,000 views, clickbait titles, blocklist (`api/data/video_blocklist.json`).
Ranking: allowlisted channels (`api/data/video_channels.json`, team-verified, empty today) first, at most 4 cards and
at most 2 not allowlisted. Quota trouble (403), timeouts (3 s), any upstream error, or 80 searches in the last
rolling 24 h -> `source: "fallback"` with HTTP 200. Errors: 422 bad topic, 429 over 30/min per IP, 503 flag off.
Storage: `video_cache` (7-day refresh, rows older than 14 days purged on every write and at startup) and
`video_search_log` (timestamps only). YouTube data is stored nowhere else.

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
Tables `answers`, `feedback` (+ `target_id`, added in place), `events`, `diagram_cache`, `video_cache` and
`video_search_log` are created on first use.

## Tests
`pytest -q tests/test_api.py tests/test_api_v2.py tests/test_api_features.py tests/test_api_events.py tests/test_ratelimit.py tests/test_safety_cues.py tests/test_api_diagram.py tests/test_api_videos.py` (LLM, YouTube and retrieval are mocked; the concept-page tests read the real
ontology and skip if it is missing).
