"""Female atlas (PRD R5): crosswalk sex rows, deep links, /api/spatial/resolve sex handling, the id map's id shapes."""
import csv
import json
import re
import sys
from pathlib import Path

import pytest

from api import spatial
from rag import atlas, config

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_atlas_crosswalk as build  # noqa: E402

ID_MAP = Path("deploy/atlas/female/id_map.csv")
HEART = {"label": "heart", "key": "heart", "atlas_id": "FMA7088", "atlas_name": "heart", "method": "atlas-name", "score": 1.0}
UTERUS = {"label": "uterus", "key": "uterus", "atlas_id": "HRA:VH_F_UTERUS", "atlas_name": "uterus",
          "method": "female-id-map", "score": 1.0, "sex": "female", "reviewed_by": "XX"}


@pytest.fixture
def links(monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(atlas, "links", lambda: {"heart": HEART, "uterus": UTERUS})
    monkeypatch.setattr(spatial.concepts, "concept", lambda n: {})


def test_record_sex_and_urls(monkeypatch):
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example/")
    assert atlas.record_sex(HEART) == "male" and atlas.record_sex(UTERUS) == "female"
    assert atlas.record_url(HEART) == "https://atlas.example/?select=FMA7088"          # male link unchanged (F-6)
    assert atlas.record_url(UTERUS) == "https://atlas.example/?select=HRA:VH_F_UTERUS&sex=female"


def test_links_male_row_wins_a_shared_key(tmp_path, monkeypatch):
    p = tmp_path / "cw.jsonl"
    rows = [{**UTERUS, "key": "heart", "atlas_id": "HRA:VH_F_HEART"}, HEART, UTERUS]
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    monkeypatch.setattr(atlas, "PATH", p)
    atlas.links.cache_clear()
    try:
        got = atlas.links()
        assert got["heart"]["atlas_id"] == "FMA7088"
        assert got["uterus"]["sex"] == "female"
    finally:
        atlas.links.cache_clear()


def test_resolve_reports_sex(links):
    r = spatial.resolve("hra:vh_f_uterus", None, "female")          # ids from the female model, any case
    assert r["sex"] == "female" and r["fma_ids"] == ["HRA:VH_F_UTERUS"]
    assert r["atlas"][0].url.endswith("&sex=female")
    h = spatial.resolve("FMA7088", None)
    assert h["sex"] == "male" and h["atlas"][0].url == "https://atlas.example/?select=FMA7088"


def test_resolve_from_the_male_model_skips_female_only_rows(links):
    assert spatial.resolve("HRA:VH_F_UTERUS", None, "male") is None
    assert spatial.resolve("FMA7088", None, "female")["sex"] == "male"   # shared structure: the male link stays


def test_spatial_action_sex_only_for_female_rows():
    assert spatial._sex_fields(HEART) == {}
    assert spatial._sex_fields(UTERUS) == {"sex": "female"}
    a = spatial._action("Heart", HEART)
    assert a.fma_ids == ["FMA7088"]
    if "sex" in type(a).model_fields:                                   # once api/schemas.py has SpatialAction.sex
        assert spatial._action("Uterus", UTERUS).sex == "female"


def _write_map(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["mesh_name", "concept_id", "concept_name", "source", "reviewed_by"])
        w.writeheader()
        w.writerows(rows)


def test_female_rows_only_reviewed_and_never_male(tmp_path):
    p = tmp_path / "id_map.csv"
    _write_map(p, [
        {"mesh_name": "VH_F_uterus", "concept_id": "HRA:VH_F_UTERUS", "concept_name": "uterus", "source": "s", "reviewed_by": "AB"},
        {"mesh_name": "VH_F_uterus_2", "concept_id": "HRA:VH_F_UTERUS", "concept_name": "uterus", "source": "s", "reviewed_by": "AB"},
        {"mesh_name": "VH_F_ovary_L", "concept_id": "UBERON:0002119", "concept_name": "left ovary", "source": "s", "reviewed_by": ""},
        {"mesh_name": "VH_F_heart", "concept_id": "FMA7088", "concept_name": "heart", "source": "s", "reviewed_by": "AB"},
        {"mesh_name": "VH_F_x", "concept_id": "HRA:VH_F_X", "concept_name": "heart", "source": "s", "reviewed_by": "AB"},
    ])
    rows = build.female_rows(p, {"heart": HEART}, {"FMA7088"})
    assert [r["atlas_id"] for r in rows] == ["HRA:VH_F_UTERUS"]
    assert rows[0]["sex"] == "female" and rows[0]["reviewed_by"] == "AB"
    assert build.female_rows(tmp_path / "missing.csv", {}, set()) == []


@pytest.mark.skipif(not ID_MAP.exists(), reason="female id map not present")
def test_id_map_ids_survive_the_matchers():
    """Synthetic ids are uppercase with no spaces or commas (normalizeFma and the ?select= parser)."""
    with ID_MAP.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert rows
    bad = [r["concept_id"] for r in rows if r["concept_id"] and not re.fullmatch(r"[A-Z]+:?[A-Z0-9_]+", r["concept_id"])]
    assert not bad, bad[:5]
    assert all("," not in r["concept_id"] and " " not in r["concept_id"] for r in rows)


# ---------------------------------------------------------------- female study model (ADR-003)

FEMUR = {"label": "femur", "key": "femur", "atlas_id": "FMA9611", "atlas_name": "femur", "method": "atlas-name", "score": 1.0}


@pytest.fixture
def study(monkeypatch):
    """The committed sidecar rag/female_study_origin.json; crosswalk holds only male rows (femur, heart)."""
    monkeypatch.setattr(config, "ATLAS_URL", "https://atlas.example")
    monkeypatch.setattr(atlas, "links", lambda: {"heart": HEART, "femur": FEMUR})
    monkeypatch.setattr(spatial.concepts, "concept", lambda n: {})


def test_study_sidecar_origins():
    assert atlas.study_origin("HRA:VH_F_UTERUS") == "hra-female"
    assert atlas.study_origin("fma:7214") == "hra-female"              # left ovary, any id spelling
    assert atlas.study_origin("FMA9611") == "bp3d-reshaped"            # femur
    assert atlas.study_origin("FMA23881") == "mixed"                   # skeletal system: reshaped bones + HRA pelvis
    assert atlas.study_record("FMA9611") is None and atlas.study_record("FMA23881") is None


@pytest.mark.parametrize("fma,label", [("HRA:VH_F_UTERUS", None), (None, "uterus"), (None, "left ovary")])
def test_resolve_female_only_structure_is_hra(study, fma, label):
    r = spatial.resolve(fma, label, "female")
    assert r["sex"] == "female" and r["origin"] == "hra-female"
    a = r["atlas"][0]
    assert a.origin == "hra-female" and a.sex == "female" and a.url.endswith("&sex=female")
    if label == "left ovary":
        assert r["fma_ids"] == ["FMA7214"]                               # the left one, never both ovaries


def test_resolve_female_only_structure_without_sex(study):
    r = spatial.resolve(None, "uterus")                                 # e.g. a chat link: crosswalk has no row
    assert r["sex"] == "female" and r["origin"] == "hra-female"


def test_resolve_reshaped_part_never_female_native(study):
    r = spatial.resolve("FMA9611", None, "female")                      # femur tapped in the female study model
    assert r["origin"] == "bp3d-reshaped"
    assert r["sex"] == "male"                                           # not a female-only structure
    assert all(a.sex != "female" and a.origin != "hra-female" for a in r["atlas"])
    assert r["atlas"][0].url == "https://atlas.example/?select=FMA9611"  # FMA deep link unchanged
    m = spatial.resolve("FMA9611", None, "male")                        # male model: no origin at all
    assert m["origin"] is None and m["sex"] == "male"


def test_resolve_mixed_structure(study):
    r = spatial.resolve("FMA23881", None, "female")
    assert r is None or (r["origin"] == "mixed" and r["sex"] == "male")


def test_api_spatial_resolve_reports_origin(study):
    from fastapi.testclient import TestClient
    from api.main import app
    c = TestClient(app)
    u = c.get("/api/spatial/resolve", params={"fma": "HRA:VH_F_UTERUS", "sex": "female"}).json()
    assert u["origin"] == "hra-female" and u["sex"] == "female" and u["atlas"][0]["origin"] == "hra-female"
    f = c.get("/api/spatial/resolve", params={"fma": "FMA9611", "sex": "female"}).json()
    assert f["origin"] == "bp3d-reshaped" and f["sex"] == "male"
    assert all(a.get("origin") != "hra-female" and a.get("sex") != "female" for a in f["atlas"])
