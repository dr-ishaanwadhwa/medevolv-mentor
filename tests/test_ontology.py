"""Ontology reconciliation rules (synthetic inputs; no textbook text, no LLM calls)."""
from ontology.normalizer import mint_uri
from ontology.reconciler import _norm, check_direction, quote_in_source
from ontology.schema import ClinicalRelation as R, EntityType as T


def test_direction_ok_swap_drop():
    assert check_direction(R.TREATED_BY, T.PathologicalCondition, T.TherapeuticAgent) == "ok"
    # "Valproate TREATED_BY Absence seizures" is reversed
    assert check_direction(R.TREATED_BY, T.TherapeuticAgent, T.PathologicalCondition) == "swap"
    # "Dengue virus CAUSED_BY Dengue fever" is reversed
    assert check_direction(R.CAUSED_BY, T.EtiologicalAgent, T.PathologicalCondition) == "swap"
    # a drug-drug interaction is not a contraindication in this schema
    assert check_direction(R.CONTRAINDICATES, T.TherapeuticAgent, T.TherapeuticAgent) == "drop"
    # an adverse effect must come from a drug
    assert check_direction(R.CAUSES_ADVERSE_EFFECT, T.PathologicalCondition, T.ClinicalPhenotype) == "drop"
    assert check_direction(R.IS_A, T.TherapeuticAgent, T.TherapeuticAgent) == "ok"
    assert check_direction(R.IS_A, T.PathologicalCondition, T.OrganSystem) == "drop"


def test_quote_must_be_in_source():
    src = _norm("Synthetic passage: the first-line agent for condition X is drug Y, given orally twice daily.")
    assert quote_in_source("the first-line agent for condition X is drug Y", src)
    assert quote_in_source("first-line agent for condition X ... given orally twice daily", src)
    assert not quote_in_source("drug Z is the first-line agent for condition X", src)   # paraphrase
    assert not quote_in_source("drug Y", src)                                           # too short to verify


def test_minted_ids_do_not_depend_on_book():
    assert mint_uri("tripathi", "Valproate", T.TherapeuticAgent) == mint_uri("harrison", "Valproate", T.TherapeuticAgent)


import pytest
from rag import ontology_facts


@pytest.mark.skipif(not ontology_facts.available(), reason="ontology file not built")
def test_condition_matching_rules():
    m = ontology_facts.match_conditions
    # a more specific, better-documented label is added (STEMI facts for acute MI) ...
    assert any("ST-Segment" in c for c in m("Acute myocardial infarction"))
    # ... but never a more general one: type 1 must not inherit plain 'diabetes mellitus' (type 2 drugs)
    assert all("1" in c for c in m("Diabetes mellitus type 1"))
    assert not m("zzz unknown condition")
    # every catalog condition has an organ system
    assert "Other" not in ontology_facts.catalog()
