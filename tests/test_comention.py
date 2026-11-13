import json

from rag import comention as c


def _write(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "GRAPH_DIR", tmp_path)
    c._load.cache_clear()
    rows = [
        {"a": "Gout", "b": "Bursitis", "key_a": "gout", "key_b": "bursitis", "score": 6.0, "passages": 5,
         "books": ["harrison", "robbins"], "example": "harrison/1", "tier": "comention"},
        {"a": "Gout", "b": "Uric acid", "key_a": "gout", "key_b": "uric acid", "score": 3.0, "passages": 3,
         "books": ["harrison"], "example": "harrison/2", "tier": "comention"},
        {"a": "Gout", "b": "Allopurinol", "key_a": "gout", "key_b": "allopurinol", "score": 8.0, "passages": 3,
         "books": ["tripathi"], "example": "tripathi/1", "tier": "comention"},
    ]
    (tmp_path / "comention.jsonl").write_text("\n".join(json.dumps(r) for r in rows))


def test_missing_data_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "GRAPH_DIR", tmp_path / "nope")
    c._load.cache_clear()
    assert c.see_also("Gout") == []


def test_see_also_shape_and_tier(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    out = c.see_also("gout", k=5, min_score=0)
    assert {r["tier"] for r in out} == {"comention"}
    assert set(out[0]) == {"label", "score", "books", "section_id", "tier"}
    # pairs seen in 2+ books come first even when a single-book pair scores higher
    assert [r["label"] for r in out] == ["Bursitis", "Allopurinol", "Uric acid"]
    assert out[0]["section_id"] == "harrison/1"


def test_both_directions_threshold_and_k(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    assert [r["label"] for r in c.see_also("Bursitis", min_score=0)] == ["Gout"]
    assert [r["label"] for r in c.see_also("Gout", min_score=5)] == ["Bursitis", "Allopurinol"]
    assert len(c.see_also("Gout", k=1, min_score=0)) == 1
    assert c.see_also("Unknown thing") == []
