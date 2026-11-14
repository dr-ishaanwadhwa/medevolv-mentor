"""Gray's normal-anatomy relations (ontology/anatomy.py): guard rules G1-G9, the reconciler gates, and the promise that
these facts never reach answers (rag/ontology_facts.py) while concept pages can show them (rag/concepts.py)."""
import json

import pytest

from ontology import anatomy
from ontology.compiler import save_compiled_facts, load_compiled_facts
from ontology.reconciler import check_direction, reconcile_section_facts
from ontology.schema import ClinicalRelation as R, EntityType as T, ExtractionItem, SectionExtractionResult
from rag import concepts, ontology_facts

SOURCE = ("The right coronary artery arises from the right aortic sinus of the ascending aorta. "
          "The diaphragm is supplied by the phrenic nerve. The ascending aorta is the first part of the aorta.")


def item(s, pred, o, quote, sk="artery", ok="artery", conf=0.95):
    return ExtractionItem(subject_name=s, subject_type=T.AnatomicalStructure, predicate=pred, object_name=o,
                          object_type=T.AnatomicalStructure, structure_kind=sk, object_structure_kind=ok,
                          verbatim_quote=quote, confidence=conf, nl_fact=f"{s} {pred.value} {o}")


def reconcile(*items, source=SOURCE):
    res = SectionExtractionResult(section_id="grays/x", book_id="grays", chapter="Thorax", triples=list(items))
    stats: dict = {}
    return reconcile_section_facts(res, {"book": "Gray's", "pages": [1]}, source_text=source, stats=stats), stats


# ---------- guard rules ----------
def test_coronary_artery_is_a_branch_not_a_part():
    assert anatomy.guard_triple("PART_OF", "Coronary artery", "Ascending aorta", "artery", "artery")[0] == "drop"      # G2
    assert anatomy.guard_triple("BRANCH_OF", "Right coronary artery", "Ascending aorta", "artery", "artery")[0] == "ok"
    assert anatomy.guard_triple("PART_OF", "Ascending aorta", "Aorta", "artery", "artery")[0] == "ok"


def test_guards_g1_g3_g4_g5_g6():
    g = anatomy.check_anatomy_kinds
    assert g("BRANCH_OF", "organ", "artery")[0] == "drop"                      # G1 organs do not branch
    assert g("BRANCH_OF", "artery", "nerve")[0] == "drop"                      # G1 same family only
    assert g("BRANCH_OF", "nerve", "nerve")[0] == "ok"
    assert g("PART_OF", "organ", "system")[0] == "ok"                          # G3
    assert g("PART_OF", "system", "organ")[0] == "drop"
    assert g("PART_OF", "artery", "organ")[0] == "review"                      # G4
    assert g("INNERVATED_BY", "muscle", "artery")[0] == "drop"                 # G5
    assert g("SUPPLIED_BY", "organ", "artery")[0] == "ok"
    assert g("DRAINED_BY", "organ", "lymphatic")[0] == "ok"
    assert g("CONTAINS", "nerve", "space")[0] == "drop"                        # G6
    assert g("BOUNDED_BY", "space", "muscle")[0] == "ok"


def test_heading_nesting_is_never_part_of():
    """The extractor only sees prose; a PART_OF whose quote has no part/segment cue is dropped (G7)."""
    it = item("Diaphragm", R.PART_OF, "Posterior abdominal wall", "The diaphragm lies in the posterior abdominal wall.", "muscle", "region")
    assert anatomy.gate_anatomy_item(it)[0] == "drop"


def test_quote_cue_and_self_relation_and_object_named():
    assert anatomy.gate_anatomy_item(item("Aorta", R.BRANCH_OF, "Aorta", "The aorta arises from the aorta."))[0] == "drop"   # G8
    assert anatomy.gate_anatomy_item(item("Radial artery", R.BRANCH_OF, "Brachial artery", "The radial artery is large."))[0] == "drop"  # G7
    assert anatomy.gate_anatomy_item(item("Radial artery", R.BRANCH_OF, "Brachial artery",
                                          "The radial artery arises from the brachial artery."))[0] == "ok"
    assert anatomy.gate_anatomy_item(item("Radial artery", R.BRANCH_OF, "Brachial artery",
                                          "The radial artery arises in the cubital fossa."))[0] == "drop"   # object not named


