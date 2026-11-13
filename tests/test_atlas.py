"""rag.atlas: ontology structure -> 3D atlas links. Navigation only; hidden when ATLAS_URL is unset."""
import json

import pytest

from rag import atlas, config
from rag import ontology_facts as onto


def _fact(cond, struct, predicate="INVOLVES_STRUCTURE", status="CERTIFIED"):
    return {"subject_label": cond, "subject_type": "PathologicalCondition", "predicate": predicate,
            "object_label": struct, "object_type": "AnatomicalStructure", "status": status}


@pytest.fixture
def wired(tmp_path, monkeypatch):
    rows = [{"label": "Right coronary artery", "key": atlas.name_key("Right coronary artery"), "atlas_id": "FMA50050",
             "atlas_name": "right coronary artery", "method": "exact", "score": 1.0},
            {"label": "Bladder", "key": atlas.name_key("Bladder"), "atlas_id": "FMA15900",
             "atlas_name": "urinary bladder", "method": "embedding+llm", "score": 0.84}]
    p = tmp_path / "atlas_crosswalk.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(atlas, "PATH", p)
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(onto, "facts", lambda: (
        _fact("Aortic dissection", "Right coronary artery"), _fact("Aortic dissection", "Intima"),
        _fact("Aortic dissection", "Bladder", status="CERTIFIED"),
        _fact("Cystitis", "Bladder", predicate="TREATED_BY")))
    atlas.links.cache_clear()
    atlas._involves.cache_clear()
    yield
    atlas.links.cache_clear()
    atlas._involves.cache_clear()


def test_atlas_link_matches_normalised_names(wired):
    assert atlas.atlas_link("right coronary artery") == "https://atlas.example/?select=FMA50050"
    assert atlas.atlas_link("The Right Coronary Arteries") == "https://atlas.example/?select=FMA50050"
    assert atlas.atlas_link("Intima") is None


def test_name_key_ignores_the():
    assert atlas.name_key("Surgical neck of the humerus") == atlas.name_key("surgical neck of humerus")


def test_structures_for_goes_through_involves_structure_only(wired):
    got = atlas.structures_for("Aortic dissection")
    assert [g["label"] for g in got] == ["Right coronary artery", "Bladder"]      # Intima has no atlas concept
    assert got[1]["atlas_name"] == "urinary bladder"
    assert atlas.structures_for("Cystitis") == []                                 # other predicates make no link
    assert atlas.structures_for("Unknown condition") == []


def test_hidden_when_atlas_url_unset(wired, monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "")
    assert atlas.atlas_link("Bladder") is None
    assert atlas.structures_for("Aortic dissection") == []
    assert not atlas.enabled()


def test_missing_crosswalk_file(tmp_path, monkeypatch):
    monkeypatch.setattr(atlas, "PATH", tmp_path / "nope.jsonl")
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    atlas.links.cache_clear()
    assert atlas.atlas_link("Bladder") is None
    atlas.links.cache_clear()


def test_url_is_escaped(wired):
    assert atlas.url_for("a b&c") == "https://atlas.example/?select=a%20b%26c"
