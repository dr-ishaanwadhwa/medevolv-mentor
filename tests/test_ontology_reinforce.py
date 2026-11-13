"""Entity merges, multi-source facts, verifier demotion, contradictions, gold scoring (synthetic, no LLM)."""
from ontology.compiler import merge_duplicates
from ontology.gold import score
from ontology.merge import apply_merges, merge_key, plan_merges
from ontology.schema import ClinicalProvenance, ClinicalRelation as R, EntityType as T, ProvenancedOntologyFact
from ontology.verifier import apply_verdicts, verdict_key
from rag import ontology_facts


def fact(s, p, o, book="harrison", quote="q", st=T.PathologicalCondition, ot=T.TherapeuticAgent, line=None,
         sid=None, oid=None, status="CERTIFIED"):
    return ProvenancedOntologyFact(
        id=f"{s}{p}{o}{book}", subject_id=sid or f"MED:OKF/{st.value.lower()}/{s.lower()}", subject_label=s,
        subject_type=st, predicate=p, object_id=oid or f"MED:OKF/{ot.value.lower()}/{o.lower()}", object_label=o,
        object_type=ot, status=status, clinical_facets={"line_of_therapy": line},
        provenance=ClinicalProvenance(book_id=book, book_title=book, chapter="1", section_id=f"{book}/x",
                                      verbatim_quote=quote), nl_fact="x")


def test_merge_key_spellings():
    assert merge_key("Graves’ disease") == merge_key("Graves disease") == merge_key("graves' disease")
    assert merge_key("Deep-venous thrombosis") == merge_key("Deep venous thrombosis")
    assert merge_key("Glucocorticoids") == merge_key("Glucocorticoid")
    assert merge_key("Arteries") == merge_key("Artery")
    # not merged: different concepts, and words that only look plural
    assert merge_key("Asthma") != merge_key("Acute asthma")
    assert merge_key("Pneumocystis") == "pneumocystis" and merge_key("Diabetes insipidus") == "diabetes insipidus"


def test_plural_and_drug_type_merges():
    fs = [fact("Asthma", R.TREATED_BY, "Glucocorticoids"), fact("Asthma", R.TREATED_BY, "Glucocorticoid", book="davidson"),
          fact("Colitis", R.CAUSED_BY, "Vancomycin", ot=T.EtiologicalAgent),
          fact("Sepsis", R.TREATED_BY, "Vancomycin"), fact("Endocarditis", R.TREATED_BY, "Vancomycin")]
    mapping, report = plan_merges(fs)
    out = apply_merges(fs, mapping)
    assert out[0].object_id == out[1].object_id                      # plural joined
    assert out[2].object_type == T.TherapeuticAgent and out[2].object_id == out[3].object_id
    merged = merge_duplicates(out)
    gluco = [f for f in merged if f.subject_label == "Asthma"]
    assert len(gluco) == 1 and {p.book_id for p in gluco[0].sources} == {"harrison", "davidson"}


def test_minor_drug_use_does_not_retype_an_agent():
    fs = [fact("Lung cancer", R.CAUSED_BY, "Tobacco", ot=T.EtiologicalAgent),
          fact("COPD", R.CAUSED_BY, "Tobacco", ot=T.EtiologicalAgent), fact("X", R.TREATED_BY, "Tobacco")]
    out = apply_merges(fs, plan_merges(fs)[0])
    assert out[0].object_type == T.EtiologicalAgent


