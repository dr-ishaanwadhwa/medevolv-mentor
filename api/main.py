"""MedEvolv Mentor v2 gateway.   uvicorn api.main:app --port 8000

POST /api/chat/stream      SSE: step* -> answer -> spatial -> done   (error ends the stream)
GET  /api/spatial/resolve  ?fma=FMA... | ?label=Name   concept + atlas link(s) + pointer citations + related concepts
GET  /api/concepts/search  ?q=prefix
GET  /api/health

answer_multihop runs unchanged in a worker thread; its trace steps are forwarded live. Settings come from rag.config.
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from api import spatial
from api.schemas import (AnswerEvent, ChatRequest, ConceptHit, DoneEvent, ErrorEvent, HealthResponse,
                         SpatialEvent, SpatialResolveResponse, StepEvent)
from rag import atlas, concepts, config, ontology_facts, trace
from rag.answer import answer_multihop

app = FastAPI(title="MedEvolv Mentor API", version="2.0.0-m1")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])


def sse(event: str, model) -> str:
    return f"event: {event}\ndata: {model.model_dump_json()}\n\n"


def _step_event(s: trace.Step) -> StepEvent:
    return StepEvent(stage=s.stage, title=s.title, detail=s.detail, status=s.status, ms=round(s.ms, 1))


def _answer_event(a) -> AnswerEvent:
    cited = set(a.cited)
    route = getattr(a.plan, "route", None) or ("single" if a.status != "personal_refusal" else "refused")
    return AnswerEvent(text=a.text, status=a.status, route=route,
                       citations=[spatial.pointer_from_hit(i, h, i in cited) for i, h in enumerate(a.hits, 1)])


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
            yield sse("answer", _answer_event(payload))
            actions = await asyncio.to_thread(spatial.spatial_actions, payload, question)
            yield sse("spatial", SpatialEvent(actions=actions))
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


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(llm_backend=config.LLM_BACKEND, atlas_enabled=atlas.enabled(),
                          ontology_loaded=ontology_facts.available())
