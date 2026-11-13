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


@pytest.fixture
def table(tmp_path, monkeypatch):
    def rec(key, ids, name, by_side=None):
        r = {"label": key, "key": key, "atlas_id": ids[0], "atlas_name": name, "method": "atlas-name", "score": 1.0}
        if len(ids) > 1:
            r["atlas_ids"] = ids
        if by_side:
            r["by_side"] = by_side
        return r
    rows = [rec("kidney", ["FMA7203"], "kidney"), rec("scaphoid", ["FMA23709"], "scaphoid"),
            rec("head of femur", ["FMA32"], "head of femur"),
            rec("lung", ["FMA7309", "FMA7310"], "lung (left and right)", {"right": "FMA7309", "left": "FMA7310"}),
            rec("femoral artery", ["FMA2"], "femoral artery")]
    p = tmp_path / "x.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(atlas, "PATH", p)
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(onto, "facts", lambda: (
        _fact("Extradural hematoma", "Femoral artery"), _fact("Cond", "Kidneys")))
    for f in (atlas.links, atlas._involves):
        f.cache_clear()
    yield
    for f in (atlas.links, atlas._involves):
        f.cache_clear()


def test_variants_plural_category_word_and_word_order(table):
    assert atlas.atlas_link("Kidneys").endswith("FMA7203")               # merge_key keeps 'kidneys'; variants fix it
    assert atlas.atlas_link("Scaphoid bone").endswith("FMA23709")        # atlas says 'scaphoid'
    assert atlas.atlas_link("Femur head").endswith("FMA32")              # 'Y X' -> 'X of Y'
    assert atlas.atlas_link("Sacro-iliac joint") is None                 # nothing to match


def test_left_right_pair_links_both_or_one_side(table):
    assert atlas.atlas_link("Lungs") == "https://atlas.example/?select=FMA7309,FMA7310"
    assert atlas.atlas_link("Left lung") == "https://atlas.example/?select=FMA7310"
    assert atlas.atlas_link("Right lung") == "https://atlas.example/?select=FMA7309"


def test_condition_spelled_two_ways_finds_the_same_facts(table):
    assert [g["label"] for g in atlas.structures_for("Extradural hemorrhage")] == ["Femoral artery"]
    assert [g["label"] for g in atlas.structures_for("Epidural hematoma")] == ["Femoral artery"]
    assert atlas.structures_for("Subdural hematoma") == []


def test_for_section_prefers_heading_then_title_then_parents(table):
    meta = {"section_path": "Gray's › 4 Abdomen › Viscera › Kidneys › Vessels", "section_title": "Vessels"}
    got = atlas.for_section(meta)
    assert got["label"] == "Kidneys" and got["url"].endswith("FMA7203")
    assert atlas.for_section({"section_path": "G › C › Overview", "section_title": "Overview"}) is None