def test_missing_kind_is_inferred_but_never_certified():          # G9
    it = item("Phrenic nerve", R.BRANCH_OF, "Cervical plexus", "The phrenic nerve arises from the cervical plexus.", None, None)
    assert anatomy.gate_anatomy_item(it)[0] == "candidate"


def test_acyclic_part_of_and_branch_of():                          # G8 after merge
    facts, _ = reconcile(item("Right coronary artery", R.BRANCH_OF, "Ascending aorta",
                              "The right coronary artery arises from the right aortic sinus of the ascending aorta."))
    a = facts[0]
    back = a.model_copy(update={"id": "x", "subject_id": a.object_id, "subject_label": a.object_label,
                                "object_id": a.subject_id, "object_label": a.subject_label})
    assert len(anatomy.drop_cycles([a])) == 1
    assert anatomy.drop_cycles([a, back]) == []


# ---------- reconciler ----------
def test_new_predicates_have_type_rules():
    for p in anatomy.ANATOMY_PREDICATES:
        assert check_direction(p, T.AnatomicalStructure, T.AnatomicalStructure) == "ok", p
        assert check_direction(p, T.PathologicalCondition, T.AnatomicalStructure) == "drop", p
    assert check_direction(R.PART_OF, T.AnatomicalStructure, T.OrganSystem) == "ok"


def test_reconcile_certifies_branch_and_drops_part_of_coronary():
    facts, stats = reconcile(
        item("Right coronary artery", R.BRANCH_OF, "Ascending aorta",
             "The right coronary artery arises from the right aortic sinus of the ascending aorta."),
        item("Coronary artery", R.PART_OF, "Ascending aorta",
             "The ascending aorta is the first part of the aorta.", "artery", "artery"),
        item("Diaphragm", R.INNERVATED_BY, "Phrenic nerve", "The diaphragm is supplied by the phrenic nerve.", "muscle", "nerve"),
        item("Diaphragm", R.INNERVATED_BY, "Phrenic nerve", "The diaphragm is never mentioned here but phrenic nerve.", "muscle", "nerve"))
    got = {(f.subject_label, f.predicate.value, f.object_label, f.status) for f in facts}
    assert ("Right coronary artery", "BRANCH_OF", "Ascending aorta", "CERTIFIED") in got
    assert ("Diaphragm", "INNERVATED_BY", "Phrenic nerve", "CERTIFIED") in got
    assert not any(f.predicate == R.PART_OF and f.subject_label == "Coronary artery" for f in facts)
    assert stats["anatomy_dropped"] >= 1
    d = next(f for f in facts if f.predicate == R.INNERVATED_BY)
    assert d.clinical_facets.structure_kind == "muscle" and d.clinical_facets.object_structure_kind == "nerve"
    unverified = [f for f in facts if "never mentioned" in f.provenance.verbatim_quote]
    assert unverified and unverified[0].status == "CANDIDATE"          # quote not in the source


# ---------- kept out of answers, shown on concept pages ----------
def test_anatomy_relations_stay_out_of_answers(tmp_path, monkeypatch):
    facts, _ = reconcile(item("Diaphragm", R.INNERVATED_BY, "Phrenic nerve", "The diaphragm is supplied by the phrenic nerve.", "muscle", "nerve"))
    path = tmp_path / "o.jsonl"
    save_compiled_facts(facts, path=path)
    monkeypatch.setattr(ontology_facts, "PATH", path)
    ontology_facts.facts.cache_clear(); ontology_facts.anatomy_facts.cache_clear(); concepts._index.cache_clear()
    try:
        assert ontology_facts.facts() == ()
        assert len(ontology_facts.anatomy_facts()) == 1 and len(ontology_facts.all_facts()) == 1
        assert ontology_facts.graph_facts_for("Diaphragm") == [] and ontology_facts.graph_facts_for("Phrenic nerve") == []
        monkeypatch.setattr(concepts, "_heading_nav", lambda: ({}, {}, {}))
        c = concepts.concept("Phrenic nerve")
        assert c and "innervates" in json.dumps(c, default=str)
    finally:
        ontology_facts.facts.cache_clear(); ontology_facts.anatomy_facts.cache_clear(); concepts._index.cache_clear()


def test_every_anatomy_predicate_has_inverse_and_is_hidden():
    for p in anatomy.ANATOMY_PREDICATES:
        assert p.value in concepts.INVERSE, p
        assert p.value in ontology_facts.ANATOMY_PREDICATES, p
    assert {p.value for p in anatomy.ANATOMY_PREDICATES} == set(ontology_facts.ANATOMY_PREDICATES)
