"""Flowchart maker (PRD 4.1): POST /api/diagram, GET /api/diagram/{diagram_id}.

Two grounded paths, one JSON graph (version 2):
  1. CERTIFIED: the question names an ontology condition or drug, the answer mentions it and at least 3 of its fact
     labels  ->  rag.diagrams.build_graph (facts only; headings are groups, never nodes).
  2. ANSWER: DeepSeek restructures the already-cited answer into a graph; api.diagram_validate drops every box and
     arrow the answer does not support (V1-V6, E1-E5). Nothing partial: it draws a valid graph or declines.

Authenticity (D-12): the chat stream signs each answer (`answer_sig`, HMAC-SHA256 over a canonical form the SERVER
builds); /api/diagram recomputes it, so only answers Mentor itself produced are restructured. The secret is
DIAGRAM_SIG_SECRET (server .env only). Without it no answer is signed and the web chip never appears.

Results (ok and deterministic declines, never generator errors) are cached in `diagram_cache` in $APP_DB under a hash
of VERSION | ontology mtime | question | answer | citations: the raw question is never stored. 90-day TTL, refreshed
when a shared page reads the row. The LLM runs on its own 2-thread executor so chat keeps the default pool.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from api import events, features, store
from api.diagram_validate import KINDS, SchemaError, markers_in, sentences, strip_numbers_of_dose, validate
from api.ratelimit import DailyCap, limit
from api.safety_cues import patient_scoped
from rag import diagrams, ontology_facts as onto
from rag.backends import chat

VERSION = 2                                     # response shape version (PRD 4.1)
TTL_DAYS = 90
TOTAL_BUDGET_S = 30.0                           # D-13: the whole endpoint, LLM retry included
DAILY_CAP = int(os.getenv("DIAGRAM_DAILY_CAP", "300"))   # D-14: a budget we set, not a provider limit
MIN_CITED_SENTENCES = 3

router = APIRouter()
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="diagram")
_cap = DailyCap(DAILY_CAP)


# ---------------------------------------------------------------- signing (single implementation: sign + check)

def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s).replace("\r\n", "\n").replace("\r", "\n")


def _opt(v) -> str | None:
    return None if v is None else _nfc(str(v))


def canonical_answer_bytes(question: str, answer_text: str, citations: list[dict], graph_citations: list[dict]) -> bytes:
    """PRD D-12: documented keys only, missing optional keys null, NFC strings, \\n line endings, list order kept,
    integers only for index and n, sort_keys + compact separators, UTF-8."""
    cs = [{"index": c["index"], "book": _nfc(c["book"]), "edition": _opt(c.get("edition")), "chapter": _opt(c.get("chapter")),
           "pages": _opt(c.get("pages")), "section_id": _opt(c.get("section_id"))} for c in citations]
    gs = [{"n": g["n"], "fact_id": _nfc(g["fact_id"]), "book": _nfc(g["book"]), "edition": _opt(g.get("edition")),
           "chapter": _opt(g.get("chapter")), "pages": _opt(g.get("pages"))} for g in graph_citations]
    obj = {"q": _nfc(question), "a": _nfc(answer_text), "c": cs, "g": gs}
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _secret() -> bytes | None:
    s = os.getenv("DIAGRAM_SIG_SECRET", "")
    return s.encode("utf-8") if s else None


def sign_answer(question: str, answer_text: str, citations: list[dict], graph_citations: list[dict]) -> str | None:
    """Hex HMAC-SHA256(secret, sha256(canonical bytes)); None when no secret is configured."""
    key = _secret()
    if key is None:
        return None
    digest = hashlib.sha256(canonical_answer_bytes(question, answer_text, citations, graph_citations)).digest()
    return hmac.new(key, digest, hashlib.sha256).hexdigest()


def verify_answer(sig: str, question: str, answer_text: str, citations: list[dict], graph_citations: list[dict]) -> bool:
    want = sign_answer(question, answer_text, citations, graph_citations)
    return want is not None and hmac.compare_digest(want, sig or "")


# ---------------------------------------------------------------- [G#] pointers for the answer event

_CITE_RE = re.compile(r"\(((?:[^()]|\([^()]*\))+?),\s*(pp?\.\s*\d+(?:\s*[–-]\s*\d+)?)\)")


def graph_citation_pointers(graph_facts: list[str], graph_cited: list[int]) -> list[dict]:
    """Pointers (book, chapter, pages) for the [G#] graph facts an answer cites. The answer pipeline keeps graph facts
    as text lines, not fact ids, so the pointer is parsed from the line's own "(Book, Chapter, pp. a-b)" cite and
    `fact_id` is a stable id derived from the line. A line that cites several books lists the books and leaves
    chapter and pages empty rather than pairing them wrongly. Lines with no cite (the BODHI graph) name the graph."""
    out = []
    for n in sorted(set(graph_cited)):
        if not 1 <= n <= len(graph_facts):
            continue
        line = graph_facts[n - 1]
        cites = []
        for m in _CITE_RE.finditer(line):
            parts = [p.strip() for p in m.group(1).split(", ")]
            cites.append((parts[0], ", ".join(parts[1:]), m.group(2).replace("pp.", "").replace("p.", "").strip()))
        cites = list(dict.fromkeys(cites))
        books = list(dict.fromkeys(c[0] for c in cites))
        if len(cites) == 1:
            book, chapter, pages = cites[0]
        elif cites:
            book, chapter, pages = "; ".join(books), "", ""
        else:
            book, chapter, pages = "Clinical knowledge graph", "", ""
        out.append({"n": n, "fact_id": f"g-{hashlib.sha1(line.encode('utf-8')).hexdigest()[:10]}", "book": book,
                    "edition": "", "chapter": chapter, "pages": pages})
    return out


# ---------------------------------------------------------------- request models

class CitationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")          # the client echoes the whole answer event: extra keys are dropped
    index: StrictInt
    book: str
    edition: str | None = None
    chapter: str | None = None
    pages: str | None = None
    section_id: str | None = None


class GraphCitationIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    n: StrictInt
    fact_id: str
    book: str
    edition: str | None = None
    chapter: str | None = None
    pages: str | None = None


class DiagramRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    answer_text: str = Field(min_length=1, max_length=8000)
    citations: list[CitationIn] = Field(default_factory=list, max_length=60)
    graph_citations: list[GraphCitationIn] = Field(default_factory=list, max_length=60)
    answer_sig: str = Field(min_length=1, max_length=128)
    condition: str | None = Field(default=None, max_length=200)


# ---------------------------------------------------------------- storage: diagram_cache

_SCHEMA = ("CREATE TABLE IF NOT EXISTS diagram_cache (key TEXT PRIMARY KEY, id TEXT UNIQUE, json TEXT NOT NULL, "
           "created_at REAL NOT NULL);")


def _conn() -> sqlite3.Connection:
    p = store.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute(_SCHEMA)
    return con


def _purge(con: sqlite3.Connection) -> None:
    con.execute("DELETE FROM diagram_cache WHERE created_at < ?", (time.time() - TTL_DAYS * 86400,))


def cache_key(question: str, answer_text: str, citations: list[dict], graph_citations: list[dict]) -> str:
    stamp = onto.PATH.stat().st_mtime_ns if onto.PATH.exists() else 0
    blob = [VERSION, diagrams.VERSION, stamp, hashlib.sha256(canonical_answer_bytes(question, answer_text, citations,
                                                                                 graph_citations)).hexdigest()]
    return hashlib.sha256(json.dumps(blob).encode()).hexdigest()


def _cache_get(key: str) -> dict | None:
    con = _conn()
    try:
        row = con.execute("SELECT json FROM diagram_cache WHERE key=? AND created_at >= ?",
                          (key, time.time() - TTL_DAYS * 86400)).fetchone()
    finally:
        con.close()
    return json.loads(row[0]) if row else None


def _cache_put(key: str, resp: dict) -> None:
    con = _conn()
    try:
        with con:
            _purge(con)
            con.execute("INSERT OR REPLACE INTO diagram_cache (key, id, json, created_at) VALUES (?,?,?,?)",
                        (key, resp.get("diagram_id"), json.dumps(resp, ensure_ascii=False), time.time()))
    finally:
        con.close()


def _new_id() -> str:
    con = _conn()
    try:
        while True:
            i = secrets.token_urlsafe(6)
            if con.execute("SELECT 1 FROM diagram_cache WHERE id=?", (i,)).fetchone() is None:
                return i
    finally:
        con.close()


def get_stored(diagram_id: str) -> dict | None:
    """A stored ok diagram, or None when missing or expired. Reading it refreshes its TTL (a shared diagram that is
    still being opened stays alive)."""
    con = _conn()
    try:
        with con:
            row = con.execute("SELECT json FROM diagram_cache WHERE id=? AND created_at >= ?",
                              (diagram_id, time.time() - TTL_DAYS * 86400)).fetchone()
            if row:
                con.execute("UPDATE diagram_cache SET created_at=? WHERE id=?", (time.time(), diagram_id))
    finally:
        con.close()
    return json.loads(row[0]) if row else None


# ---------------------------------------------------------------- building the response

def _declined(reason: str) -> dict:
    return {"status": "declined", "diagram_id": None, "source": None, "kind": None, "subject": None, "title": None,
            "groups": [], "nodes": [], "edges": [], "fact_sources": [], "dropped": 0, "reason": reason, "version": VERSION}


def _ok(source: str, kind: str, subject: str | None, title: str | None, groups: list, nodes: list, edges: list,
        fact_sources: list, dropped: int) -> dict:
    return {"status": "ok", "diagram_id": None, "source": source, "kind": kind, "subject": subject, "title": title,
            "groups": groups, "nodes": nodes, "edges": edges, "fact_sources": fact_sources, "dropped": dropped,
            "reason": None, "version": VERSION}


def ontology_response(ont: dict) -> dict | None:
    """rag.diagrams.build_graph output -> the wire shape. Drops `fact` and `quote` text (pointer-only rule, D-10) and
    dose/duration numbers from labels; None when fewer than 3 boxes remain."""
    keep, nodes = set(), []
    for n in ont["nodes"]:
        label = strip_numbers_of_dose(n["label"])
        if label:
            keep.add(n["id"])
            nodes.append({**n, "label": label[:80]})
    edges = [e for e in ont["edges"] if e["from"] in keep and e["to"] in keep]
    if len(nodes) < 3:
        return None
    used = {n["group"] for n in nodes if n["group"]}
    groups = [{"id": g["id"], "title": g["title"]} for g in ont["groups"] if g["id"] in used]
    srcs = [{"n": s["n"], "fact_id": s["fact_id"], **s["prov"]} for s in ont["facts"]]
    return _ok("ontology", ont["kind"], ont["subject"], ont["title"], groups, nodes, edges, srcs, 0)


SYSTEM = """You restructure ONE cited answer into a flowchart, as JSON. Rules:
- Restructure ONLY the given answer. Do not add facts, steps, boxes or arrows the answer does not state.
- Choose one kind: "classification" (types and subtypes), "pathway" (courses, branches, supply, drainage) or "sequence"
  (mechanism, pathogenesis, cascade, workup, treatment steps).
- Every node and every edge must list in "cites" the markers (for example "1" for [1], "G1" for [G1]) that appear in the
  answer sentence it came from. Use only markers that appear in the answer.
- Node labels are short (at most 80 characters), made of words from the answer. No doses, durations or frequencies.
- Edge "label" is one of the allowed verbs for the kind, or "". Arrows follow the order the answer states.
- At most the node limit for the kind. The graph must be connected. No self-loops.
Output JSON: {"kind": "...", "title": "...", "nodes": [{"id": "n1", "label": "...", "role": "start|step|branch|end|warning",
"cites": ["1"]}], "edges": [{"from": "n1", "to": "n2", "label": "", "cites": ["1"]}]}"""


def _user_prompt(answer_text: str, passage_ns: set[int], fact_ns: set[int], err: str | None) -> str:
    limits = "; ".join(f"{k}: at most {cap} nodes, verbs {list(v)}" for k, (cap, v) in KINDS.items())
    markers = ", ".join([str(n) for n in sorted(passage_ns)] + [f"G{n}" for n in sorted(fact_ns)]) or "(none)"
    out = f"Limits per kind: {limits}\nMarkers you may cite: {markers}\n\nAnswer:\n{answer_text}\n"
    if err:
        out += f"\nYour previous reply was rejected: {err} Fix it and reply with the JSON object only."
    return out


def _extract_json(raw: str):
    s = (raw or "").strip()
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", s)
    try:
        return json.loads(s)
    except ValueError:
        m = re.search(r"\{.*\}", s, re.S)
        if not m:
            raise SchemaError("The reply was not valid JSON.")
        try:
            return json.loads(m.group(0))
        except ValueError:
            raise SchemaError("The reply was not valid JSON.")


def answer_path(answer_text: str, passage_ns: set[int], fact_ns: set[int], graph_pointers: list[dict]) -> dict:
    """Blocking (runs on the diagram executor): one LLM call, one retry on a malformed reply, then the validator."""
    err = None
    for _ in range(2):
        try:
            raw = chat(SYSTEM, _user_prompt(answer_text, passage_ns, fact_ns, err), temperature=0, max_tokens=1000,
                       json_mode=True, purpose="Flowchart from a cited answer")
            res = validate(_extract_json(raw), answer_text=answer_text, passage_ns=passage_ns, fact_ns=fact_ns)
        except SchemaError as e:
            err = str(e)
            continue
        if not res.ok:
            return _declined(res.reason or "too_few_supported_nodes")
        g = res.graph
        srcs = [{k: p[k] for k in ("n", "fact_id", "book", "edition", "chapter", "pages")}
                for p in graph_pointers if p["n"] in res.fact_ns]
        return _ok("answer", g["kind"], None, g["title"], [], g["nodes"], g["edges"], srcs, res.dropped)
    return _declined("generator_error")


# ---------------------------------------------------------------- endpoints

def _event(name: str, props: dict | None = None) -> None:
    try:
        events.record(name, props)
    except Exception:                                       # noqa: BLE001 - counters never break the request
        pass


@router.post("/api/diagram", dependencies=[Depends(limit("diagram", per_minute=10))])
async def make_diagram(req: DiagramRequest):
    if not features.flag("diagram"):
        raise HTTPException(503, "diagram_unavailable")
    cits = [c.model_dump() for c in req.citations]
    gcits = [g.model_dump() for g in req.graph_citations]
    if [c["index"] for c in cits] != sorted(c["index"] for c in cits) or [g["n"] for g in gcits] != sorted(g["n"] for g in gcits):
        raise HTTPException(422, "citations must be sorted by index")
    if not verify_answer(req.answer_sig, req.question, req.answer_text, cits, gcits):
        _event("diagram_sig_fail")
        raise HTTPException(403, "bad_signature")
    _event("diagram_request")
    if patient_scoped(req.question):
        return JSONResponse(_declined("patient_scoped"))

    key = cache_key(req.question, req.answer_text, cits, gcits)
    hit = await asyncio.to_thread(_cache_get, key)
    if hit is not None:
        if hit["status"] == "ok":
            _event("diagram_ok", {"kind": hit["kind"]})
        return JSONResponse(hit)

    # 1. certified path
    ont = await asyncio.to_thread(diagrams.build_graph, req.question, req.answer_text, req.condition)
    resp = ontology_response(ont) if ont else None
    if resp is None:
        # 2. answer path: needs 3 sentences that carry a marker the answer really has
        passage_ns, fact_ns = {c["index"] for c in cits}, {g["n"] for g in gcits}
        allowed = {("passage", n) for n in passage_ns} | {("fact", n) for n in fact_ns}
        n_cited = sum(1 for s in sentences(req.answer_text) if markers_in(s) & allowed)
        if n_cited < MIN_CITED_SENTENCES:
            resp = _declined("too_few_supported_nodes")
        elif not _cap.take():
            return JSONResponse(_declined("budget"))                   # not cached: tomorrow it may work
        else:
            loop = asyncio.get_running_loop()
            try:
                resp = await asyncio.wait_for(
                    loop.run_in_executor(_executor, answer_path, req.answer_text, passage_ns, fact_ns, gcits),
                    timeout=TOTAL_BUDGET_S)
            except (asyncio.TimeoutError, Exception):                  # noqa: BLE001 - LLM trouble is a decline, never a 5xx
                resp = _declined("generator_error")
    if resp["reason"] == "generator_error":
        return JSONResponse(resp)                                      # never cached, so a retry can succeed
    if resp["status"] == "ok":
        resp["diagram_id"] = await asyncio.to_thread(_new_id)
        _event("diagram_ok", {"kind": resp["kind"]})
    await asyncio.to_thread(_cache_put, key, resp)
    return JSONResponse(resp)


@router.get("/api/diagram/{diagram_id}")
async def get_diagram(diagram_id: str):
    if not features.flag("diagram"):
        raise HTTPException(503, "diagram_unavailable")
    stored = await asyncio.to_thread(get_stored, diagram_id[:32])
    if stored is None:
        raise HTTPException(404, "Unknown diagram")
    return JSONResponse(stored)
