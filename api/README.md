# MedEvolv Mentor API

`uvicorn api.main:app --port 8000` (run from the repo root; settings and `.env` come from `rag.config`).
CORS allows `http://localhost:3000` and `http://127.0.0.1:3000` only. No auth. Wire types live in `api/schemas.py`.

## SSE framing

Streaming endpoints return `text/event-stream`. Each message is exactly:

    event: <name>\ndata: <one-line JSON>\n\n

`POST` bodies are JSON, so use `fetch` + a stream reader (not `EventSource`).

### POST /api/chat/stream
Body `{question: str (1..2000)}`. Order: `step`* -> `answer` -> `spatial` -> `done`. `error` ends the stream early.

### POST /api/why/stream  ("Why was I wrong?")
Body `{question: str (1..3000), options: str[] (2..6), chosen: int}`; `chosen` indexes `options`
(out of range -> HTTP 422 before streaming). Order: `step`* -> `verdict` -> `done`. `error` ends the stream early.

### Events
| event | data |
|---|---|
| `step` | `{stage, title, detail, status: "ok"\|"warn"\|"stop", ms}` |
| `answer` | `{text, status, route, citations: AnswerCitation[]}` (chat only) |
| `spatial` | `{actions: [{action:"highlight", fma_ids, label, tier:"navigation"}]}` (chat only) |
| `verdict` | `VerdictEvent` (why only), below |
| `done` | `{ms}` |
| `error` | `{message, error_type}` (no internals leaked) |

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

## Storage
SQLite at `$APP_DB`, default `var/app.db` in the repo root (gitignored; never under the symlinked `data/`).
Tables `answers` and `feedback` are created on first use.

## Tests
`pytest -q tests/test_api.py tests/test_api_v2.py` (LLM and retrieval are mocked; the concept-page tests read the real
ontology and skip if it is missing).
