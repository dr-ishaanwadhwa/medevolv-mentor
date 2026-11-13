"""Concept pages (rag/concepts.py) on a tiny synthetic ontology, plus the leak test: only certified ontology facts
and textbook passages may reach the answer prompt as citable evidence."""
import pytest

from rag import answer, concepts, hops, ontology_facts


def fact(i, sub, pred, obj, book="harrison", extra_books=(), sub_type="PathologicalCondition", obj_type="TherapeuticAgent"):
    src = [{"book_id": b, "book_title": b, "chapter": "1 X", "section_id": f"{b}/001-x", "pages": [1, 2], "verbatim_quote": "q"}
           for b in (book, *extra_books)]
    return {"id": f"f{i}", "subject_id": sub.lower(), "subject_label": sub, "subject_type": sub_type,
            "predicate": pred, "object_id": obj.lower(), "object_label": obj, "object_type": obj_type,
            "status": "CERTIFIED", "clinical_facets": {}, "provenance": src[0], "sources": src}


FACTS = (
    fact(1, "Tuberculosis", "TREATED_BY", "Rifampicin", extra_books=("davidson",)),
    fact(2, "Tuberculosis", "TREATED_BY", "Isoniazid"),
    fact(3, "Hepatitis", "CONTRAINDICATES", "Rifampicin"),
    fact(4, "Tuberculosis", "MANIFESTS_AS", "Cough", obj_type="ClinicalPhenotype"),
    fact(5, "Tuberculosis", "CONFIRMED_BY", "Sputum culture", obj_type="DiagnosticModality"),
    fact(6, "Rifampicin", "CAUSES_ADVERSE_EFFECT", "Hepatotoxicity", sub_type="TherapeuticAgent", obj_type="ClinicalPhenotype"),
)


@pytest.fixture
def onto(monkeypatch):
    monkeypatch.setattr(ontology_facts, "facts", lambda: FACTS)
    monkeypatch.setattr(concepts, "_heading_nav", lambda: ({}, {}, {}))   # real headings must not be cached against fake facts
    concepts._index.cache_clear()
    yield
    concepts._index.cache_clear()


def test_drug_page_has_backlinks_with_correct_direction(onto):
    c = concepts.concept("rifampicin")                  # label lookup is case-insensitive
    assert c["type"] == "TherapeuticAgent" and c["degree"] == 3
    assert [l["other_label"] for l in c["backlinks"]["treats"]] == ["Tuberculosis"]
    assert [l["other_label"] for l in c["backlinks"]["contraindicated in"]] == ["Hepatitis"]   # never "treats"
    assert "Hepatotoxicity" in [l["other_label"] for l in c["outgoing"]["CAUSES_ADVERSE_EFFECT"]]
    assert c["books"] == ["davidson", "harrison"]


def test_symptom_and_test_backlinks(onto):
    assert concepts.concept("Cough")["backlinks"]["manifestation of"][0]["other_label"] == "Tuberculosis"
    assert concepts.concept("Sputum culture")["backlinks"]["confirms"][0]["other_label"] == "Tuberculosis"


def test_tiers_direct_is_certified_inverse_is_derived(onto):
    tb, rif = concepts.concept("Tuberculosis"), concepts.concept("Rifampicin")
    assert all(l["tier"] == "certified" for ls in tb["outgoing"].values() for l in ls)
    assert all(l["tier"] == "derived" for ls in rif["backlinks"].values() for l in ls)
    # an inverse edge is the same fact, not a new one
    assert rif["backlinks"]["treats"][0]["fact_id"] == tb["outgoing"]["TREATED_BY"][0]["fact_id"]


def test_related_ranks_by_shared_facts_then_books(onto):
    rel = concepts.related("Tuberculosis", k=3)
    assert rel[0]["label"] == "Rifampicin"              # stated by 2 books beats the other single-fact neighbours
    assert all(r["tier"] == "certified" for r in rel)
    assert concepts.related("Rifampicin")[0]["tier"] in {"certified", "derived"}
    assert concepts.related("nonsense") == []


def test_search_prefix(onto):
    assert [r["label"] for r in concepts.search_concepts("tub")] == ["Tuberculosis"]
    assert concepts.search_concepts("culture")[0]["label"] == "Sputum culture"     # word prefix
    assert concepts.search_concepts("") == []


def test_empty_when_ontology_missing(monkeypatch):
    monkeypatch.setattr(ontology_facts, "facts", lambda: ())
    concepts._index.cache_clear()
    assert concepts.concept("Tuberculosis") == {} and concepts.related("x") == [] and concepts.search_concepts("t") == []
    concepts._index.cache_clear()


def test_every_predicate_in_real_ontology_has_an_inverse_name():
    preds = {f["predicate"] for f in ontology_facts.facts()}
    if not preds:
        pytest.skip("no ontology on this machine")
    assert preds <= set(concepts.INVERSE)


# ---------------- leak test ----------------
class FakeHit:
    def __init__(self, id):
        self.id, self.similarity, self.passage, self.meta = id, 0.9, f"textbook passage {id}", {"book_id": "b", "book": "B"}

    def citation(self):
        return f"Book > {self.id}"


ONTOLOGY_LINES = ["Textbook ontology: first-line treatment for Dengue fever: Paracetamol (Harrison, p. 1).",
                  "WARNING (textbook ontology): Aspirin is contraindicated in Dengue fever (Harrison, p. 2)."]


