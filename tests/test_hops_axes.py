"""Three-axis case decomposition in rag.hops, with a stubbed LLM (`chat`), retriever and ontology."""
import json

import pytest

from rag import hops

CASE = ("A 58-year-old man with long-standing hypertension and type 2 diabetes is brought to the emergency department "
        "with crushing central chest pain radiating to the left arm for 40 minutes, sweating and breathlessness. "
        "BP is 90/60 mmHg. ECG shows ST elevation in leads II, III and aVF. What is the most likely diagnosis, how "
        "should he be managed immediately, and which drugs should be avoided?")


class FakeHit:
    def __init__(self, id, sim=0.9):
        self.id, self.similarity, self.passage, self.meta = id, sim, f"passage {id}", {"book_id": "b"}

    def citation(self):
        return f"Book › {self.id}"


@pytest.fixture
def stubs(monkeypatch):
    """Stub chat/search/ontology; returns the list of chat calls so tests can assert on them."""
    calls = []

    def set_reply(reply):
        def fake_chat(system, user, **kw):
            calls.append((system, kw.get("purpose")))
            if isinstance(reply, Exception):
                raise reply
            return reply(system) if callable(reply) else reply
        monkeypatch.setattr(hops, "chat", fake_chat)

    monkeypatch.setattr(hops, "search", lambda q, k=5: [FakeHit(f"{q[:12]}-{i}") for i in range(2)])
    monkeypatch.setattr(hops.ontology_facts, "available", lambda: True)
    monkeypatch.setattr(hops.ontology_facts, "match_conditions", lambda name: ["Myocardial infarction"])
    monkeypatch.setattr(hops.ontology_facts, "graph_facts_for", lambda name: [
        "Textbook ontology: first-line treatment for Myocardial infarction: Aspirin (Harrison, p. 1).",
        "Textbook ontology: Myocardial infarction is confirmed by: Troponin (Harrison, p. 2).",
        "WARNING (textbook ontology): Nitrates is contraindicated in Right ventricular infarction (Harrison, p. 3).",
    ])
    return set_reply, calls


GOOD = json.dumps({"likely_condition": "Inferior wall myocardial infarction", "axes": [
    {"axis": "pharmacology", "query": "drug treatment and contraindications in inferior myocardial infarction"},
    {"axis": "etiology", "query": "differential diagnosis of acute chest pain with ST elevation"},
    {"axis": "stabilization", "query": "emergency management of STEMI with hypotension"},
]})


def test_parse_axes_valid_orders_axes_clinically():
    a = hops.parse_axes(GOOD)
    assert a.condition == "Inferior wall myocardial infarction"
    assert [x.axis for x in a.axes] == ["etiology", "stabilization", "pharmacology"]


@pytest.mark.parametrize("raw", [
    "not json at all",
    "[]",
    '{"likely_condition": "x"}',                                               # no axes
    '{"likely_condition": "x", "axes": "etiology"}',                           # wrong type
    '{"likely_condition": "x", "axes": []}',                                   # nothing usable
    '{"likely_condition": "x", "axes": [{"axis": "surgery", "query": "q"}]}',  # unknown axis
    '{"likely_condition": "x", "axes": [{"axis": "etiology", "query": "   "}]}',
    '{"likely_condition": "x", "axes": [{"axis": "etiology", "query": "' + "word " * 30 + '"}]}',  # too long
])
def test_parse_axes_rejects_junk(raw):
    assert hops.parse_axes(raw) is None


def test_parse_axes_drops_bad_items_keeps_good_and_dedupes():
    raw = json.dumps({"likely_condition": 42, "axes": [
        {"axis": "etiology", "query": "causes of chest pain"}, {"axis": "etiology", "query": "duplicate axis"},
        {"axis": "bogus", "query": "x"}, "junk", {"axis": "pharmacology", "query": 7}]})
    a = hops.parse_axes(raw)
    assert a.condition == "" and [(x.axis, x.query) for x in a.axes] == [("etiology", "causes of chest pain")]


def test_case_uses_three_axes_and_routes_ontology_facts(stubs):
    set_reply, calls = stubs
    set_reply(GOOD)
    p = hops.plan_case(CASE)
    assert p.route == "case"
    assert len(calls) == 1 and calls[0][0] == hops.AXES_SYSTEM            # one LLM call, no fallback
    retrieve = [h.query for h in p.hops if h.kind == "retrieve"]
    assert retrieve == ["[etiology] differential diagnosis of acute chest pain with ST elevation",
                        "[stabilization] emergency management of STEMI with hypotension",
                        "[pharmacology] drug treatment and contraindications in inferior myocardial infarction"]
    assert p.evidence and len(p.evidence) <= hops.MAX_EVIDENCE
    assert any("confirmed by" in f for f in p.graph_facts)                 # etiology axis
    assert any("first-line" in f for f in p.graph_facts)                   # pharmacology axis
    assert any(f.startswith("WARNING") for f in p.graph_facts)


def test_axes_that_do_not_apply_are_skipped(stubs):
    set_reply, _ = stubs
    set_reply(json.dumps({"likely_condition": "Hypothyroidism", "axes": [
        {"axis": "etiology", "query": "causes of primary hypothyroidism"}]}))
    p = hops.plan_case(CASE)
    assert [h.query for h in p.hops if h.kind == "retrieve"] == ["[etiology] causes of primary hypothyroidism"]
    assert not any("first-line" in f or f.startswith("WARNING") for f in p.graph_facts)   # no pharmacology axis


def test_no_condition_means_no_ontology_lookup(stubs, monkeypatch):
    set_reply, _ = stubs
    monkeypatch.setattr(hops.ontology_facts, "graph_facts_for", lambda name: pytest.fail("should not be called"))
    set_reply(json.dumps({"likely_condition": "", "axes": [{"axis": "pharmacology", "query": "drug of choice"}]}))
    assert hops.plan_case(CASE).graph_facts == []


def test_junk_reply_falls_back_to_focus_split(stubs):
    set_reply, calls = stubs
    old = json.dumps({"focus": "STEMI", "asks": ["treatment"], "queries": ["management of STEMI"]})
    set_reply(lambda system: old if system == hops.CASE_SYSTEM else "Sorry, I can't help with that.")
    p = hops.plan_case(CASE)
    assert [c[0] for c in calls] == [hops.AXES_SYSTEM, hops.CASE_SYSTEM]
    assert p.hops[0].result == "STEMI :: management of STEMI"


def test_backend_error_falls_back_without_second_llm_call(stubs):
    set_reply, calls = stubs
    set_reply(RuntimeError("DeepSeek API refused the request (HTTP 402). Check the key and balance."))
    p = hops.plan_case(CASE)
    assert len(calls) == 1                                                 # no second doomed call
    assert p.route == "case" and p.evidence                               # still retrieves on the whole case


def test_decompose_case_survives_backend_error(stubs):
    set_reply, _ = stubs
    set_reply(RuntimeError("HTTP 402"))
    assert hops.decompose_case(CASE) == ("", [], [CASE])
