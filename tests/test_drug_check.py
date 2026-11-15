"""Post-answer patient-aware drug check: no network (chat is stubbed), works with or without the ontology file."""
import re

import pytest

from rag import drug_check as dc

RV_CASE = ("A 72-year-old man with inferior STEMI and right ventricular infarction. BP 78/50 mmHg, HR 46 bpm, "
           "clear lungs, raised JVP. He is allergic to penicillin and is taking sildenafil.")

RV_ANSWER = """**Emergency stabilization**
- Give IV fluid boluses to maintain preload [2].
- Beta blockers, ACE inhibitors and morphine are first-line in myocardial infarction [3][G1].
- Start metoprolol 25 mg orally [4].
- Aspirin 300 mg chewed and urgent reperfusion [1].

**Definitive pharmacology & contraindications**
Beta blockers should only be started once the BP recovers [3].
Avoid: beta blockers, nitrates and morphine in this hypotensive patient [G2]."""


class Plan:
    def __init__(self, graph_facts=(), conditions=()):
        self.graph_facts = list(graph_facts)
        self.conditions = list(conditions)


def test_findings_parsing():
    f = dc.patient_findings(RV_CASE)
    assert f["bp"] == (78, 50) and f["hr"] == 46 and f["age"] == 72
    assert {"hypotension", "bradycardia", "elderly"} <= f["flags"]
    assert "penicillin" in f["allergies"] and "sildenafil" in f["medications"]
    g = dc.patient_findings("A 28-year-old woman, 30 weeks of gestation, BP 190/110, pulse 120, with chronic kidney "
                            "disease and cirrhosis; sulfa allergy.")
    assert {"pregnancy", "severe_hypertension", "tachycardia", "renal_failure", "hepatic_failure"} <= g["flags"]
    assert g["trimester"] == 3 and "sulfa" in g["allergies"]
    assert dc.patient_findings("What is the mechanism of penicillin?")["flags"] == set()
    assert dc.patient_findings("No known drug allergies.")["allergies"] == []


def test_rv_infarct_conflicts_found():
    avoid = dc.avoid_set(RV_ANSWER, Plan(), dc.patient_findings(RV_CASE))
    assert {"beta blocker", "morphine", "nitrate"} <= set(avoid)
    found = dc.conflicts(RV_ANSWER, avoid)
    drugs = {c["key"] for c in found}
    assert {"beta blocker", "morphine"} <= drugs
    sents = {c["sentence"] for c in found}
    assert any("first-line" in s for s in sents)
    # the Avoid line itself and the caveat sentence are never flagged; fluids and aspirin are not avoided
    assert not any(s.startswith("Avoid") or "only be started once" in s for s in sents)
    assert not any("Aspirin" in s or "fluid" in s for s in sents)


def test_metoprolol_matched_via_class():
    avoid = dc.avoid_set("Avoid: beta-blockers here [G1].", Plan(), {"flags": set()})
    found = dc.conflicts("Start metoprolol 25 mg [2].\nAvoid: beta-blockers here [G1].", avoid)
    assert [c["drug"] for c in found] == ["metoprolol"]


def test_negated_sentences_not_flagged():
    avoid = {"beta blocker": "x", "morphine": "x"}
    text = ("Beta blockers are contraindicated in this patient [1]. Do not give morphine [2]. "
            "Morphine only after stabilisation [3]. Beta blockers are not for this patient [4].")
    assert dc.conflicts(text, avoid) == []


def test_warning_fact_and_allergy_feed_avoid_only_when_relevant():
    plan = Plan(graph_facts=["WARNING (textbook ontology): Beta blockers is contraindicated in Myocardial infarction: "
                             "Avoid in heart failure, hypotension, or bradycardia (Harrison, p. 1)."])
    assert "beta blocker" in dc.avoid_set("", plan, dc.patient_findings("BP 80/50"))
    assert "beta blocker" not in dc.avoid_set("", plan, dc.patient_findings("BP 130/80, HR 80"))
    found = dc.conflicts("Give amoxicillin 1 g [2].", dc.avoid_set("", Plan(), dc.patient_findings(RV_CASE)))
    assert found and found[0]["drug"] == "amoxicillin"


