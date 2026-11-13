"""GRAPH_WALK (Stage 5): navigation-only expansion. Stubs the retriever, mention index and ontology; the crosswalk is real
(read from a temp file) so the T2/T3 gate is exercised for real. The leak tests are the hard gate of the plan."""
import inspect
import json

import pytest

from rag import comention, config, crosswalk as cw, hops, hubs, mentions

SENTINEL = "MENTION-ONLY-SENTINEL"


class FakeHit:
    def __init__(self, id, book="harrison", sim=0.8, section=None):
        self.id, self.similarity, self.passage = id, sim, f"passage {id}"
        self.meta = {"book_id": book, "section_id": section or id.split("#")[0]}

    def citation(self):
        return f"Book {self.id}"

    def __eq__(self, o):
        return isinstance(o, FakeHit) and o.id == self.id

    __hash__ = None


def _row(**kw):
    base = {"ont_id": "o1", "ont_label": "Pneumonia", "ont_type": "PathologicalCondition", "bodhi_id": "b1",
            "bodhi_ids": ["b1"], "bodhi_name": "Lobar pneumonia", "bodhi_type": "Condition", "relation": "exact",
            "score": 1.0, "method": "name_key", "checked": True, "tier": "T2", "note": ""}
    return {**base, **kw}


@pytest.fixture
def walk(tmp_path, monkeypatch):
    rows = [_row(),                                                                    # T2: may feed certified facts
            _row(ont_id="o2", ont_label="T3 only disease", bodhi_id="b2", bodhi_ids=["b2"], bodhi_name="Bodhi two",
                 relation="broader", checked=False, tier="T3"),
            _row(ont_id="o3", ont_label="Related only disease", bodhi_id="b3", bodhi_ids=["b3"], bodhi_name="Bodhi three",
                 relation="related", checked=True, tier="T3")]
    f = tmp_path / "crosswalk.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(cw, "PATH", f)
    for fn in (cw._records, cw._by_label, cw._by_bodhi):
        fn.cache_clear()

    def poison(*a, **k):
        raise AssertionError("hubs / co-mention must never be read by hops.py")
    for mod in (hubs, comention):
        for name, fn in vars(mod).items():
            if callable(fn) and not name.startswith("_") and getattr(fn, "__module__", "") == mod.__name__:
                monkeypatch.setattr(mod, name, poison)

    state = {"searches": [], "hits": {}}
    monkeypatch.setattr(config, "GRAPH_WALK", True)
    monkeypatch.setattr(hops.ontology_facts, "available", lambda: True)
    monkeypatch.setattr(hops.ontology_facts, "condition_labels", lambda: ())
    hops._label_keys.cache_clear()
    monkeypatch.setattr(hops.ontology_facts, "match_conditions", lambda name: [name] if name == "Asthma" else [])
    facts = {"Asthma": ["Textbook ontology: first-line treatment for Asthma: Salbutamol (Tripathi, p. 1)."],
             "Pneumonia": ["Textbook ontology: first-line treatment for Pneumonia: Amoxicillin (Harrison, p. 2)."],
             "T3 only disease": ["Textbook ontology: first-line treatment for T3 only disease: LEAK (X, p. 9)."],
             "Related only disease": ["Textbook ontology: first-line treatment for Related only disease: LEAK (X, p. 9)."]}
    monkeypatch.setattr(hops.ontology_facts, "graph_facts_for", lambda name: list(facts.get(name, [])))
    monkeypatch.setattr(hops.mention_index, "sections_for", lambda label, k=5, min_strength=None: [
        {"section_id": f"{b}/s-{label}", "book_id": b, "title": SENTINEL, "path": [SENTINEL], "count": 9,
         "strength": 20.0, "evidence": "mention", "tier": "mention"} for b in ("harrison", "robbins", "tripathi")])

    def fake_search(q, k=5, section_ids=None, book_ids=None):
        state["searches"].append((q, section_ids))
        return state["hits"].get(tuple(section_ids or ()), state["hits"].get("*", []))
    monkeypatch.setattr(hops, "search", fake_search)
    yield state
    for fn in (cw._records, cw._by_label, cw._by_bodhi):
        fn.cache_clear()


def _plan(cands=(("b2", "T3 only disease"), ("b1", "Lobar pneumonia"), ("b0", "Asthma")), n_ev=3):
    p = hops.Plan(route="graph")
    p.candidates = [{"id": i, "name": n} for i, n in cands]
    p.conditions = [n for _, n in cands]
    p.evidence = [FakeHit(f"harrison/e{i}#p1", "harrison") for i in range(n_ev)]
    return p


# ---------------------------------------------------------------- flag and routing
def test_flag_off_never_walks(monkeypatch):
    monkeypatch.setattr(config, "GRAPH_WALK", False)
    monkeypatch.setattr(hops, "_plan_routes", lambda q: hops.Plan(route="graph"))
    monkeypatch.setattr(hops, "graph_walk", lambda *a: pytest.fail("walk ran with the flag off"))
    assert hops.plan("q").route == "graph"


def test_single_route_is_left_alone(monkeypatch):
    monkeypatch.setattr(config, "GRAPH_WALK", True)
    monkeypatch.setattr(hops, "_plan_routes", lambda q: hops.Plan(route="single"))
    monkeypatch.setattr(hops, "graph_walk", lambda *a: pytest.fail("walk ran on the single route"))
    assert hops.plan("q").route == "single"


