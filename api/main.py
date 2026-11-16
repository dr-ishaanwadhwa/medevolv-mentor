"""MedEvolv Mentor v2 gateway.   uvicorn api.main:app --port 8000

POST /api/chat/stream      SSE: step* -> answer -> spatial -> topic -> done   (error ends the stream)
POST /api/why/stream       SSE: step* -> verdict -> done             (error ends the stream)
GET  /api/concepts/{label_or_id}   concept page (404 JSON when unknown)
POST /api/answers, GET /api/answers/{id}   save / fetch a shared answer;  POST /api/feedback
GET  /api/spatial/resolve  ?fma=FMA... | ?label=Name   concept + atlas link(s) + pointer citations + related concepts
GET  /api/concepts/search  ?q=prefix
POST /api/diagram, GET /api/diagram/{id}   flowchart maker (flag `diagram`);  POST /api/videos   suggested videos (flag `videos`)
GET  /api/health;  GET /api/features (runtime flags);  POST /api/events + GET /api/events/summary (api/events.py)

answer_multihop runs unchanged in a worker thread; its trace steps are forwarded live. Settings come from rag.config.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api import concept_page, diagram, events, features, spatial, store, story, topic, videos, why
from api.safety_cues import patient_scoped
from api.schemas import (AnswerEvent, AnswerRecord, AnswerSave, AnswerSaved, ChatRequest, ConceptHit, ConceptPage, DoneEvent,
                         ErrorEvent, FeedbackOk, FeedbackRequest, HealthResponse, NotFound, SpatialEvent,
                         SpatialResolveResponse, StepEvent, TopicEvent, WhyRequest)
from rag import atlas, concepts, config, ontology_facts, trace
from rag.answer import answer_multihop

app = FastAPI(title="MedEvolv Mentor API", version="2.0.0-m1")


def _warm() -> None:
    """Load the clinical graph, embedder and vector index once, off the request path (the first question after a
    restart otherwise waits ~25 s). Best effort: a failure here only means the first request pays the cost."""
    import os
    if os.getenv("API_WARMUP", "1") != "1":
        return
    try:
        from rag import graph, retrieve
        graph.link_entities("pheochromocytoma with headache")
        retrieve.search("pheochromocytoma preoperative alpha blockade", k=2)
        concepts.search_concepts("pheo", limit=1)
    except Exception:
        pass


@app.on_event("startup")
def _startup_warm() -> None:
    import threading
    threading.Thread(target=_warm, daemon=True, name="warmup").start()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


def sse(event: str, model) -> str:
    return f"event: {event}\ndata: {model.model_dump_json()}\n\n"


def _step_event(s: trace.Step) -> StepEvent:
    return StepEvent(stage=s.stage, title=s.title, detail=s.detail, status=s.status, ms=round(s.ms, 1))


def _answer_event(a, question: str = "") -> AnswerEvent:
    cited = set(a.cited)
    route = getattr(a.plan, "route", None) or ("single" if a.status != "personal_refusal" else "refused")
    cits = [spatial.pointer_from_hit(i, h, i in cited) for i, h in enumerate(a.hits, 1)]
    gfacts = getattr(a.plan, "graph_facts", None) or []
    gcits = diagram.graph_citation_pointers(gfacts, getattr(a, "graph_cited", None) or []) if a.status == "answered" else []
    sig = None
    if a.status == "answered" and not patient_scoped(question):   # only these may offer a flowchart (D-1, D-16)
        try:
            sig = diagram.sign_answer(question, a.text, [c.model_dump() for c in cits], gcits)
        except Exception:                           # noqa: BLE001 - a signing problem only means no Flowchart chip
            sig = None
    return AnswerEvent(text=a.text, status=a.status, route=route, citations=cits, graph_citations=gcits, answer_sig=sig)


async def chat_events(question: str):
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()
    t0 = time.perf_counter()

    def put(kind, payload):
        loop.call_soon_threadsafe(q.put_nowait, (kind, payload))

    def work():
        trace.start(lambda s: put("step", s))      # trace is a ContextVar: start it in the worker thread
        try:
            put("result", answer_multihop(question))
        except Exception as e:                      # noqa: BLE001 - reported to the client as event: error
            put("error", e)
        finally:
            trace.stop()

    fut = loop.run_in_executor(None, work)
    try:
        while True:
            kind, payload = await q.get()
            if kind == "step":
                yield sse("step", _step_event(payload))
            elif kind == "error":
                yield sse("error", ErrorEvent(message="The question could not be answered.", error_type=type(payload).__name__))
                return
            else:
                break
        try:
            yield sse("answer", _answer_event(payload, question))
            actions = await asyncio.to_thread(spatial.spatial_actions, payload, question)
            yield sse("spatial", SpatialEvent(actions=actions))
            try:                                    # best effort: no topic must never fail an answer that already streamed
                t_ev = await asyncio.to_thread(topic.topic_event, question, payload, actions)
            except Exception:                       # noqa: BLE001
                t_ev = TopicEvent()
            yield sse("topic", t_ev)
        except Exception as e:                      # noqa: BLE001
            yield sse("error", ErrorEvent(message="The answer could not be assembled.", error_type=type(e).__name__))
            return
        yield sse("done", DoneEvent(ms=round((time.perf_counter() - t0) * 1000, 1)))
    finally:
        await asyncio.shield(fut)


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    return StreamingResponse(chat_events(req.question), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def why_events(req: WhyRequest):
    loop = asyncio.get_running_loop()
    q: asyncio.Queue = asyncio.Queue()
    t0 = time.perf_counter()

    def put(kind, payload):
        loop.call_soon_threadsafe(q.put_nowait, (kind, payload))

    def work():
        trace.start(lambda s: put("step", s))
        try:
            put("result", why.run(req))
        except Exception as e:                      # noqa: BLE001 - reported to the client as event: error
            put("error", e)
        finally:
            trace.stop()

    fut = loop.run_in_executor(None, work)
    try:
        while True:
            kind, payload = await q.get()
            if kind == "step":
                yield sse("step", _step_event(payload))
            elif kind == "error":
                yield sse("error", ErrorEvent(message="The question could not be judged.", error_type=type(payload).__name__))
                return
            else:
                break
        yield sse("verdict", payload)
        yield sse("done", DoneEvent(ms=round((time.perf_counter() - t0) * 1000, 1)))
    finally:
        await asyncio.shield(fut)


@app.post("/api/why/stream")
async def why_stream(req: WhyRequest):
    if req.chosen >= len(req.options):
        raise HTTPException(422, "chosen must be an index into options")
    return StreamingResponse(why_events(req), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/spatial/resolve", response_model=SpatialResolveResponse)
async def spatial_resolve(fma: str | None = Query(None, min_length=1), label: str | None = Query(None, min_length=1)):
    if bool(fma) == bool(label):
        raise HTTPException(422, "Pass exactly one of ?fma= or ?label=")
    r = await asyncio.to_thread(spatial.resolve, fma, label)
    if r is None:
        raise HTTPException(404, "Unknown structure")
    return SpatialResolveResponse(query={"fma": fma} if fma else {"label": label}, **r)


@app.get("/api/concepts/search", response_model=list[ConceptHit])
async def concepts_search(q: str = Query("", max_length=100), limit: int = Query(20, ge=1, le=50)):
    return await asyncio.to_thread(concepts.search_concepts, q, limit)


@app.get("/api/concepts/{label_or_id:path}", response_model=ConceptPage, responses={404: {"model": NotFound}})
async def concept_get(label_or_id: str):
    page = await asyncio.to_thread(concept_page.build, label_or_id)
    if page is None:
        raise HTTPException(404, "Unknown concept")
    return page


@app.post("/api/answers", response_model=AnswerSaved)
async def answers_save(req: AnswerSave):
    try:
        payload = videos.strip_youtube(req.payload)          # a share keeps the topic, never YouTube data (V-12)
        return AnswerSaved(id=await asyncio.to_thread(store.save_answer, req.kind, req.question, payload))
    except store.PayloadTooLarge as e:
        raise HTTPException(413, str(e))


@app.get("/api/answers/{answer_id}", response_model=AnswerRecord, responses={404: {"model": NotFound}})
async def answers_get(answer_id: str):
    rec = await asyncio.to_thread(store.get_answer, answer_id)
    if rec is None:
        raise HTTPException(404, "Unknown answer")
    return rec


@app.post("/api/feedback", response_model=FeedbackOk)
async def feedback(req: FeedbackRequest):
    await asyncio.to_thread(store.add_feedback, req.answer_id, req.question, req.kind, req.note, req.target_id)
    return FeedbackOk()


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(llm_backend=config.LLM_BACKEND, atlas_enabled=atlas.enabled(),
                          ontology_loaded=ontology_facts.available())


app.include_router(features.router)   # GET /api/features (api/features.py)
app.include_router(events.router)     # POST /api/events, GET /api/events/summary (api/events.py)
app.include_router(diagram.router)    # POST /api/diagram, GET /api/diagram/{id} (api/diagram.py)
app.include_router(videos.router)     # POST /api/videos (api/videos.py)
app.include_router(story.router)     # POST /api/story/explore (api/story.py)