def test_verifier_only_demotes():
    good = fact("Malaria", R.TREATED_BY, "Artesunate", quote="good")
    two = merge_duplicates([fact("Gout", R.TREATED_BY, "Colchicine", quote="bad"),
                            fact("Gout", R.TREATED_BY, "Colchicine", book="davidson", quote="fine")])[0]
    bad = fact("Infection", R.TREATED_BY, "Nitrofurantoin", quote="adverse effects table")
    k = lambda f, q: verdict_key(f.subject_label, f.predicate.value, f.object_label, q)
    cache = {k(good, "good"): "yes", k(two, "bad"): "no", k(two, "fine"): "partial", k(bad, "adverse effects table"): "no"}
    g, t, b = apply_verdicts([good, two, bad], cache)
    assert g.status == "CERTIFIED" and g.llm_check == "yes"
    assert t.status == "CERTIFIED" and [p.verbatim_quote for p in t.sources] == ["fine"] and t.provenance.verbatim_quote == "fine"
    assert b.status == "CANDIDATE"


def test_contradictions_and_corroboration(monkeypatch):
    fs = [fact("Zeta fever", R.TREATED_BY, "DrugA", line="FIRST_LINE"),
          fact("Zeta fever", R.TREATED_BY, "DrugB", book="davidson", line="FIRST_LINE"),
          fact("Zeta fever", R.CONTRAINDICATES, "DrugA", book="tripathi"),
          *merge_duplicates([fact("Zeta fever", R.MANIFESTS_AS, "Rash", ot=T.ClinicalPhenotype),
                             fact("Zeta fever", R.MANIFESTS_AS, "Rash", ot=T.ClinicalPhenotype, book="micro")])]
    dicts = tuple(f.model_dump(mode="json") for f in fs)
    monkeypatch.setattr(ontology_facts, "facts", lambda: dicts)
    kinds = sorted(c["kind"] for c in ontology_facts._contradictions())
    assert kinds == ["first_line_differs", "treated_and_contraindicated"]
    assert all(c["note"] == ontology_facts.DIFFER_NOTE for c in ontology_facts._contradictions())
    rash = [d for d in dicts if d["object_label"] == "Rash"][0]
    assert ontology_facts.corroboration(rash) == 2 and ontology_facts.books(rash) == ["harrison", "micro"]


def test_gold_score():
    facts = [{"subject_label": "TB", "predicate": "TREATED_BY", "object_label": "Isoniazid"},
             {"subject_label": "TB", "predicate": "TREATED_BY", "object_label": "Aspirin"}]
    gold = [{"condition": "TB", "predicate": "TREATED_BY", "object": "isoniazid", "expected": True},
            {"condition": "TB", "predicate": "TREATED_BY", "object": "Rifampicin", "expected": True},
            {"condition": "TB", "predicate": "TREATED_BY", "object": "Aspirin", "expected": False}]
    s = score(facts, gold)
    assert s["precision"] == 0.5 and s["recall"] == 0.5 and len(s["wrong_still_present"]) == 1


def test_british_and_inn_names_merge():
    assert merge_key("Salbutamol") == merge_key("albuterol")
    assert merge_key("Rifampicin") == merge_key("Rifampin")
    assert merge_key("Haemorrhagic fever") == merge_key("Hemorrhagic fever")
    assert merge_key("Oesophageal varices") == merge_key("Esophageal varix") or merge_key("Oesophageal varices") == merge_key("Esophageal varices")


def test_gold_split_is_fixed_and_balanced():
    from ontology.gold import load_gold, split_of
    gold = load_gold()
    halves = [split_of(g) for g in gold]
    assert set(halves) == {"dev", "heldout"} and abs(halves.count("dev") - halves.count("heldout")) < len(gold) * 0.2
    assert split_of(gold[0]) == split_of(dict(gold[0]))


def test_gapfill_passages_come_from_the_named_condition():
    import pytest
    from pathlib import Path
    if not Path("data/okf/harrison/sections").exists():
        pytest.skip("corpus not present")
    from ontology.gapfill import find_passages
    found = find_passages(["myasthenia gravis", "myasthenia"])
    assert found and all(len(p.split()) <= 1500 for _, p in found)
    assert any("myasthenia" in path.name for path, _ in found)


