"""A general first-line list must flag drugs the books also contraindicate for some patients with the condition,
so a hypotensive MI patient is never told 'beta blockers are first-line' without the caveat."""
import pytest
from rag import ontology_facts as o


def test_inn_stem_classes():
    assert "Beta blockers" in o.drug_classes("Metoprolol")
    assert "ACE inhibitors" in o.drug_classes("Enalapril")
    assert o.drug_classes("Aspirin") == ()


@pytest.mark.skipif(not o.available(), reason="ontology file not built")
def test_mi_first_line_carries_beta_blocker_caveat(monkeypatch):
    monkeypatch.setattr(o, "FIRST_LINE_CAVEAT", True)
    line = next(l for l in o.graph_facts_for("Myocardial infarction") if "first-line" in l)
    assert "in general" in line
    for chunk in line.split(";"):
        if any(c in o.drug_classes(chunk.split("(")[0].strip()) for c in ("Beta blockers",)) or "beta blocker" in chunk.lower():
            assert "not for every patient" in chunk


@pytest.mark.skipif(not o.available(), reason="ontology file not built")
def test_caveat_off_by_default_keeps_live_wording(monkeypatch):
    monkeypatch.setattr(o, "FIRST_LINE_CAVEAT", False)
    line = next(l for l in o.graph_facts_for("Myocardial infarction") if "first-line" in l)
    assert "in general" not in line and "not for every patient" not in line
