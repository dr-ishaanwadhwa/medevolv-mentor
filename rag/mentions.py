"""Entity <-> section mention index (Stage 2 of docs/graph_networking_plan.md). Deterministic, no LLM.

Built by scripts/build_mentions.py into data/graph/. Every result carries tier="mention": a navigation and
retrieval hint ("this section talks about X"), never a clinical claim. Do not put these into an answer prompt.

    sections_for("Tuberculosis", k=5)  -> [{"section_id", "book_id", "title", "path", "count", "strength", "evidence", "primary", "tier"}]
    "primary" is True when the section's own heading names the concept (a ranking hint from the ToC, navigation only).
    concepts_in("harrison/001-...", k=10) -> [{"label", "type", "count", "strength", "tier"}]
    books_for("Tuberculosis")          -> ["harrison", "robbins", ...]

`section_id` is the same id that `rag.retrieve.search(..., section_ids=[...])` filters on.
Everything returns [] when data/graph/ has not been built.
"""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path

GRAPH_DIR = Path("data/graph")
# Chosen from reports/mention_audit.md: links weaker than this are kept on disk but hidden by default.
DEFAULT_MIN_STRENGTH = 7.0
TIER = "mention"

_TOKEN = re.compile(r"[a-z0-9]+")


def norm_token(t: str) -> str:
    """Cheap plural + British/US folding, applied to text and labels alike so they meet in the middle."""
    t = t.replace("ae", "e").replace("oe", "e")
    t = re.sub(r"isation", "ization", t)
    t = re.sub(r"(is)(e|ed|es|ing)$", r"iz\2", t) if len(t) > 5 else t
    t = re.sub(r"ys(e|ed|es|ing)$", r"yz\1", t)
    t = re.sub(r"our(s|ed)?$", r"or\1", t)
    t = re.sub(r"tre$", "ter", t)
    if t.endswith("ies") and len(t) > 4:
        return t[:-3] + "y"
    if t.endswith("sses"):
        return t[:-2]
    if t.endswith("s") and not t.endswith(("ss", "us", "is")) and len(t) > 3:
        return t[:-1]
    return t


def tokens(text: str) -> list[str]:
    text = text.lower().replace("'s ", " ").replace("’s ", " ")
    return [norm_token(t) for t in _TOKEN.findall(text)]


def phrase_key(label: str) -> str:
    label = re.sub(r"\([^)]*\)", " ", label)           # drop qualifiers such as "(disorder)"
    return " ".join(tokens(label))


@functools.cache
def _load() -> tuple[dict, dict]:
    """(by_key: phrase key -> [[section_id, count, strength, evidence], ...], by_section: id -> row)"""
    f, r = GRAPH_DIR / "mentions.jsonl", GRAPH_DIR / "by_section.jsonl"
    if not (f.exists() and r.exists()):
        return {}, {}
    by_key: dict[str, dict[str, list]] = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        slot = by_key.setdefault(row["key"], {})
        for sid, count, strength, ev, *rest in row["sections"]:
            old = slot.get(sid)
            if old is None or strength > old[2]:
                slot[sid] = [sid, count, strength, ev, bool(rest and rest[0])]   # 5th: heading says this is the concept's own section
    by_section = {}
    for line in r.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        by_section[row["section_id"]] = row
    return {k: list(v.values()) for k, v in by_key.items()}, by_section


def _diverse(rows: list[list], by_section: dict, k: int) -> list[list]:
    """Best section of each book first, then the second best of each, and so on (rows already sorted)."""
    queues: dict[str, list] = {}
    for row in rows:
        queues.setdefault(by_section[row[0]]["book_id"], []).append(row)
    out, depth = [], 0
    while len(out) < k and any(len(q) > depth for q in queues.values()):
        layer = sorted((q[depth] for q in queues.values() if len(q) > depth), key=lambda x: (not x[4], -x[2]))
        out.extend(layer)
        depth += 1
    return out[:k]


def sections_for(label: str, k: int = 5, min_strength: float | None = None) -> list[dict]:
    by_key, by_section = _load()
    floor = DEFAULT_MIN_STRENGTH if min_strength is None else min_strength
    rows = [r for r in by_key.get(phrase_key(label), []) if r[0] in by_section and (r[3] == "certified" or r[2] >= floor)]
    rows.sort(key=lambda r: (not r[4], -r[2]))              # a concept's own section (its heading names it) first, then by strength
    out = []
    for sid, count, strength, ev, primary in _diverse(rows, by_section, k):
        s = by_section[sid]
        out.append({"section_id": sid, "book_id": s["book_id"], "title": s["title"], "path": s["path"],
                    "count": count, "strength": strength, "evidence": ev, "primary": primary, "tier": TIER})
    return out


def concepts_in(section_id: str, k: int = 10, min_strength: float | None = None) -> list[dict]:
    _, by_section = _load()
    floor = DEFAULT_MIN_STRENGTH if min_strength is None else min_strength
    row = by_section.get(section_id)
    if not row:
        return []
    ents = [e for e in row["entities"] if e["evidence"] == "certified" or e["strength"] >= floor]
    ents.sort(key=lambda e: -e["strength"])
    return [{**e, "tier": TIER} for e in ents[:k]]


def books_for(label: str, min_strength: float | None = None) -> list[str]:
    _, by_section = _load()
    floor = DEFAULT_MIN_STRENGTH if min_strength is None else min_strength
    books: dict[str, float] = {}
    for sid, _c, strength, ev, *_ in _load()[0].get(phrase_key(label), []):
        if sid in by_section and (ev == "certified" or strength >= floor):
            b = by_section[sid]["book_id"]
            books[b] = max(books.get(b, 0), strength)
    return sorted(books, key=lambda b: -books[b])