@pytest.fixture
def graph_route(monkeypatch):
    monkeypatch.setattr(hops, "link_entities", lambda q: [{"name": "Fever", "type": "Symptom", "ids": ["s1"]},
                                                          {"name": "Rash", "type": "Symptom", "ids": ["s2"]}])
    pool = [{"id": "c1", "name": "Dengue fever", "symptoms_matched": 2, "score": 6, "spec": 1.0}]
    monkeypatch.setattr(hops, "conditions_for_symptoms", lambda ids, top=5: [dict(c) for c in pool])
    monkeypatch.setattr(hops, "specialities_for", lambda cid: ["Infectious disease"])
    monkeypatch.setattr(hops, "drugs_for", lambda cid: ["BODHIONLYDRUG", "ANOTHERBODHIDRUG"])
    monkeypatch.setattr(hops, "search", lambda q, k=5: [FakeHit("a"), FakeHit("b")])
    monkeypatch.setattr(hops, "mentions", lambda h, c: True)
    monkeypatch.setattr(hops, "names_condition", lambda h, c: True)
    monkeypatch.setattr(hops.ontology_facts, "available", lambda: True)
    monkeypatch.setattr(hops.ontology_facts, "match_conditions", lambda n: ["Dengue fever"])
    monkeypatch.setattr(hops.ontology_facts, "graph_facts_for", lambda n: list(ONTOLOGY_LINES))


def test_bodhi_never_reaches_graph_facts(graph_route):
    p = hops.plan("Fever and rash after a mosquito bite, what is the diagnosis?")
    assert p.route == "graph"
    # BODHI may supply the differential and the specialist, never drugs; drugs come only from certified ontology
    assert all(f in ONTOLOGY_LINES or (f.startswith("BODHI") and "drug" not in f.lower()) for f in p.graph_facts)
    assert set(ONTOLOGY_LINES) <= set(p.graph_facts)
    assert not any("BODHIONLYDRUG" in f or "ANOTHERBODHIDRUG" in f for f in p.graph_facts)
    assert any("BODHIONLYDRUG" in h for h in p.nav_hints)       # still available as a navigation hint
    assert p.bodhi_drugs == {"Dengue fever": ["BODHIONLYDRUG", "ANOTHERBODHIDRUG"]}   # cross_check still works


def test_answer_prompt_has_only_certified_facts_and_passages(graph_route, monkeypatch):
    prompts = []
    monkeypatch.setattr(answer, "chat", lambda system, user, **kw: prompts.append(user) or "Paracetamol [G1] [1].")
    res = answer.answer_multihop("Fever and rash after a mosquito bite, what is the diagnosis?")
    prompt = prompts[0]
    assert "BODHIONLYDRUG" not in prompt and "ANOTHERBODHIDRUG" not in prompt and "BODHI drug links" not in prompt
    graph_part = prompt.split("Textbook passages:")[0]
    g = [l.split("] ", 1)[1] for l in graph_part.splitlines() if l.startswith("[G")]
    assert all(f in ONTOLOGY_LINES or (f.startswith("BODHI") and "drug" not in f.lower()) for f in g)
    assert "textbook passage" in prompt
    assert res.plan.nav_hints                                   # hints exist for the UI but were not sent


# ---- heading navigation data on concept pages (rag/headings.py, tier T2: never a fact, never in the prompt)

def test_heading_fields_on_concept_page(onto, monkeypatch):
    slim = {"heading_id": "h1", "book_id": "harrison", "section_id": "harrison/001-x", "heading": "Tuberculosis",
            "path": ["Part 1", "Tuberculosis"], "method": "rule1:heading-exact", "tier": "T2"}
    monkeypatch.setattr(concepts, "_heading_nav", lambda: (
        {"tuberculosis": [slim]}, {"tuberculosis": [slim]}, {"tuberculosis": ["Koch disease", "Tuberculosis"]}))
    c = concepts.concept("Tuberculosis")
    assert [t["section_id"] for t in c["topic_sections"]] == ["harrison/001-x"]
    assert c["topic_sections"][0]["tier"] == "T2" and len(c["headings"]) == 1
    assert c["heading_aliases"] == ["Koch disease"]                    # the label itself is not an alias
    assert "Koch disease" in c["aliases"]
    other = concepts.concept("Cough")
    assert other["topic_sections"] == [] and other["headings"] == [] and other["heading_aliases"] == []
    assert not any("headings" in str(l) for ls in c["outgoing"].values() for l in ls)   # facts stay fact-only


def test_non_name_parentheticals_are_not_aliases():
    for junk in ("Table 7.7", "pp. 729-730", "anterior view", "Fig. 4", "12"):
        assert concepts._NOT_AN_ALIAS.search(junk), junk
    for ok in ("Rubeola", "VHF", "obstructive uropathy"):
        assert not concepts._NOT_AN_ALIAS.search(ok), ok


def test_real_headings_give_topic_sections_and_aliases():
    from pathlib import Path
    if not Path("data/graph/headings.jsonl").exists() or not Path("data/ontology/clinical_ontology.jsonl").exists():
        pytest.skip("headings or ontology not built")
    concepts._index.cache_clear()
    concepts._heading_nav.cache_clear()
    tb = concepts.concept("Tuberculosis")
    assert "harrison/183-183-tuberculosis" in [t["section_id"] for t in tb["topic_sections"]]
    assert all(t["tier"] == "T2" and "body" not in t for t in tb["topic_sections"])
    some = [c for c in (concepts.concept(l) for l in ("Measles", "Rubella", "Pertussis")) if c.get("heading_aliases")]
    assert some                                                         # at least one parenthetical alias reaches a page
