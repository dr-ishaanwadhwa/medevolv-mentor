"""POST /api/story/explore: the 'Try your own question' chapter of the /how scroll story.

A visitor's question is placed on the same map the story draws (scripts/build_library_map.py). The response gives the 12
nearest passages as indices into that map, the best similarity, whether it clears the relevance floor, and a two-sentence
narration. Passage text never leaves the server. Results are cached in-process by the whitespace-normalised question.
"""
from __future__ import annotations

import functools
import re
from collections import Counter

from fastapi import APIRouter

from api.schemas import StoryExploreRequest, StoryExploreResponse, StoryNeighbour
from rag import config
from rag.answer import _guard
from rag.backends import chat
from rag.index import get_collection
from rag.retrieve import search

router = APIRouter(prefix="/api/story")

NEIGHBOURS = 12
PAGE = 5000            # same paging as scripts/build_library_map.load(): offset 0, then 5000 at a time
CACHE_SIZE = 256
NARRATION_MAX = 400    # characters; a longer model draft is treated as a failure and falls back to the template
REFUSED_NARRATION = ("This asks for treatment or dosing for a real person, so it's refused before any search. "
                     "The app is a study aid.")

SYSTEM = """You write two short sentences for a visitor to a study app's map of textbook passages.
Rules:
- Second person, warm, plain language. No hype words.
- Sentence one says where the visitor's question landed on the map, naming the textbooks involved.
- Sentence two says what that means for the answer, using only the facts given.
- Use ONLY numbers that appear in the facts. Never invent a number, percentage or book.
- Never quote or paraphrase textbook text. No medical advice.
- Output the two sentences only: no list, no quotes, no headings."""


@functools.cache
def _index_map() -> dict[str, int]:
    """Chroma id -> position in the story map. Built once, in the same order as scripts/build_library_map.load()."""
    c = get_collection()
    ids: list[str] = []
    for off in range(0, c.count(), PAGE):
        ids += c.get(include=[], limit=PAGE, offset=off)["ids"]
    return {pid: i for i, pid in enumerate(ids)}


def _numbers(text: str) -> set[float]:
    return {float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def _facts(question: str, passes: bool, best: float, floor: float, books: Counter) -> str:
    by_book = "; ".join(f"{b}: {n}" for b, n in books.most_common())
    return (f'Question: "{question}". Passes the relevance floor: {"yes" if passes else "no"}. '
            f"Best similarity: {best:.2f} (1 means identical). Relevance floor: {floor:.2f}. "
            f"The {NEIGHBOURS} nearest passages by textbook: {by_book}. "
            f"These {NEIGHBOURS} are only the neighbourhood shown on the map: a real answer sends just the closest few "
            f"that clear the floor to the model as evidence, never all {NEIGHBOURS}. Do not say the answer uses all of them.")


def _template(question: str, passes: bool, best: float, floor: float, books: Counter) -> str:
    """Deterministic narration, built from the same facts as the model prompt."""
    where = ", ".join(f"{b} ({n})" for b, n in books.most_common())
    if passes:
        return (f"Your question landed among passages from {where}, close together on the map, with a closest match of "
                f"{best:.2f}. That clears the {floor:.2f} cut-off, so the app answers and cites the passages it used.")
    return (f"Your question landed away from most of the library: its closest passage scores {best:.2f}, under the "
            f"{floor:.2f} cut-off. So the app says it could not find this in its textbooks rather than guess.")


def _narrate(facts: str, allowed: set[float]) -> str | None:
    """Model narration, validated like scripts/build_story_narration.py: no number outside the facts, one retry."""
    user = f"FACTS (the only numbers you may use): {facts}"
    for _ in range(2):
        try:
            text = " ".join(chat(SYSTEM, user, temperature=0.3, max_tokens=160).split())
        except Exception:
            return None
        bad = _numbers(text) - allowed
        if text and len(text) <= NARRATION_MAX and not bad:
            return text
        user += f"\nYour last draft used numbers not in the facts: {sorted(bad)}. Use only the facts."
    return None


def _compute(question: str) -> dict:
    floor = config.MIN_SIMILARITY
    if _guard(question):
        return {"question": question, "refused": True, "neighbours": [], "best": None, "min_similarity": floor,
                "passes_floor": False, "narration": REFUSED_NARRATION}

    index = _index_map()
    hits = search(question, k=NEIGHBOURS)
    if not hits:
        return {"question": question, "refused": False, "neighbours": [], "best": None, "min_similarity": floor,
                "passes_floor": False,
                "narration": "Your question did not land near any passage in the library, so there is nothing to show."}

    best = hits[0].similarity
    passes = best >= floor
    neighbours = [{"i": index[h.id], "sim": round(h.similarity, 3), "book": _book(h)}
                  for h in hits if h.id in index]
    books = Counter(n["book"] for n in neighbours)
    facts = _facts(question, passes, best, floor, books)
    narration = _narrate(facts, _numbers(facts))
    if narration is None:
        narration = _template(question, passes, best, floor, books)
    return {"question": question, "refused": False, "neighbours": neighbours, "best": round(best, 3),
            "min_similarity": floor, "passes_floor": passes, "narration": narration}


def _book(hit) -> str:
    return hit.meta.get("book") or hit.meta.get("book_id", "")


@functools.lru_cache(maxsize=CACHE_SIZE)
def _explore(question: str) -> dict:
    return _compute(question)


@router.post("/explore", response_model=StoryExploreResponse)
def explore(req: StoryExploreRequest) -> StoryExploreResponse:
    # Cache key: the question with runs of whitespace collapsed. Casing is kept, since it can matter to the embedder.
    return StoryExploreResponse(**_explore(" ".join(req.question.split())))
