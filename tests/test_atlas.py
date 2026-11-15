"""rag.atlas: ontology structure -> 3D atlas links. Navigation only; hidden when ATLAS_URL is unset."""
import json
from pathlib import Path

import pytest

from rag import atlas, config
from rag import ontology_facts as onto


@pytest.fixture(autouse=True)
def _no_guard_file(tmp_path, monkeypatch):
    """Default: no guard file, so only the curated overrides apply; guard tests point GUARD_PATH at their own file."""
    monkeypatch.setattr(atlas, "GUARD_PATH", tmp_path / "no_guard.jsonl")
    atlas.guard.cache_clear()
    yield
    atlas.guard.cache_clear()


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
        _fact("Example lesion", "Right coronary artery"), _fact("Example lesion", "Intima"),
        _fact("Example lesion", "Bladder", status="CERTIFIED"),
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
    got = atlas.structures_for("Example lesion")
    assert [g["label"] for g in got] == ["Right coronary artery", "Bladder"]      # Intima has no atlas concept
    assert got[1]["atlas_name"] == "urinary bladder"
    assert atlas.structures_for("Cystitis") == []                                 # other predicates make no link
    assert atlas.structures_for("Unknown condition") == []


def test_hidden_when_atlas_url_unset(wired, monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "")
    assert atlas.atlas_link("Bladder") is None
    assert atlas.structures_for("Example lesion") == []
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


def _write_guard(path, rows):
    path.write_text("".join(json.dumps({"condition": c, "label": lab, "reason": "t"}) + "\n" for c, lab in rows))
    atlas.guard.cache_clear()


def test_guard_shows_only_local_conditions(wired, tmp_path, monkeypatch):
    monkeypatch.setattr(onto, "facts", lambda: (
        _fact("Example lesion", "Bladder"), _fact("Tuberculosis", "Bladder"), _fact("Pneumonia", "Bladder"),
        _fact("Sepsis", "Bladder"), _fact("Brand new condition", "Bladder")))
    atlas._involves.cache_clear()
    p = tmp_path / "guard.jsonl"
    monkeypatch.setattr(atlas, "GUARD_PATH", p)
    _write_guard(p, [("Example lesion", "local"), ("Tuberculosis", "local"), ("Pneumonia", "multi_site"),
                     ("Sepsis", "systemic")])
    assert [g["label"] for g in atlas.structures_for("Example lesion")] == ["Bladder"]
    assert atlas.structures_for("Tuberculosis") == []            # curated override beats a 'local' row in the file
    assert atlas.structures_for("Pneumonia") == []
    assert atlas.structures_for("Sepsis") == []
    assert atlas.structures_for("Brand new condition") == []     # not classified: hidden
    assert atlas.atlas_link("Bladder")                           # structure pages keep their link


def test_missing_guard_file_falls_back_to_curated_list(wired, monkeypatch):
    monkeypatch.setattr(onto, "facts", lambda: (
        _fact("Example lesion", "Bladder"), _fact("Tuberculosis", "Bladder"), _fact("Hepatic cirrhosis", "Bladder")))
    atlas._involves.cache_clear()
    assert not atlas.GUARD_PATH.exists()
    assert atlas.guard() is None
    assert [g["label"] for g in atlas.structures_for("Example lesion")] == ["Bladder"]
    assert atlas.structures_for("Tuberculosis") == [] and atlas.structures_for("hepatic cirrhosis") == []


REAL = (atlas.PATH.exists() and Path("data/graph/atlas_condition_guard.jsonl").exists()
        and Path("data/ontology/clinical_ontology.jsonl").exists())


@pytest.mark.skipif(not REAL, reason="needs the built crosswalk, guard file and ontology")
def test_real_guard_on_certified_facts(monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(atlas, "GUARD_PATH", Path("data/graph/atlas_condition_guard.jsonl"))
    for f in (atlas.links, atlas.guard, atlas._involves):
        f.cache_clear()
    try:
        assert atlas.structures_for("Tuberculosis") == [] and atlas.structures_for("Pneumonia") == []
        # lesion-only: the pituitary tumour shows the gland, not the compressed chiasm; a dissection shows the aorta only
        assert [g["label"] for g in atlas.structures_for("Pituitary macroadenoma")] == ["Pituitary gland"]
        assert [g["label"] for g in atlas.structures_for("Aortic dissection")] == ["Aorta"]
        # signs shown on a denervated target muscle are hidden
        for c in ("Trendelenburg's sign", "Diaphragmatic paralysis", "Complete ptosis"):
            assert atlas.structures_for(c) == []
    finally:
        for f in (atlas.links, atlas.guard, atlas._involves):
            f.cache_clear()


@pytest.mark.skipif(not REAL, reason="needs the built crosswalk")
def test_crosswalk_synonyms_resolve(monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    atlas.links.cache_clear()
    try:
        assert atlas.atlas_record("Anterior interventricular artery")["atlas_id"] == "FMA3862"
        assert atlas.atlas_record("Iliotibial band")["atlas_id"] == "FMA51048"
    finally:
        atlas.links.cache_clear()


def test_synonym_table_has_the_two_same_structure_entries():
    import importlib.util
    spec = importlib.util.spec_from_file_location("bx", "scripts/build_atlas_crosswalk.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    t = {atlas.name_key("iliotibial tract"): {"label": "iliotibial tract", "key": "x", "atlas_id": "FMA51048",
                                               "atlas_name": "iliotibial tract"},
         atlas.name_key("anterior interventricular branch of left coronary artery"):
             {"label": "a", "key": "y", "atlas_id": "FMA3862", "atlas_name": "a"}}
    m.add_synonyms(t)
    assert t[atlas.name_key("Iliotibial band")]["atlas_id"] == "FMA51048"
    assert t[atlas.name_key("Anterior interventricular artery")]["atlas_id"] == "FMA3862"
