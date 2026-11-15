"""POST /api/story/explore. No network: retrieval, guard, id->index map and the LLM are all mocked."""
import pytest
from fastapi.testclient import TestClient

from api import main, story
from rag import config
from rag.retrieve import Hit

BOOKS = ["Tripathi", "Guyton", "Harrison"]


def pid(n):
    return f"{BOOKS[n % 3].lower()}/s1#p{n}"


def hits_for(sims):
    return [Hit(id=pid(n), passage="Passage text that must never be returned. " * 5,
                meta={"book": BOOKS[n % 3], "book_id": BOOKS[n % 3].lower()}, similarity=s)
            for n, s in enumerate(sims)]


INDEX = {pid(n): n * 10 for n in range(40)}
HAPPY_CHAT = "Your question sits among three textbooks. Its best match scores 0.81, above the 0.60 cut-off."


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(story, "_index_map", lambda: INDEX)
    monkeypatch.setattr(story, "_guard", lambda q: False)
    monkeypatch.setattr(story, "search", lambda q, k=12: hits_for([0.81 - 0.01 * n for n in range(k)]))
    monkeypatch.setattr(story, "chat", lambda system, user, **kw: HAPPY_CHAT)
    monkeypatch.setattr(config, "MIN_SIMILARITY", 0.60)
    story._explore.cache_clear()
    yield TestClient(main.app)
    story._explore.cache_clear()


def post(client, q):
    return client.post("/api/story/explore", json={"question": q})


def test_refused_returns_no_neighbours_and_never_searches(client, monkeypatch):
    monkeypatch.setattr(story, "_guard", lambda q: True)

    def boom(*a, **k):
        raise AssertionError("must not run for a refused question")

    monkeypatch.setattr(story, "search", boom)
    monkeypatch.setattr(story, "chat", boom)
    body = post(client, "My mother has TB, what dose of rifampicin should she take?").json()
    assert body["refused"] is True
    assert body["neighbours"] == []
    assert body["best"] is None
    assert body["passes_floor"] is False
    assert body["narration"] == story.REFUSED_NARRATION


def test_below_floor_is_reported_and_narrated(client, monkeypatch):
    monkeypatch.setattr(story, "search", lambda q, k=12: hits_for([0.41 - 0.01 * n for n in range(k)]))
    monkeypatch.setattr(story, "chat", lambda system, user, **kw: "Your question sits far from the library. "
                        "Its best match scores 0.41, under the 0.60 cut-off.")
    body = post(client, "Who won the 2011 cricket world cup?").json()
    assert body["refused"] is False
    assert body["passes_floor"] is False
    assert body["best"] == 0.41
    assert body["min_similarity"] == 0.60
    assert len(body["neighbours"]) == 12
    assert body["narration"].startswith("Your question sits far")


def test_below_floor_without_llm_uses_template(client, monkeypatch):
    monkeypatch.setattr(story, "search", lambda q, k=12: hits_for([0.41 - 0.01 * n for n in range(k)]))

    def broken(*a, **k):
        raise RuntimeError("backend down")

    monkeypatch.setattr(story, "chat", broken)
    body = post(client, "Who won the 2011 cricket world cup?").json()
    assert body["passes_floor"] is False
    assert "0.41" in body["narration"] and "0.60" in body["narration"]
    assert "could not find this" in body["narration"]


def test_happy_path_maps_neighbours_to_story_indices(client, monkeypatch):
    calls = []

    def fake_search(q, k=12):
        calls.append((q, k))
        return hits_for([0.81 - 0.01 * n for n in range(k)])

    monkeypatch.setattr(story, "search", fake_search)
    body = post(client, "What drug should be started first in pheochromocytoma?").json()
    assert calls == [("What drug should be started first in pheochromocytoma?", 12)]
    assert body["refused"] is False
    assert body["passes_floor"] is True
    assert body["best"] == 0.81
    assert body["min_similarity"] == 0.60
    assert len(body["neighbours"]) == 12
    first = body["neighbours"][0]
    assert set(first) == {"i", "sim", "book"}
    assert first == {"i": 0, "sim": 0.81, "book": "Tripathi"}
    assert body["neighbours"][1]["i"] == 10 and body["neighbours"][1]["book"] == "Guyton"
    assert body["narration"] == HAPPY_CHAT
    assert "Passage text" not in str(body)


def test_invented_number_falls_back_to_template(client, monkeypatch):
    seen = []

    def chat_with_invention(system, user, **kw):
        seen.append(user)
        return "Your question sits among 37 passages. It scores 0.81 against a 0.60 cut-off."

    monkeypatch.setattr(story, "chat", chat_with_invention)
    body = post(client, "What drug is first in pheochromocytoma?").json()
    assert len(seen) == 2                       # one retry, then the template
    assert "37" not in body["narration"]
    assert body["narration"].startswith("Your question landed among passages from ")
    assert "0.81" in body["narration"] and "0.60" in body["narration"]


def test_llm_exception_falls_back_to_template(client, monkeypatch):
    def broken(system, user, **kw):
        raise RuntimeError("backend down")

    monkeypatch.setattr(story, "chat", broken)
    body = post(client, "What drug is first in pheochromocytoma?").json()
    assert body["narration"].startswith("Your question landed among passages from ")


def test_repeat_question_is_served_from_cache(client, monkeypatch):
    calls = []
    monkeypatch.setattr(story, "search", lambda q, k=12: calls.append(q) or hits_for([0.8] * k))
    first = post(client, "Beta  blocker   first?").json()
    second = post(client, "Beta blocker first?").json()
    assert len(calls) == 1
    assert first == second


@pytest.mark.parametrize("q", ["", "   ", "x" * 301])
def test_empty_or_too_long_question_is_422(client, q):
    assert post(client, q).status_code == 422


def test_missing_question_is_422(client):
    assert client.post("/api/story/explore", json={}).status_code == 422
