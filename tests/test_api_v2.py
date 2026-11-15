"""W1 endpoints: why stream, concept page, saved answers, feedback. No network, no LLM, no real data except the concept test."""
import json

import pytest
from fastapi.testclient import TestClient

from api import main, store, why
from api.schemas import ConceptPage, DoneEvent, ErrorEvent, StepEvent, VerdictEvent
from rag import config, trace
from rag.retrieve import Hit

from tests.test_api import parse_sse

OPTS = ["Beta blocker first", "Alpha blocker first", "Surgery immediately"]


def mk_hit(i, sim=0.8):
    return Hit(id=f"harrison/s1#p{i}", passage="Phenoxybenzamine precedes beta blockade. " * 30,
               meta={"book": "Harrison", "book_id": "harrison", "chapter": "Endocrine", "pages": "10-12",
                     "section_id": "harrison/s1", "section_title": "Pheo", "section_path": "Harrison › Endocrine › Pheo",
                     "heading": ""}, similarity=sim)


GOOD = {"grounded": True, "correct_option": "B", "chosen_wrong_because": "Unopposed alpha stimulation causes crisis [1].",
        "explanation": "Alpha blockade comes first [1][2].", "viva_questions": ["Why alpha first?", "Which drug?", "Target BP?"]}


@pytest.fixture
def whyc(monkeypatch):
    monkeypatch.setattr(why, "search", lambda q, k=6: [mk_hit(1), mk_hit(2, 0.7)])
    calls = []

    def fake_chat(system, user, **kw):
        trace.record("llm", "fake", "x")
        calls.append(user)
        out = replies.pop(0) if len(replies) > 1 else replies[0]
        return out if isinstance(out, str) else json.dumps(out)
    replies = [GOOD]
    monkeypatch.setattr(why, "chat", fake_chat)
    c = TestClient(main.app)
    c.replies, c.calls = replies, calls
    return c


def why_stream(c, chosen=0, opts=OPTS):
    r = c.post("/api/why/stream", json={"question": "Pheo pre-op?", "options": opts, "chosen": chosen})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def test_why_verdict_happy_path(whyc):
    ev = why_stream(whyc)
    assert [e for e, _ in ev][-2:] == ["verdict", "done"] and all(e == "step" for e, _ in ev[:-2])
    StepEvent.model_validate(ev[0][1])
    DoneEvent.model_validate(ev[-1][1])
    v = VerdictEvent.model_validate(ev[-2][1])
    assert v.status == "verdict" and v.correct_option == 1 and len(v.viva_questions) == 3
    assert [c.cited for c in v.citations] == [True, True] and all(len(c.excerpt) <= 301 for c in v.citations)
    assert "B. Alpha blocker first" in whyc.calls[0] and "student chose A" in whyc.calls[0]


def test_why_chosen_correct_says_so(whyc):
    whyc.replies[0] = {**GOOD, "chosen_wrong_because": "Alpha blockade protects against crisis [1]."}
    v = why_stream(whyc, chosen=1)[-2][1]
    assert v["correct_option"] == 1 and v["chosen_wrong_because"].startswith("Your choice was correct")


@pytest.mark.parametrize("bad", [
    {"grounded": False, "correct_option": None},
    {**GOOD, "explanation": "No citations here."},
    {**GOOD, "explanation": "Cites a ghost [9]."},
    {**GOOD, "correct_option": "F"},
    {**GOOD, "viva_questions": ["only one"]},
])
def test_why_ungrounded_is_insufficient(whyc, bad):
    whyc.replies[0] = bad
    v = why_stream(whyc)[-2][1]
    assert v["status"] == "insufficient" and v["correct_option"] is None and "don't settle this" in v["explanation"]
    assert v["viva_questions"] == []


@pytest.mark.parametrize("garbage", ["not json at all", "[1,2]", "{broken", ""])
def test_why_malformed_json_never_500(whyc, garbage):
    whyc.replies[0] = garbage
    ev = why_stream(whyc)
    assert [e for e, _ in ev][-2:] == ["verdict", "done"] and ev[-2][1]["status"] == "insufficient"


def test_why_retry_recovers(whyc):
    whyc.replies[:] = ["oops", GOOD]
    assert why_stream(whyc)[-2][1]["status"] == "verdict" and len(whyc.calls) == 2


