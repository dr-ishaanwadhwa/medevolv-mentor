"""API contract tests: stubbed answer_multihop, atlas and concepts; no data, no LLM."""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from api import main, spatial
from api.schemas import (EXCERPT_FIELD_MAX, AnswerEvent, DoneEvent, ErrorEvent, SpatialEvent,
                         SpatialResolveResponse, StepEvent)
from rag import answer as answer_mod, atlas, concepts, config, graph, mentions, ontology_facts as onto, trace
from rag.retrieve import Hit

LONG = "SECRET-TEXTBOOK-PROSE " * 100          # 2200 chars: must never leave beyond 300 + ellipsis
RCA = {"label": "Right coronary artery", "key": "right coronary artery", "atlas_id": "FMA50050",
       "atlas_name": "right coronary artery", "method": "exact", "score": 1.0}
HEART = {"label": "Heart", "key": "heart", "atlas_id": "FMA7088", "atlas_name": "heart", "method": "exact", "score": 1.0}
CONCEPT = {"id": "C:rca", "label": "Right coronary artery", "type": "AnatomicalStructure", "aliases": [], "degree": 3,
           "books": ["grays"], "sections": ["grays/s1"], "outgoing": {}, "backlinks": {}, "same_label": []}


def hit(i, book_id="grays", section="grays/s1"):
    return Hit(id=f"{section}#p00{i}", passage=LONG,
               meta={"book": "Gray's Anatomy", "book_id": book_id, "chapter": "Heart", "pages": "10-12",
                     "section_id": section, "section_title": "Heart", "section_path": "Gray's Anatomy › Heart › Heart",
                     "heading": ""}, similarity=0.8)


def stub_answer(question):
    trace.record("guard", "Personal-advice check", "continue")
    trace.record("route", "Routing", "graph route", ms=3.0)
    return answer_mod.Answer("Inferior MI involves the RCA [1].", hits=[hit(1), hit(2, "robbins", "robbins/s9")], cited=[1],
                             plan=SimpleNamespace(route="graph", conditions=["Inferior myocardial infarction"]))


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(main, "answer_multihop", stub_answer)
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(atlas, "links", lambda: {"right coronary artery": RCA, "heart": HEART,
                                                 "~heart": HEART, "~rightcoronaryartery": RCA})
    monkeypatch.setattr(atlas, "structures_for", lambda c: [{"label": "Right coronary artery", "atlas_name": "x", "url": "u"}]
                        if c == "Inferior myocardial infarction" else [])
    monkeypatch.setattr(spatial, "section_concept_labels", lambda sid: ["Heart", "Not in atlas"] if sid == "grays/s1" else [])
    monkeypatch.setattr(concepts, "concept", lambda n: CONCEPT if n.lower() == "right coronary artery" else {})
    monkeypatch.setattr(concepts, "related", lambda n, k=10: [
        {"id": "C:mi", "label": "Inferior MI", "type": "PathologicalCondition", "shared_facts": 2, "n_books": 1,
         "predicates": ["INVOLVES_STRUCTURE"], "tier": "derived"}])
    monkeypatch.setattr(concepts, "search_concepts", lambda q, limit=20: [
        {"id": "C:rca", "label": "Right coronary artery", "type": "AnatomicalStructure", "degree": 3}][:limit])
    monkeypatch.setattr(onto, "facts", lambda: ({"subject_id": "C:mi", "object_id": "C:rca",
                        "provenance": {"book_id": "grays", "section_id": "grays/s1", "chapter": "3. Heart", "pages": [10, 12],
                                       "book_title": "Gray's Anatomy"}},))
    monkeypatch.setattr(mentions, "sections_for", lambda label, k=5: [
        {"section_id": "robbins/s9", "book_id": "robbins", "title": "MI", "path": "Robbins › Heart › MI"}])
    monkeypatch.setattr(atlas, "enabled", lambda: True)
    return TestClient(main.app)