def test_contraindication_qualifiers():
    from ontology.reconciler import REGIMEN_OBJECT, qualify_contraindication as q
    # a named subtype becomes the subject
    assert q("Tuberculosis", "Corticosteroids are contraindicated in intestinal tuberculosis because perforation")[0] \
        == "Intestinal tuberculosis"
    # a population keeps the subject and is recorded
    s, pop = q("Tuberculosis", "S is contraindicated because it is ototoxic to the foetus.")
    assert s == "Tuberculosis" and "pregnan" in pop
    assert "HIV" in q("Tuberculosis", "not recommended in patients infected with HIV")[1]
    # no qualifier: unchanged; 'patients with <the subject>' and its acronym are not qualifiers
    assert q("Asthma", "Beta blockers are contraindicated in asthma") == ("Asthma", None)
    assert q("Myocardial infarction", "avoided in patients with acute myocardial infarction")[1] is None
    assert q("ST-Segment Elevation Myocardial Infarction", "should be avoided in patients with STEMI.")[1] is None
    # items of one list are separate contraindications, not qualifiers
    assert q("Epilepsy", "contraindicated in epilepsy, depression, renal insufficiency.")[1] is None
    # a chapter about pregnancy qualifies its warnings
    assert q("Heart disease", "Drug X should be avoided.", context="30 Maternal medicine")[1]
    assert q("Renal insufficiency", "Metformin should not be used in renal insufficiency.")[1] is None
    assert REGIMEN_OBJECT.search("Twice-weekly treatment regimens") and not REGIMEN_OBJECT.search("Streptomycin")
    from ontology.reconciler import ineffective_only
    assert ineffective_only("Group V drugs with uncertain efficacy; not recommended for MDR-TB")
    assert not ineffective_only("Ineffective and may precipitate seizures")


def test_warning_wording_is_neutral(monkeypatch):
    f = {"subject_id": "s", "object_id": "o", "subject_label": "Tuberculosis", "object_label": "Streptomycin",
         "clinical_facets": {"contraindication_severity": "CAUTIONARY", "population": "the patient is pregnant",
                             "rationale": None}}
    monkeypatch.setattr(ontology_facts, "_treats", lambda: frozenset())
    assert ontology_facts.warning_text(f) == "Streptomycin is contraindicated in Tuberculosis when the patient is pregnant"
    monkeypatch.setattr(ontology_facts, "_treats", lambda: frozenset({("s", "o")}))
    g = dict(f, clinical_facets=dict(f["clinical_facets"], population=None, contraindication_severity="STRICT"))
    assert "strictly" not in ontology_facts.warning_text(g) and ontology_facts.DIFFER_NOTE in ontology_facts.warning_text(g)


def test_ci_triage_only_softens_or_hides(tmp_path):
    import json
    from ontology.verifier import apply_ci_triage
    a = fact("Renal impairment", R.CONTRAINDICATES, "Metformin", quote="qa")
    b = fact("Gonorrhea", R.CONTRAINDICATES, "Fluoroquinolones", quote="qb")
    c = fact("Asthma", R.CONTRAINDICATES, "Timolol", quote="qc")
    for f in (a, b, c):
        from ontology.schema import ContraindicationSeverity
        f.clinical_facets.contraindication_severity = ContraindicationSeverity.STRICT
    k = lambda f: verdict_key(f.subject_label, f.predicate.value, f.object_label, f.provenance.verbatim_quote)
    path = tmp_path / "tri.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in [{"k": k(a), "v": "qualifier", "q": "eGFR below 30"},
                                                           {"k": k(b), "v": "not_ci", "q": None},
                                                           {"k": k(c), "v": "ok", "q": None}]))
    x, y, z = apply_ci_triage([a, b, c], path)
    assert x.clinical_facets.contraindication_severity.value == "CAUTIONARY" and "eGFR" in x.clinical_facets.population
    assert y.status == "CANDIDATE" and z.clinical_facets.contraindication_severity.value == "STRICT"
