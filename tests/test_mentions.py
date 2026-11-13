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