def parse_sse(body: str):
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(l.split(": ", 1) for l in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def stream(client, q="Inferior MI?"):
    r = client.post("/api/chat/stream", json={"question": q})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def test_event_order_and_schemas(client):
    ev = stream(client)
    assert [e for e, _ in ev] == ["step", "step", "answer", "spatial", "done"]
    StepEvent.model_validate(ev[0][1])
    assert ev[1][1]["stage"] == "route" and ev[1][1]["ms"] == 3.0
    ans = AnswerEvent.model_validate(ev[2][1])
    assert (ans.status, ans.route) == ("answered", "graph")
    assert [c.cited for c in ans.citations] == [True, False]
    SpatialEvent.model_validate(ev[3][1])
    DoneEvent.model_validate(ev[4][1])
    print("\n".join(f"event: {e}\ndata: {json.dumps(d)[:160]}\n" for e, d in ev))


def test_citations_are_pointers_with_capped_excerpt(client):
    ans = stream(client)[2][1]
    for c in ans["citations"]:
        assert set(c) == {"index", "cited", "book", "edition", "chapter", "pages", "section_id", "excerpt"}
        assert len(c["excerpt"]) <= EXCERPT_FIELD_MAX and c["excerpt"].endswith("…")
    assert ans["citations"][0]["section_id"] == "grays/s1" and ans["citations"][0]["pages"] == "10-12"
    assert LONG not in json.dumps(ans)


def test_spatial_only_atlas_linked_ids(client):
    acts = stream(client)[3][1]["actions"]
    assert {a["label"] for a in acts} == {"Right coronary artery", "Heart"}      # "Not in atlas" never appears
    allowed = {RCA["atlas_id"], HEART["atlas_id"]}
    for a in acts:
        assert a["action"] == "highlight" and a["tier"] == "navigation" and set(a["fma_ids"]) <= allowed
    assert len({tuple(a["fma_ids"]) for a in acts}) == len(acts)                 # deduplicated


def test_spatial_empty_when_nothing_links(client, monkeypatch):
    monkeypatch.setattr(atlas, "links", lambda: {})
    monkeypatch.setattr(atlas, "structures_for", lambda c: [])
    assert stream(client)[3] == ("spatial", {"actions": []})


def test_errors_stream_as_error_event(client, monkeypatch):
    def boom(q):
        trace.record("guard", "Safety check")
        raise RuntimeError("secret internal detail")
    monkeypatch.setattr(main, "answer_multihop", boom)
    ev = stream(client)
    assert [e for e, _ in ev] == ["step", "error"]
    ErrorEvent.model_validate(ev[1][1])
    assert ev[1][1]["error_type"] == "RuntimeError" and "secret" not in json.dumps(ev[1][1])


def test_error_while_deriving_spatial(client, monkeypatch):
    monkeypatch.setattr(spatial, "spatial_actions", lambda *a: (_ for _ in ()).throw(ValueError("x")))
    assert [e for e, _ in stream(client)][-1] == "error"


def test_bad_request(client):
    assert client.post("/api/chat/stream", json={"question": ""}).status_code == 422


def test_resolve_by_fma(client):
    r = client.get("/api/spatial/resolve", params={"fma": "FMA50050"})
    assert r.status_code == 200
    body = SpatialResolveResponse.model_validate(r.json())
    assert body.fma_ids == ["FMA50050"] and body.concept.id == "C:rca"
    assert body.atlas[0].url == "https://atlas.example/?select=FMA50050"
    assert {c.section_id for c in body.citations} == {"grays/s1", "robbins/s9"}
    assert body.related[0].label == "Inferior MI"
    assert all(c.excerpt is None for c in body.citations)


def test_resolve_by_label_and_errors(client):
    assert client.get("/api/spatial/resolve", params={"label": "right coronary artery"}).json()["fma_ids"] == ["FMA50050"]
    assert client.get("/api/spatial/resolve", params={"fma": "FMA1"}).status_code == 404
    assert client.get("/api/spatial/resolve").status_code == 422
    assert client.get("/api/spatial/resolve", params={"fma": "a", "label": "b"}).status_code == 422


def test_concepts_search_health_cors(client):
    assert client.get("/api/concepts/search", params={"q": "right"}).json()[0]["id"] == "C:rca"
    assert client.get("/api/health").json()["status"] == "ok"
    r = client.options("/api/chat/stream", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_resolve_survives_broken_mention_index(client, monkeypatch):
    def broken(label, k=5):
        raise ValueError("index format skew")
    monkeypatch.setattr(mentions, "sections_for", broken)
    r = client.get("/api/spatial/resolve", params={"fma": "FMA50050"})
    assert r.status_code == 200 and [c["section_id"] for c in r.json()["citations"]] == ["grays/s1"]


CHIASM = {"label": "Optic chiasm", "key": "optic chiasm", "atlas_id": "FMA62045", "atlas_name": "optic chiasm",
          "method": "exact", "score": 1.0}


@pytest.fixture
def fallback(client, monkeypatch):
    """No plan conditions, no Gray's citation: only the question/answer text can produce actions."""
    def ans(q):
        return answer_mod.Answer("Compression of the optic chiasm by a pituitary tumour [1]. Also SLE.", hits=[hit(1, "robbins", "robbins/s9")],
                                 cited=[1], plan=SimpleNamespace(route="single", conditions=[]))
    monkeypatch.setattr(main, "answer_multihop", ans)
    monkeypatch.setattr(spatial, "section_concept_labels", lambda sid: [])
    monkeypatch.setattr(atlas, "links", lambda: {"optic chiasm": CHIASM, "heart": HEART, "right coronary artery": RCA})
    nodes = {"optic chiasm": {"label": "Optic chiasm", "type": "AnatomicalStructure"},
             "pituitary macroadenoma": {"label": "Pituitary macroadenoma", "type": "PathologicalCondition"},
             "systemic lupus erythematosus": {"label": "Systemic lupus erythematosus", "type": "PathologicalCondition"}}
    monkeypatch.setattr(concepts, "concept", lambda n: nodes.get(n.lower(), {}))
    monkeypatch.setattr(concepts, "search_concepts", lambda q, limit=20: [])
    monkeypatch.setattr(graph, "link_entities", lambda q: [{"name": "Bitemporal hemianopia", "type": "Symptom"}])
    monkeypatch.setattr(onto, "match_conditions", lambda n: [n])
    monkeypatch.setattr(atlas, "structures_for", lambda c: [{"label": "Optic chiasm", "atlas_name": "x", "url": "u"}]
                        if c == "Pituitary macroadenoma" else [])
    return client


def test_fallback_structure_named_in_answer_and_condition_in_question(fallback):
    acts = stream(fallback, "Pituitary macroadenoma with bitemporal hemianopia. Why?")[1][1]["actions"]
    assert [a["fma_ids"] for a in acts] == [["FMA62045"]]               # chiasm found twice, emitted once
    assert acts[0]["tier"] == "navigation"


def test_fallback_systemic_condition_gets_no_highlight(fallback):
    acts = stream(fallback, "Systemic lupus erythematosus features?")[1][1]["actions"]
    assert all(a["label"] != "Systemic lupus erythematosus" for a in acts)
    assert [a["fma_ids"] for a in acts] == [["FMA62045"]]               # only the chiasm named in the answer text


def test_fallback_runs_after_plan_and_caps_at_five(fallback, monkeypatch):
    many = {f"s{i}": {"label": f"S{i}", "key": f"s{i}", "atlas_id": f"FMA{i}", "atlas_name": f"s{i}"} for i in range(9)}
    monkeypatch.setattr(atlas, "links", lambda: {**many, "optic chiasm": CHIASM})
    monkeypatch.setattr(atlas, "structures_for", lambda c: [{"label": f"S{i}", "atlas_name": "x", "url": "u"} for i in range(9)])
    monkeypatch.setattr(main, "answer_multihop", lambda q: answer_mod.Answer(
        "x", hits=[], cited=[], plan=SimpleNamespace(route="graph", conditions=["Any"])))
    acts = stream(fallback, "q")[1][1]["actions"]
    assert [a["label"] for a in acts] == ["S0", "S1", "S2", "S3", "S4"]


def test_fallback_survives_broken_entity_linker(fallback, monkeypatch):
    monkeypatch.setattr(graph, "link_entities", lambda q: (_ for _ in ()).throw(RuntimeError("no graph")))
    assert stream(fallback, "optic chiasm?")[1][1]["actions"][0]["fma_ids"] == ["FMA62045"]


def test_fallback_never_guesses_by_prefix(fallback, monkeypatch):
    """'inferior' must not become 'Inferior mesenteric artery' just because search_concepts prefix-matches it."""
    monkeypatch.setattr(concepts, "search_concepts", lambda q, limit=20: [
        {"id": "x", "label": "Inferior mesenteric artery", "type": "AnatomicalStructure", "degree": 1}])
    monkeypatch.setattr(main, "answer_multihop", lambda q: answer_mod.Answer("inferior wall", hits=[], cited=[], plan=None))
    assert stream(fallback, "inferior wall MI")[1][1]["actions"] == []
