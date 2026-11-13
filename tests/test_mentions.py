import json

from rag import mentions as m


def _write(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "GRAPH_DIR", tmp_path)
    m._load.cache_clear()
    secs = [("a/1", "a"), ("a/2", "a"), ("a/3", "a"), ("b/1", "b")]
    (tmp_path / "by_section.jsonl").write_text("\n".join(json.dumps({
        "section_id": s, "book_id": b, "title": s, "path": [s],
        "entities": [{"label": "Anaemia", "type": "PathologicalCondition", "count": 2, "strength": 9.0, "evidence": "mention"},
                     {"label": "Weak", "type": "PathologicalCondition", "count": 1, "strength": 1.0, "evidence": "mention"}],
    }) for s, b in secs))
    key = m.phrase_key("Anaemia")
    (tmp_path / "mentions.jsonl").write_text(json.dumps({"id": "e1", "label": "Anaemia", "type": "PathologicalCondition", "key": key, "sections": [
        ["a/1", 5, 12.0, "mention"], ["a/2", 3, 11.0, "mention"], ["a/3", 1, 2.0, "mention"],
        ["b/1", 2, 8.0, "mention"]]}) + "\n")


def test_normalisation_folds_plural_and_spelling():
    assert m.phrase_key("Anaemias") == m.phrase_key("anemia")
    assert m.phrase_key("Tumour") == m.phrase_key("tumors")
    assert m.phrase_key("Hyperkalaemia (disorder)") == m.phrase_key("hyperkalemia")
    assert m.tokens("Crohn's disease") == m.tokens("crohn disease")


def test_missing_data_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "GRAPH_DIR", tmp_path / "nope")
    m._load.cache_clear()
    assert m.sections_for("Anemia") == [] and m.concepts_in("a/1") == [] and m.books_for("Anemia") == []


def test_sections_for_threshold_diversity_and_tier(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    out = m.sections_for("anemia", k=3, min_strength=5.0)
    assert [r["section_id"] for r in out] == ["a/1", "b/1", "a/2"]      # book b is pulled ahead of a's second section
    assert all(r["tier"] == "mention" for r in out)
    assert "a/3" not in [r["section_id"] for r in m.sections_for("anemia", k=10)]   # below the default threshold
    assert m.sections_for("unknown thing") == []


def test_concepts_in_and_books_for(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    out = m.concepts_in("a/1", k=5, min_strength=5.0)
    assert [c["label"] for c in out] == ["Anaemia"] and out[0]["tier"] == "mention"
    assert m.concepts_in("missing") == []
    assert m.books_for("Anaemia", min_strength=5.0) == ["a", "b"]


def teardown_module(module):
    m._load.cache_clear()


def test_primary_flag_roundtrip_and_legacy_rows(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    # rewrite with a 5th element on one row (new build) next to 4-element rows (old build)
    key = m.phrase_key("Anaemia")
    (tmp_path / "mentions.jsonl").write_text(json.dumps({"id": "e1", "label": "Anaemia", "type": "PathologicalCondition", "key": key, "sections": [
        ["a/2", 3, 21.0, "mention", 1], ["a/1", 5, 12.0, "mention"], ["b/1", 2, 8.0, "mention"]]}) + "\n")
    m._load.cache_clear()
    out = m.sections_for("anemia", k=3)
    assert [r["section_id"] for r in out] == ["a/2", "b/1", "a/1"] and [r["primary"] for r in out] == [True, False, False]
    assert m.books_for("anemia") == ["a", "b"]


def test_real_index_ranks_primary_topic_section_first():
    """The concept's own section (its heading names it) leads the list, ahead of other books' stronger-looking mentions."""
    from pathlib import Path
    m._load.cache_clear()
    if not Path("data/graph/mentions.jsonl").exists():
        return
    for label, sid in (("Tuberculosis", "harrison/183-183-tuberculosis"),
                       ("Pleura", "grays/071-thorax-pleura"),
                       ("Aortic valve", "grays/094-thorax-aortic-valve")):
        top = m.sections_for(label, k=3)
        assert top and top[0]["section_id"] == sid and top[0]["primary"] is True, label
        assert top[0]["tier"] == "mention"
    assert any(r["evidence"] == "certified" for r in m.sections_for("Tuberculosis", k=8) + m.sections_for("Pleura", k=8))


def test_build_primary_loader_skips_bridge(tmp_path, monkeypatch):
    import sys
    sys.path.insert(0, "scripts")
    import build_mentions as bm
    rows = [{"class": "matched", "section_id": "a/1", "concept_ids": ["e1"], "method": "rule1:heading-exact"},
            {"class": "matched", "section_id": "a/2", "concept_ids": ["e1"], "method": "rule1:heading-bridge"},
            {"class": "entity", "section_id": "a/3", "concept_ids": [], "method": "rule:entity"}]
    p = tmp_path / "h.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(bm, "HEADINGS", p)
    assert bm.load_primary() == {"e1": {"a/1"}}
    monkeypatch.setattr(bm, "HEADINGS", tmp_path / "none.jsonl")
    assert bm.load_primary() == {}