def test_default_is_off():
    assert 'os.getenv("GRAPH_WALK", "0") == "1"' in inspect.getsource(config)


# ---------------------------------------------------------------- expansion
def test_expansion_adds_at_most_two_and_records_a_hop(walk):
    walk["hits"]["*"] = [FakeHit(f"robbins/x#p{i}", "robbins", 0.9 - i / 100) for i in range(5)]
    p = _plan()
    hops.graph_walk(p, "question about asthma")
    assert len(p.walk["added"]) == 2 and len(p.evidence) == 5
    assert [h.kind for h in p.hops] == ["expand"]
    assert all(sid for _, sid in walk["searches"])                    # every search was section-restricted


def test_expansion_respects_min_similarity(walk):
    walk["hits"]["*"] = [FakeHit("robbins/x#p1", "robbins", config.MIN_SIMILARITY - 0.01)]
    p = _plan()
    hops.graph_walk(p, "q")
    assert p.walk["added"] == [] and len(p.evidence) == 3


def test_expansion_does_not_duplicate_evidence(walk):
    walk["hits"]["*"] = [FakeHit("harrison/e0#p1", "harrison", 0.95)]
    p = _plan()
    hops.graph_walk(p, "q")
    assert p.walk["added"] == [] and len(p.evidence) == 3


def test_full_evidence_never_exceeds_cap(walk):
    walk["hits"]["*"] = [FakeHit(f"robbins/x#p{i}", "robbins", 0.9) for i in range(3)]
    p = _plan(n_ev=hops.MAX_EVIDENCE)
    hops.graph_walk(p, "q")
    assert len(p.evidence) == hops.MAX_EVIDENCE and len(p.walk["added"]) == 2


def test_sections_prefer_books_not_in_evidence(walk):
    p = _plan()                                                       # evidence is all Harrison
    secs = hops.walk_sections("Asthma", p.evidence)
    assert secs[0]["book_id"] != "harrison" and len(secs) == hops.WALK_SECTIONS
    assert secs[-1]["book_id"] == "harrison"


# ---------------------------------------------------------------- bridge to certified facts
def test_bridge_uses_t2_exact_links_only(walk):
    p = _plan()
    hops.graph_walk(p, "q")
    text = " ".join(p.graph_facts)
    assert "Amoxicillin" in text                                      # b1 -> Pneumonia (T2) now has certified facts
    assert "LEAK" not in text                                         # broader/unchecked and related links add nothing
    assert p.walk["bridge_facts"] == 1


def test_bridge_skips_candidates_already_covered_by_name(walk):
    p = _plan(cands=(("b0", "Asthma"),))
    hops.graph_walk(p, "q")
    assert p.graph_facts == [] and p.walk["bridge_facts"] == 0


# ---------------------------------------------------------------- LEAK TESTS: nothing below T1 reaches graph_facts
def test_mention_hub_comention_text_never_reaches_graph_facts(walk):
    walk["hits"]["*"] = [FakeHit("robbins/x#p1", "robbins", 0.9)]
    p = _plan()
    hops.graph_walk(p, "q")                                           # hubs/co-mention are poisoned: any call fails
    assert p.walk["added"]
    assert SENTINEL not in " ".join(p.graph_facts)
    assert all(f.startswith(("Textbook ontology:", "WARNING (textbook ontology)")) for f in p.graph_facts)
    assert p.nav_hints == [] and p.bodhi_drugs == {}


def test_non_trusted_crosswalk_labels_never_resolve(walk):
    assert cw.trusted_labels("b1") == ["Pneumonia"]
    assert cw.trusted_labels("b2") == [] and cw.trusted_labels("b3") == []
    p = _plan(cands=(("b2", "Bodhi two"), ("b3", "Bodhi three")))
    ents = hops.resolve_entities("q", p)
    assert ents == []                                                 # broader / related / unchecked rows resolve nothing


def test_every_graph_fact_comes_from_graph_facts_for(walk):
    walk["hits"]["*"] = [FakeHit("robbins/x#p1", "robbins", 0.9)]
    p = _plan()
    hops.graph_walk(p, "q")
    allowed = {l for ls in (hops.ontology_facts.graph_facts_for(n) for n in ("Asthma", "Pneumonia")) for l in ls}
    assert set(p.graph_facts) <= allowed


def test_hops_source_has_no_forbidden_tiers():
    src = inspect.getsource(hops)
    for banned in ("rag.hubs", "import hubs", "comention", "rag.concepts", "bodhi_for(", "ontology_for("):
        assert banned not in src, f"hops.py must not use {banned}"
    walk_src = inspect.getsource(hops.graph_walk) + inspect.getsource(hops._bridge_facts) + inspect.getsource(hops.resolve_entities)
    assert "graph_facts.append(" not in walk_src.replace("p.graph_facts.append(line)", "")   # only the certified line path
    assert "trusted_labels" in walk_src
    # sections_for rows are read for ids and books only, never as text for the prompt
    assert '["title"]' not in walk_src and '["path"]' not in walk_src


def test_expansion_hits_are_plain_evidence_not_graph_facts(walk):
    walk["hits"]["*"] = [FakeHit("robbins/x#p1", "robbins", 0.9)]
    p = _plan()
    before = list(p.graph_facts)
    hops.graph_walk(p, "q")
    assert any(h.id == "robbins/x#p1" for h in p.evidence)
    assert not any("robbins/x#p1" in f or "passage" in f for f in p.graph_facts[len(before):])
