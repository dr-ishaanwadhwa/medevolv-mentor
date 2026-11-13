"""Dry-run planner for Gray's anatomy relations (scripts/plan_anatomy_relations.py): no spend, and the guard rules
that correct the 'coronary artery PART_OF ascending aorta' error in the v2 plan."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, "scripts")
import plan_anatomy_relations as p  # noqa: E402


def test_coronary_artery_is_a_branch_not_a_part():
    assert p.guard_triple("PART_OF", "Coronary artery", "Ascending aorta")[0] == "drop"
    assert p.guard_triple("BRANCH_OF", "Right coronary artery", "Ascending aorta")[0] == "ok"
    assert p.guard_triple("PART_OF", "Ascending aorta", "Aorta")[0] == "ok"          # a segment is a part
    assert p.guard_triple("BRANCH_OF", "Ulnar nerve", "Medial cord")[0] == "ok"


def test_guard_rules_organs_systems_and_families():
    assert p.guard_triple("PART_OF", "Heart", "Cardiovascular system")[0] == "ok"
    assert p.guard_triple("PART_OF", "Cardiovascular system", "Heart")[0] == "drop"
    assert p.guard_triple("BRANCH_OF", "Heart", "Aorta")[0] == "drop"                # organs do not branch
    assert p.guard_triple("BRANCH_OF", "Radial artery", "Median nerve")[0] == "drop"  # across families
    assert p.guard_triple("INNERVATED_BY", "Diaphragm", "Phrenic nerve")[0] == "ok"
    assert p.guard_triple("INNERVATED_BY", "Diaphragm", "Phrenic artery")[0] == "drop"
    assert p.guard_triple("SUPPLIED_BY", "Femoral head", "Obturator artery", "bone", "artery")[0] == "ok"
    assert p.guard_triple("DRAINED_BY", "Rectum", "Superior rectal vein")[0] == "ok"
    assert p.guard_triple("CONTAINS", "Inguinal canal", "Spermatic cord", "space", "organ")[0] == "ok"
    assert p.guard_triple("CONTAINS", "Phrenic nerve", "Inguinal canal", "nerve", "space")[0] == "drop"


def test_every_proposed_predicate_has_inverse_wording():
    for pred, (_, _, reads, inverse) in p.PROPOSED_PREDICATES.items():
        assert reads and inverse, pred


def test_dry_run_makes_no_llm_call_and_matches_prices(monkeypatch):
    if not Path("data/okf/grays/sections").exists():
        pytest.skip("corpus not on this machine")
    from rag import backends
    monkeypatch.setattr(backends, "chat", lambda *a, **k: (_ for _ in ()).throw(AssertionError("LLM called in a dry run")))
    from ontology import gapfill
    assert p.PRICES["repo_assumed (ontology/gapfill.py, verifier.py)"] == (gapfill.PRICE_IN, gapfill.PRICE_OUT)
    c = p.stage_c(p.passages())
    assert 0 < c["passages_targeted"] <= c["passages_total"] and c["sections_targeted"] <= c["sections_total"]
    assert all(v < 10 for row in c["cost_usd"].values() for r in row.values() for v in r.values())   # order of magnitude: dollars
    assert p.stage_b()["entity_headings"] >= 0
