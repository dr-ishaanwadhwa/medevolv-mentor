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
