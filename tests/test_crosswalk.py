import json

import pytest

from rag import crosswalk as cw


def _reset(monkeypatch, path):
    monkeypatch.setattr(cw, "PATH", path)
    for f in (cw._records, cw._by_label, cw._by_bodhi):
        f.cache_clear()


def _row(**kw):
    base = {"ont_id": "o1", "ont_label": "Migraine", "ont_type": "PathologicalCondition", "bodhi_id": "b1",
            "bodhi_ids": ["b1", "b1x"], "bodhi_name": "Migraine", "bodhi_type": "Condition", "relation": "exact",
            "score": 1.0, "method": "name_key", "checked": True, "tier": "T2", "note": ""}
    return {**base, **kw}


@pytest.fixture
def data(tmp_path, monkeypatch):
    p = tmp_path / "crosswalk.jsonl"
    rows = [_row(),
            _row(ont_id="o2", ont_label="Acute asthma", bodhi_id="b2", bodhi_ids=["b2"], bodhi_name="Asthma",
                 relation="broader", score=0.9, method="embedding+llm", checked=False, tier="T3"),
            _row(ont_id="o3", ont_label="Fever", ont_type="ClinicalPhenotype", bodhi_id="b3", bodhi_ids=["b3"],
                 bodhi_name="Fever", bodhi_type="Condition", relation="related", checked=True, tier="T3",
                 note="typing mismatch")]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    _reset(monkeypatch, p)
    yield
    _reset(monkeypatch, cw.PATH)


def test_missing_file_returns_empty(tmp_path, monkeypatch):
    _reset(monkeypatch, tmp_path / "nope.jsonl")
    assert cw.bodhi_for("Migraine") == [] and cw.ontology_for("b1") == []
    _reset(monkeypatch, cw.PATH)


def test_default_is_exact_only(data):
    assert [r["bodhi_id"] for r in cw.bodhi_for("migraine")] == ["b1"]
    assert cw.bodhi_for("Acute asthma") == []
    assert cw.bodhi_for("Acute asthma", relations=("broader",))[0]["tier"] == "T3"


def test_ontology_for_by_any_variant_id_or_name(data):
    assert cw.ontology_for("b1x")[0]["ont_label"] == "Migraine"
    assert cw.ontology_for("MIGRAINE")[0]["ont_id"] == "o1"
    assert cw.trusted_labels("b1") == ["Migraine"]
    assert cw.trusted_labels("b2") == []          # broader links never feed facts


def test_typing_mismatch_is_related_never_exact(data):
    assert cw.bodhi_for("Fever") == []
    r = cw.bodhi_for("Fever", relations=("related",))[0]
    assert r["tier"] == "T3" and "mismatch" in r["note"]


def test_tier_rule():
    assert cw.tier_of("exact", True) == "T2"
    assert cw.tier_of("exact", False) == "T3" and cw.tier_of("related", True) == "T3"


def test_normalisation():
    assert cw.norm_name("Presbyopia (disorder)") == cw.norm_name("presbyopia")
    assert cw.norm_name("Thyroid-stimulating hormone (TSH)") == cw.norm_name("Thyroid stimulating hormone")
    assert cw.norm_name("Pneumonia (community-acquired)") != cw.norm_name("Pneumonia")
    assert cw.token_key("Medullary carcinoma of the thyroid") == cw.token_key("Medullary thyroid carcinoma")
    assert cw.token_key("Acute asthma") != cw.token_key("Asthma")
    assert cw.token_key("Diabetes mellitus type 1") != cw.token_key("Diabetes mellitus type 2")


def test_kind_compatibility():
    assert cw.kinds_compatible("PathologicalCondition", "Concept")
    assert cw.kinds_compatible("ClinicalPhenotype", "Symptom")
    assert not cw.kinds_compatible("ClinicalPhenotype", "Condition")
    assert not cw.kinds_compatible("PathologicalCondition", "Symptom")


def test_real_file_invariants():
    if not cw.PATH.exists():
        pytest.skip("crosswalk not built")
    for r in cw._records():
        if r["relation"] == "exact":
            assert cw.kinds_compatible(r["ont_type"], r["bodhi_type"])
        assert r["tier"] == cw.tier_of(r["relation"], r["checked"])