def test_why_fenced_json_parses(whyc):
    whyc.replies[0] = "```json\n" + json.dumps(GOOD) + "\n```"
    assert why_stream(whyc)[-2][1]["status"] == "verdict"


def test_why_no_relevant_passages_skips_llm(whyc, monkeypatch):
    monkeypatch.setattr(why, "search", lambda q, k=6: [mk_hit(1, config.MIN_SIMILARITY - 0.2)])
    assert why_stream(whyc)[-2][1]["status"] == "insufficient" and whyc.calls == []


def test_why_backend_error_is_error_event(whyc, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("secret key abc")
    monkeypatch.setattr(why, "chat", boom)
    ev = why_stream(whyc)
    assert ev[-1][0] == "error" and "secret" not in json.dumps(ev[-1][1])
    ErrorEvent.model_validate(ev[-1][1])


def test_why_request_validation(whyc):
    post = lambda **b: whyc.post("/api/why/stream", json={"question": "q", "options": OPTS, "chosen": 0, **b}).status_code
    assert post(options=["only one"]) == 422 and post(options=list("abcdefg")) == 422
    assert post(chosen=3) == 422 and post(chosen=-1) == 422 and post(question="") == 422


# ---- concept page (real data; skipped when the ontology is not available)

@pytest.fixture(scope="module")
def real():
    from rag import concepts
    if not concepts.search_concepts("pheochromocytoma", 1):
        pytest.skip("ontology not available")
    return TestClient(main.app)


def test_concept_page_shape_real(real):
    r = real.get("/api/concepts/Pheochromocytoma")
    assert r.status_code == 200
    p = ConceptPage.model_validate(r.json())
    assert p.label == "Pheochromocytoma" and p.books and p.links_out and p.sections
    assert any(s.primary for s in p.sections)
    assert {l.tier for l in p.links_out} <= {"certified"} and {l.tier for l in p.links_in} <= {"derived"}
    assert all(s.tier == "suggested" for s in p.see_also)
    assert p.graph.nodes[0].center and len(p.graph.nodes) <= 40
    ids = {n.id for n in p.graph.nodes}
    assert all(e.source in ids and e.target in ids for e in p.graph.edges)
    assert real.get(f"/api/concepts/{p.id}").json()["id"] == p.id               # by id too
    assert p.atlas.link is None or p.atlas.link.startswith("http")
    assert isinstance(p.atlas.structures, list)


def test_concept_ids_with_slashes_and_search_still_work(real):
    hit = real.get("/api/concepts/search", params={"q": "paroxysmal"}).json()
    assert hit and real.get(f"/api/concepts/{hit[0]['id']}").status_code == 200


def test_concept_404_json(real):
    r = real.get("/api/concepts/no-such-thing-xyz")
    assert r.status_code == 404 and r.json() == {"detail": "Unknown concept"}


# ---- answers + feedback

@pytest.fixture
def db(tmp_path, monkeypatch):
    monkeypatch.setenv("APP_DB", str(tmp_path / "sub" / "app.db"))
    return TestClient(main.app)


def test_answers_roundtrip(db):
    r = db.post("/api/answers", json={"kind": "why", "question": "q?", "payload": {"a": [1, "é"]}})
    assert r.status_code == 200
    aid = r.json()["id"]
    assert 6 <= len(aid) <= 10 and aid.replace("-", "").replace("_", "").isalnum()
    rec = db.get(f"/api/answers/{aid}").json()
    assert rec["kind"] == "why" and rec["question"] == "q?" and rec["payload"] == {"a": [1, "é"]} and rec["created_at"] > 0
    assert db.get("/api/answers/nope").status_code == 404
    assert db.post("/api/answers", json={"kind": "other", "question": "q", "payload": {}}).status_code == 422
    assert db.post("/api/answers", json={"kind": "chat", "question": "q", "payload": []}).status_code == 422


def test_answers_payload_cap(db):
    big = {"x": "a" * (store.MAX_PAYLOAD_BYTES + 10)}
    assert db.post("/api/answers", json={"kind": "chat", "question": "q", "payload": big}).status_code == 413


def test_default_db_is_in_worktree_var(monkeypatch):
    monkeypatch.delenv("APP_DB", raising=False)
    p = store.db_path()
    assert p.parts[-2:] == ("var", "app.db") and "data" not in p.parts[-3:-2]


def test_feedback(db):
    ok = lambda **b: db.post("/api/feedback", json=b)
    assert ok(kind="wrong_citation", answer_id="abc", note="p.5 is wrong").json() == {"ok": True}
    assert ok(kind="unhelpful", question="q").status_code == 200
    assert ok(kind="other").status_code == 200
    assert ok(kind="spam").status_code == 422 and ok().status_code == 422
    assert ok(kind="other", note="x" * 1001).status_code == 422
    assert ok(kind="other", note="x" * 1000).status_code == 200


def test_spatial_resolve_handles_list_paths():
    """mentions rows carry `path` as a list (chapter first); resolve once crashed on .split() for every concept."""
    from pathlib import Path
    import pytest
    from fastapi.testclient import TestClient
    from api.main import app
    if not Path("data/graph").exists():
        pytest.skip("no graph data")
    r = TestClient(app).get("/api/spatial/resolve", params={"label": "Optic chiasm"})
    assert r.status_code == 200
    assert all(not c["chapter"][:1].isdigit() for c in r.json()["citations"])


# ---------------------------------------------------------------- `topic` SSE event (PRD 4.2 seam)

from types import SimpleNamespace as _NS

from api import spatial as spatial_mod, topic as topic_mod
from api.schemas import TopicEvent
from rag import answer as _answer_mod, concepts as _concepts, diagrams as _diagrams
from tests.test_api import client, stream  # noqa: F401  (fixture reused: stubbed answer, atlas and concepts)


def _link(i, pred="TREATED_BY", tier="certified", books=("harrison",)):
    return {"other_id": f"C:{i}", "other_label": f"Concept {i}", "other_type": "Drug", "predicate": pred,
            "tier": tier, "books": list(books), "fact_id": f"f{i}", "sections": []}


def test_topic_event_between_spatial_and_done(client, monkeypatch):
    monkeypatch.setattr(_diagrams, "pick_subject", lambda q, condition=None, drug=None: None)
    ev = stream(client)
    names = [e for e, _ in ev]
    assert names[-3:] == ["spatial", "topic", "done"]
    t = TopicEvent.model_validate(ev[-2][1])
    assert t.topic == "Right coronary artery"           # (2) first spatial highlight label
    assert t.related == []                              # stub concept has no outgoing links


def test_topic_prefers_ontology_subject_and_returns_certified_related_only(client, monkeypatch):
    monkeypatch.setattr(_diagrams, "pick_subject", lambda q, condition=None, drug=None: ("case", "Nephrotic syndrome"))
    links = [_link(i) for i in range(8)] + [_link(99, tier="derived"), _link(0, pred="OTHER", books=("a", "b"))]
    concept = {"id": "C:ns", "label": "Nephrotic syndrome", "outgoing": {"TREATED_BY": links}}
    monkeypatch.setattr(_concepts, "concept", lambda n: concept if n == "Nephrotic syndrome" else {})
    t = TopicEvent.model_validate(stream(client)[-2][1])
    assert t.topic == "Nephrotic syndrome"
    assert len(t.related) == 6 and all(r.tier == "certified" for r in t.related)
    assert "C:99" not in {r.id for r in t.related}                 # derived link never listed
    assert t.related[0].id == "C:0" and len({r.id for r in t.related}) == 6   # most books first, no duplicates


@pytest.mark.parametrize("q", ["My mother has chest pain, should I give her aspirin?", "I have a lump, what should I do?",
                               "A patient with MI: what dose of heparin should I give?"])
def test_topic_null_for_patient_scoped_questions(client, monkeypatch, q):
    monkeypatch.setattr(spatial_mod, "recognised_concepts", lambda question, text: [])   # keep the real entity linker out
    t = stream(client, q)[-2]
    assert t == ("topic", {"topic": None, "related": []})


def test_topic_null_when_answer_is_declined(client, monkeypatch):
    monkeypatch.setattr(main, "answer_multihop", lambda q: _answer_mod.Answer("not here", status="not_in_sources"))
    assert stream(client)[-2] == ("topic", {"topic": None, "related": []})


def test_topic_failure_never_breaks_the_stream(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("ontology missing")
    monkeypatch.setattr(topic_mod, "topic_event", boom)
    ev = stream(client)
    assert [e for e, _ in ev][-3:] == ["spatial", "topic", "done"] and ev[-2][1] == {"topic": None, "related": []}
