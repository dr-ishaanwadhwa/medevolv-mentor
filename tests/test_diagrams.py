"""Clinical diagrams (synthetic ontology; no textbook text, no LLM or network calls)."""
import json
import re

import pytest

from rag import diagrams, ontology_facts as onto


def fact(i, subj, pred, obj, stype="PathologicalCondition", otype="TherapeuticAgent", status="CERTIFIED", **facets):
    return {"id": f"f{i}", "subject_label": subj, "subject_type": stype, "predicate": pred, "object_label": obj,
            "object_type": otype, "status": status, "nl_fact": f"{subj} {pred} {obj}.",
            "clinical_facets": {"line_of_therapy": None, "contraindication_severity": None, **facets},
            "provenance": {"book_id": "bookA", "book_title": "Book A", "chapter": "1. Ch", "pages": [10],
                           "verbatim_quote": "synthetic"}}


FACTS = [
    fact(1, "Synthetic fever", "MANIFESTS_AS", "Chills", otype="ClinicalPhenotype"),
    fact(2, "Synthetic fever", "CONFIRMED_BY", "Blood culture", otype="DiagnosticModality"),
    fact(3, "Synthetic fever", "TREATED_BY", "Drugamycin", line_of_therapy="FIRST_LINE"),
    fact(4, "Synthetic fever", "TREATED_BY", "Secondol", line_of_therapy="SECOND_LINE"),
    fact(5, "Synthetic fever", "CONTRAINDICATES", "Badrug", contraindication_severity="STRICT"),
    fact(6, "Synthetic fever", "DIFFERENTIAL_OF", 'Mimic "X" fever', otype="PathologicalCondition"),
    fact(7, "Synthetic fever", "TREATED_BY", "Unverifiedol", status="CANDIDATE", line_of_therapy="FIRST_LINE"),
    fact(8, "Drugamycin", "TARGETS_MECHANISM", "Ribosome 30S", stype="TherapeuticAgent", otype="MolecularTarget"),
    fact(9, "Drugamycin", "CAUSES_ADVERSE_EFFECT", "Ototoxicity", stype="TherapeuticAgent", otype="ClinicalPhenotype"),
    fact(10, "Kidney failure", "CONTRAINDICATES", "Drugamycin", contraindication_severity="STRICT"),
]
HEADINGS = {"Presentation", "Differentials to exclude", "Workup / confirmation", "Treatment", "First line",
            "Second line", "Adjunct", "Refractory", "Supportive", "⚠ Contraindicated", "⚠ Use with caution",
            "Acts on (mechanism)", "Used to treat", "Adverse effects", "⚠ Contraindicated in"}


@pytest.fixture(autouse=True)
def synthetic(tmp_path, monkeypatch):
    p = tmp_path / "onto.jsonl"
    p.write_text("\n".join(json.dumps(f) for f in FACTS), encoding="utf-8")
    monkeypatch.setattr(onto, "PATH", p)
    monkeypatch.setattr(diagrams, "CACHE_DIR", tmp_path / "cache")
    for fn in (onto.facts, onto._counts, onto.condition_labels):
        fn.cache_clear()
    yield
    for fn in (onto.facts, onto._counts, onto.condition_labels):
        fn.cache_clear()


def box_labels(dot):
    """Every node label in the DOT, with the [n] source marker and line wraps removed."""
    out = []
    for raw in re.findall(r'\[label="((?:[^"\\]|\\.)*)"', dot):
        text = re.sub(r"\s*\[\d+\]$", "", raw.replace("\\n", " ")).replace('\\"', '"')
        out.append(text)
    return out


def test_case_flowchart_uses_only_certified_facts():
    dg = diagrams.build("A patient with synthetic fever: workup and management?")
    assert dg["kind"] == "case" and dg["subject"] == "Synthetic fever"
    certified = {f["object_label"] for f in FACTS if f["status"] == "CERTIFIED"} | {"Synthetic fever"}
    for label in box_labels(dg["dot"]):
        assert label in certified or label in HEADINGS, label        # nothing invented
    assert "Unverifiedol" not in dg["dot"]                            # CANDIDATE facts never drawn
    assert "Badrug" in dg["dot"] and "#c53030" in dg["dot"]           # contraindication drawn as a red warning
    # every numbered box has a source with a citation
    assert {s["n"] for s in dg["sources"]} == {int(n) for n in re.findall(r"\[(\d+)\]\"", dg["dot"])}
    assert all(s["cite"].startswith("Book A") for s in dg["sources"])


def test_symptom_label_does_not_beat_the_disease():
    # "Chills" is also a condition label (with no workup/treatment facts); the disease must win
    extra = fact(11, "Chills", "MANIFESTS_AS", "Shivering", otype="ClinicalPhenotype")
    onto.PATH.write_text(onto.PATH.read_text() + "\n" + json.dumps(extra), encoding="utf-8")
    for fn in (onto.facts, onto._counts, onto.condition_labels):
        fn.cache_clear()
    assert diagrams.find_condition("Chills and weight loss: how is synthetic fever treated?") == "Synthetic fever"


def test_quotes_in_labels_are_escaped():
    dot = diagrams.build("synthetic fever?")["dot"]
    assert 'Mimic \\"X\\" fever' in dot


def test_pharmacology_question_gives_mechanism_diagram():
    dg = diagrams.build("What is the mechanism of action of drugamycin?")
    assert dg["kind"] == "drug"
    for want in ("Ribosome 30S", "Ototoxicity", "Synthetic fever", "Kidney failure"):
        assert want in dg["dot"]


def test_answer_mentions_are_bold():
    dot = diagrams.build("synthetic fever management?", answer_text="Start drugamycin.", use_cache=False)["dot"]
    assert re.search(r'label="Drugamycin \[\d+\]"[^\]]*penwidth="2.5"', dot)


def test_no_diagram_when_nothing_to_draw():
    assert diagrams.build("What is the capital of France?") is None


def test_missing_ontology_degrades_to_none(tmp_path, monkeypatch):
    monkeypatch.setattr(onto, "PATH", tmp_path / "absent.jsonl")
    onto.facts.cache_clear()
    assert diagrams.build("synthetic fever?") is None


def test_errors_never_escape(monkeypatch):
    monkeypatch.setattr(diagrams, "case_flowchart", lambda *a, **k: 1 / 0)
    assert diagrams.build("synthetic fever?", use_cache=False) is None


def test_cached_on_disk():
    first = diagrams.build("synthetic fever?")
    files = list(diagrams.CACHE_DIR.glob("*.json"))
    assert len(files) == 1
    files[0].write_text(json.dumps({**first, "dot": "cached"}), encoding="utf-8")
    assert diagrams.build("synthetic fever?")["dot"] == "cached"


class FakeSt:
    def __init__(self, click):
        self.session_state, self.click, self.charts = {}, click, []

    def button(self, *a, **k):
        return self.click

    def graphviz_chart(self, dot, **k):
        self.charts.append(dot)

    def expander(self, *a, **k):
        import contextlib
        return contextlib.nullcontext()

    def markdown(self, *a, **k):
        pass


def test_render_is_on_demand():
    idle = FakeSt(click=False)
    diagrams.render(idle, "synthetic fever?")
    assert idle.charts == []                       # nothing drawn until the button is pressed
    clicked = FakeSt(click=True)
    diagrams.render(clicked, "synthetic fever?")
    assert len(clicked.charts) == 1 and clicked.session_state["diagram_open"]
    nothing = FakeSt(click=True)
    diagrams.render(nothing, "capital of France?")  # no subject: no button, no chart, no error
    assert nothing.charts == []
