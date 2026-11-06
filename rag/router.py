"""ToC router (rung 3): a prompt-based, training-free stand-in for STAIR.

Stage 0  which book?        majority vote of the top vector hits (cheap, and books differ clearly by subject)
Stage A  which chapter(s)?  LLM picks up to 3 titles from the book's chapter list
Stage B  which section(s)?  LLM picks up to 3 titles from the top chapter's section list
Both LLM stages are constrained to real titles (Ollama JSON-schema enum; nearest-title snapping for other backends),
so the router can never cite a section that does not exist -- the same guarantee STAIR's constrained decoding gives.

route(question, book) -> ranked [(chapter, "chapter › section"), ...]       (for evaluation)
section_ids(question)  -> OKF section ids to restrict vector search to         (for answering)
"""
from __future__ import annotations

import difflib
import functools
import json
from collections import Counter

from rag import config
from rag.backends import chat
from rag.retrieve import search

SYSTEM_A = ("You route a medical student's question to the textbook chapter(s) that answer it. Pick from the given "
            "list only, best first, at most 3. Return JSON {\"choices\": [...]}.")
SYSTEM_B = ("You route a medical student's question to the section(s) of one chapter that answer it. Pick from the "
            "given list only, best first, at most 3. Return JSON {\"choices\": [...]}.")


@functools.cache
def toc(book: str) -> dict:
    """chapters, sections per chapter (paths below the chapter), and label -> OKF section ids."""
    entries = json.loads((config.OKF_DIR / book / "toc.json").read_text())
    chapters, sections, ids = [], {}, {}
    for t in entries:
        parts = t["path"].split(" › ")
        ch = t.get("chapter") or parts[-1]
        if ch not in chapters:
            chapters.append(ch)
        below = " › ".join(parts[parts.index(ch) + 1:]) if ch in parts else ""
        label = f"{ch} › {below}" if below else ch
        sections.setdefault(ch, [])
        if below and below not in sections[ch]:
            sections[ch].append(below)
        ids.setdefault(label, []).append(t["id"])
        ids.setdefault(ch, []).append(t["id"])          # chapter label -> all its sections
    return {"chapters": chapters, "sections": sections, "ids": ids}


def _choose(system: str, listing: list[str], question: str, k: int = 3) -> list[str]:
    schema = {"type": "object", "required": ["choices"], "properties": {
        "choices": {"type": "array", "maxItems": k, "minItems": 1, "items": {"type": "string", "enum": listing}}}}
    user = "Options:\n" + "\n".join(f"- {o}" for o in listing) + f"\n\nQuestion: {question}"
    raw = chat(system, user, temperature=0.0, max_tokens=300, schema=schema)
    try:
        picks = json.loads(raw[raw.find("{"): raw.rfind("}") + 1]).get("choices", [])
    except (json.JSONDecodeError, ValueError):
        picks = []
    out = []
    for p in picks:                      # snap anything off-list to the closest real title (non-Ollama backends)
        p = p if p in listing else next(iter(difflib.get_close_matches(str(p), listing, n=1, cutoff=0.6)), None)
        if p and p not in out:
            out.append(p)
    return out[:k]


def pick_book(question: str, n: int = 10) -> str:
    votes = Counter(h.meta["book_id"] for h in search(question, k=n))
    return votes.most_common(1)[0][0]


SHORTLIST = 4   # chapters proposed by vector search before the LLM chooses (0 = show the LLM every chapter)


def shortlist_chapters(question: str, book: str, n: int = SHORTLIST) -> list[str]:
    """Distinct chapters of the top vector hits, best first -- an easy candidate list for a small LLM."""
    out: list[str] = []
    for h in search(question, k=40, book_ids=[book]):
        ch = h.labels()[0]
        if ch not in out:
            out.append(ch)
        if len(out) == n:
            break
    return out


def route(question: str, book: str | None = None, k: int = 5, shortlist: int = SHORTLIST) -> list[tuple[str, str]]:
    book = book or pick_book(question)
    t = toc(book)
    # Choosing among 78+ titles is hard for a 3B model (measured on 40 held-out questions: 12% chapter@1 over all titles, 32% with a 4-chapter shortlist, vs 74% for plain vector search). A vector shortlist keeps the
    # choice structure-aware but small; the LLM still may only pick real titles.
    options = [c for c in shortlist_chapters(question, book, shortlist) if c in t["chapters"]] if shortlist else []
    options = options or t["chapters"]
    chapters = _choose(SYSTEM_A, options, question) or options[:1]
    ranked: list[tuple[str, str]] = []
    top = chapters[0]
    secs = t["sections"].get(top, [])
    if len(secs) > 1:
        for s in _choose(SYSTEM_B, secs, f"Chapter: {top}\n{question}"):
            ranked.append((top, f"{top} › {s}"))
    elif secs:
        ranked.append((top, f"{top} › {secs[0]}"))
    else:
        ranked.append((top, top))
    for ch in chapters[1:]:              # lower-ranked chapters contribute their first section as a fallback
        ranked.append((ch, f"{ch} › {t['sections'][ch][0]}" if t["sections"].get(ch) else ch))
    return ranked[:k]


def section_ids(question: str, book: str | None = None, max_sections: int = 3) -> tuple[str, list[str]]:
    """OKF section ids for the routed sections (plus the whole top chapter as a safety net)."""
    book = book or pick_book(question)
    t = toc(book)
    ranked = route(question, book)
    ids: list[str] = []
    for _, label in ranked[:max_sections]:
        ids += t["ids"].get(label, [])
    ids += t["ids"].get(ranked[0][0], [])  # whole top chapter, in case the section pick was too narrow
    return book, list(dict.fromkeys(ids))
