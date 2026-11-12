"""Clinical graph builder (synthetic ontology facts; no textbook text, no LLM calls)."""
from collections import Counter

import pytest

from rag import clinical_graph as cg
from rag import ontology_facts as onto


def _f(i, subj, pred, obj, obj_type="X", **facets):
    return {"id": f"t{i}", "subject_label": subj, "subject_type": "PathologicalCondition", "predicate": pred,
            "object_label": obj, "object_type": obj_type, "status": "CERTIFIED",
            "clinical_facets": {"line_of_therapy": None, "contraindication_severity": None, **facets},
            "provenance": {"book_id": "synth", "book_title": "Synthetic Text", "chapter": "1. Test", "pages": [10],
                           "verbatim_quote": f"quote {i}"}, "nl_fact": f"fact {i}"}


FACTS = (
    _f(1, "Condition alpha", "MANIFESTS_AS", "Chest pain"),
    _f(2, "Condition alpha", "MANIFESTS_AS", "Breathlessness"),
    _f(3, "Condition alpha", "HAS_CLINICAL_STAGE", "Early phase"),
    _f(4, "Condition alpha", "CONFIRMED_BY", "Blood marker"),
    _f(5, "Condition alpha", "TREATED_BY", "Drug two", line_of_therapy="SECOND_LINE"),
    _f(6, "Condition alpha", "TREATED_BY", "Drug one", line_of_therapy="FIRST_LINE"),
    _f(7, "Condition alpha", "CONTRAINDICATES", "Drug bad", contraindication_severity="STRICT"),
    _f(8, "Condition alpha", "DIFFERENTIAL_OF", "Condition gamma"),
    _f(9, "Condition beta", "MANIFESTS_AS", "Fever"),
    _f(10, "Condition beta", "CONFIRMED_BY", "Culture"),
) + tuple(_f(100 + i, "Condition alpha", "TREATED_BY", f"Extra drug {i}") for i in range(20))


@pytest.fixture(autouse=True)
def synthetic(monkeypatch):
    counts = Counter(f["subject_label"] for f in FACTS)
    monkeypatch.setattr(onto, "facts", lambda: FACTS)
    monkeypatch.setattr(onto, "_counts", lambda: counts)
    monkeypatch.setattr(onto, "condition_labels", lambda: tuple(c for c, _ in counts.most_common()))


def kinds(g):
    return Counter(n["kind"] for n in g["nodes"])


def test_starts_with_complaints_and_differential_only():
    g = cg.build(["chest pain", "fever"], ["Condition alpha", "Condition beta"])
    assert kinds(g) == {"symptom": 2, "condition": 3}          # 2 candidates + 1 textbook differential
    assert {n["level"] for n in g["nodes"]} == {1, 2}
    e = next(e for e in g["edges"] if e["from"] == "symptom:chest pain")
    assert e["to"] == "condition:condition alpha" and g["facts"][e["fact"]]["id"] == "t1"
    # 'fever' is a presentation of beta, cited; no uncited edge when a cited one exists
    assert any(e["from"] == "symptom:fever" and e["fact"] == "t9" for e in g["edges"])


def test_drilling_reveals_levels_in_order():
    g3 = cg.build(["chest pain"], ["Condition alpha"], {"Condition alpha": 3})
    assert kinds(g3)["stage"] == 1 and "diagnostic" not in kinds(g3)
    g4 = cg.build(["chest pain"], ["Condition alpha"], {"Condition alpha": 4})
    assert kinds(g4)["diagnostic"] == 1 and "drug" not in kinds(g4)
    g5 = cg.build(["chest pain"], ["Condition alpha"], {"Condition alpha": 5})
    assert {n["level"] for n in g5["nodes"]} == {1, 2, 3, 4, 5}
    assert kinds(g5)["contra"] == 1


def test_drugs_capped_and_first_line_first():
    g = cg.build([], ["Condition alpha"], {"Condition alpha": 5})
    drugs = [e for e in g["edges"] if g["facts"].get(e["fact"], {}).get("predicate") == "TREATED_BY"]
    assert len(drugs) == cg.CAPS["drugs"]
    assert drugs[0]["to"] == "drug:drug one" and "1st line" in drugs[0]["label"]
    assert drugs[1]["to"] == "drug:drug two"


def test_every_cited_edge_has_its_fact():
    g = cg.build(["chest pain"], ["Condition alpha"], {"Condition alpha": 5})
    ids = {n["id"] for n in g["nodes"]}
    for e in g["edges"]:
        assert e["from"] in ids and e["to"] in ids
        if e["fact"]:
            assert "quote" in g["facts"][e["fact"]]["provenance"]["verbatim_quote"]
            assert onto.cite(g["facts"][e["fact"]]) == "Synthetic Text, Test, p. 10"


def test_no_vignette_symptoms_uses_presentation_and_unmatched_gets_dashed_link():
    g = cg.build([], ["Condition alpha"])
    assert {n["label"] for n in g["nodes"] if n["kind"] == "symptom"} == {"Chest pain", "Breathlessness"}
    g = cg.build(["headache"], ["Condition beta"])
    e = next(e for e in g["edges"] if e["from"] == "symptom:headache")
    assert e["dashes"] and e["fact"] is None


def test_next_depth_skips_empty_levels_and_wraps():
    g = cg.build([], ["Condition beta"])
    assert g["levels"]["Condition beta"] == [4]               # no phases, no therapy
    assert cg.next_depth(2, [4]) == 4
    assert cg.next_depth(4, [4]) == 2
    assert cg.next_depth(2, [3, 4, 5]) == 3


def test_symptoms_in_text():
    assert cg.symptoms_in_text("A man with crushing chest pain and fever", ["Condition alpha"]) == ["Chest pain"]