def test_revise_fallback_when_rewrite_adds_citation(monkeypatch):
    import rag.backends
    calls = []

    def fake_chat(system, user, **kw):
        calls.append(kw.get("temperature"))
        return RV_ANSWER.replace("[4]", "[4][9]")            # sneaks in a new citation -> rejected
    monkeypatch.setattr(rag.backends, "chat", fake_chat)
    avoid = dc.avoid_set(RV_ANSWER, Plan(), dc.patient_findings(RV_CASE))
    found = dc.conflicts(RV_ANSWER, avoid)
    new, how = dc.revise(RV_ANSWER, found, Plan(), avoid)
    assert calls == [0] and how == "drop"
    assert "[9]" not in new and "metoprolol" not in new and "first-line" not in new
    assert "Aspirin 300 mg" in new and "Avoid: beta blockers" in new and "fluid boluses" in new
    assert dc.conflicts(new, avoid) == []


def test_revise_accepts_valid_rewrite_and_drops_leftovers(monkeypatch):
    import rag.backends
    fixed = RV_ANSWER.replace("- Beta blockers, ACE inhibitors and morphine are first-line in myocardial infarction "
                              "[3][G1].", "- ACE inhibitors are first-line in myocardial infarction [3][G1].")
    monkeypatch.setattr(rag.backends, "chat", lambda *a, **k: fixed)   # leaves the metoprolol sentence in
    avoid = dc.avoid_set(RV_ANSWER, Plan(), dc.patient_findings(RV_CASE))
    new, how = dc.revise(RV_ANSWER, dc.conflicts(RV_ANSWER, avoid), Plan(), avoid)
    assert how == "rewrite+drop" and "metoprolol" not in new and "ACE inhibitors are first-line" in new
    assert dc.conflicts(new, avoid) == []


def test_check_never_adds_drugs_or_citations(monkeypatch):
    import rag.backends
    monkeypatch.setattr(rag.backends, "chat", lambda *a, **k: RV_ANSWER + "\nAlso give dobutamine [G7].")
    new = dc.check(RV_CASE, RV_ANSWER, Plan())
    cites = lambda t: set(re.findall(r"\[(G?\d+)\]", t))
    assert cites(new) <= cites(RV_ANSWER)
    assert set(dc.drug_terms(new)) <= set(dc.drug_terms(RV_ANSWER))
    assert "dobutamine" not in new.lower()


def test_no_conflict_means_no_chat(monkeypatch):
    import rag.backends
    monkeypatch.setattr(rag.backends, "chat", lambda *a, **k: pytest.fail("chat called"))
    text = "Give aspirin [1].\nAvoid: nitrates [G1]."
    assert dc.check("BP 80/50", text, Plan()) == text


def _stub_pipeline(monkeypatch, answer_text):
    import rag.answer as A
    import rag.hops as H
    plan = H.Plan(route="case", graph_facts=["Textbook ontology: something (Harrison, p. 1)."] * 2)
    monkeypatch.setattr(H, "plan", lambda q: plan)
    monkeypatch.setattr(A, "chat", lambda *a, **k: answer_text)
    return A


def test_flag_off_answer_unchanged(monkeypatch):
    A = _stub_pipeline(monkeypatch, RV_ANSWER)
    monkeypatch.setattr(A.config, "DRUG_CHECK", False)
    res = A.answer_multihop(RV_CASE.replace("He is", "Patient is"))
    assert res.text == RV_ANSWER


def test_flag_on_fixes_answer_and_recomputes_citations(monkeypatch):
    import rag.backends
    A = _stub_pipeline(monkeypatch, RV_ANSWER)
    monkeypatch.setattr(A.config, "DRUG_CHECK", True)
    monkeypatch.setattr(rag.backends, "chat", lambda *a, **k: "")          # unusable rewrite -> drop
    res = A.answer_multihop(RV_CASE.replace("He is", "Patient is"))
    assert "metoprolol" not in res.text and "Avoid: beta blockers" in res.text
    assert res.graph_cited == [2]                                        # G1 was only in a dropped sentence
