"""Co-mention layer (Stage 6 of docs/graph_networking_plan.md): the weakest tier, T4. Deterministic, no LLM.

Two entities that appear in the same paragraph often enough get a PMI score. This is a "you might also browse"
hint only. It is NOT a clinical claim: a drug and its side effect share paragraphs with the disease the drug treats.
Never put these into an answer prompt, never read them from the fact path in hops.py, never count them as knowledge.

Built by scripts/build_comention.py into data/graph/comention.jsonl.

    see_also("Tuberculosis", k=5) -> [{"label", "score", "books", "section_id", "tier": "comention"}]

Returns [] when the data has not been built.
"""
from __future__ import annotations

import functools
import json

from rag.mentions import GRAPH_DIR, phrase_key

TIER = "comention"
# Chosen from reports/comention_audit.md (>= 80% of sampled pairs judged useful at or above this PMI).
DEFAULT_MIN_SCORE = 4.0


@functools.cache
def _load() -> dict[str, list[dict]]:
    """phrase key -> neighbour rows, best first. Each pair is stored once on disk and indexed on both sides."""
    f = GRAPH_DIR / "comention.jsonl"
    if not f.exists():
        return {}
    idx: dict[str, list[dict]] = {}
    for line in f.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        for me, other, other_label in ((r["key_a"], r["key_b"], r["b"]), (r["key_b"], r["key_a"], r["a"])):
            idx.setdefault(me, []).append({"label": other_label, "score": r["score"], "books": r["books"],
                                           "section_id": r["example"], "tier": TIER})
    for rows in idx.values():
        rows.sort(key=lambda x: (len(x["books"]) < 2, -x["score"]))
    return idx


def see_also(label: str, k: int = 10, min_score: float | None = None) -> list[dict]:
    floor = DEFAULT_MIN_SCORE if min_score is None else min_score
    rows = [r for r in _load().get(phrase_key(label), []) if r["score"] >= floor]
    return [dict(r) for r in rows[:k]]
