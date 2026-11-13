"""Build the weak co-mention layer into data/graph/comention.jsonl (deterministic, no LLM).

    .venv/bin/python scripts/build_comention.py [--min-count 3] [--cap 20]

Entities are the same ones, with the same matching, stoplist and normalisation as build_mentions.py. A "passage" is a
paragraph. Pairs are scored by PMI over paragraphs. Pairs that are already a certified fact edge are dropped.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_mentions as bm  # noqa: E402
from rag.mentions import GRAPH_DIR, phrase_key  # noqa: E402

MIN_PARA_TOKENS = 8
MAX_ENTS_PER_PARA = 30     # a paragraph naming more than this is a list, not a statement
GENERIC_PARA_DF = 0.004    # an entity in more than this share of paragraphs is too common to be informative
GENERIC_SECTION_DF = 0.08


def contained(a: str, b: str) -> bool:
    """'heart failure' vs 'failure': one label is a token run inside the other, so the pair is trivial."""
    ta, tb = a.split(), b.split()
    if len(ta) > len(tb):
        ta, tb = tb, ta
    return any(tb[i:i + len(ta)] == ta for i in range(len(tb) - len(ta) + 1))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-count", type=int, default=3)
    ap.add_argument("--cap", type=int, default=20)
    args = ap.parse_args()
    t0 = time.time()

    by_key = bm.load_entities()
    alias_words, abbrs = bm.load_aliases(by_key)
    phrases: dict[tuple, str] = {}
    for key in by_key:
        toks = tuple(key.split())
        if len(toks) > bm.MAX_LEN or all(t in bm.STOP for t in toks) or (len(toks) == 1 and len(toks[0]) < 4) \
                or bm.BARE_ORDINAL.match(key):
            continue
        phrases[toks] = key
    for ak, ck in alias_words.items():
        toks = tuple(ak.split())
        if len(toks) <= bm.MAX_LEN and not all(t in bm.STOP for t in toks) and not (len(toks) == 1 and len(toks[0]) < 4):
            phrases[toks] = ck
    firsts = defaultdict(list)
    for toks in phrases:
        firsts[toks[0]].append(toks)
    abbr_re = re.compile(r"\b(" + "|".join(map(re.escape, abbrs)) + r")\b") if abbrs else None

    def scan(text: str) -> set[str]:
        toks = bm.tokens(text)
        found = set()
        for i, t in enumerate(toks):
            for p in firsts.get(t, ()):
                if tuple(toks[i:i + len(p)]) == p:
                    found.add(phrases[p])
        if abbr_re:
            found.update(abbrs[m] for m in abbr_re.findall(text))
        return found

    # certified fact edges, as unordered pairs of phrase keys
    id2key = {eid: key for key, ents in by_key.items() for eid, _, _ in ents}
    fact_pairs, fact_nbrs = set(), defaultdict(set)
    for line in bm.ONTOLOGY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        if f.get("status") != "CERTIFIED":
            continue
        a, b = id2key.get(f["subject_id"]), id2key.get(f["object_id"])
        if a and b and a != b:
            fact_pairs.add(frozenset((a, b)))
            fact_nbrs[a].add(b)
            fact_nbrs[b].add(a)

    paras = []                        # (section id, book id, frozenset of keys)
    sec_df = Counter()
    n_sections = 0
    for p in sorted(Path(".").glob(bm.SECTIONS)):
        s = bm.parse(p)
        n_sections += 1
        if bm.NOISE_TITLE.search(s["title"]):
            continue
        seen = set()
        for para in re.split(r"\n\s*\n", s["body"]):
            para = "\n".join(l for l in para.splitlines() if not l.startswith("#")).strip()
            if len(bm.tokens(para)) < MIN_PARA_TOKENS:
                continue
            ents = scan(para)
            seen |= ents
            if len(ents) >= 2:
                paras.append((s["id"], s["book_id"], ents))
        sec_df.update(seen)
    n_paras = len(paras)

    para_df = Counter(k for _, _, e in paras for k in e)
    generic = {k for k, d in para_df.items() if d / n_paras > GENERIC_PARA_DF or sec_df[k] / n_sections > GENERIC_SECTION_DF}

    pair_n = Counter()
    pair_books: dict[tuple, Counter] = defaultdict(Counter)
    pair_ex: dict[tuple, str] = {}
    x_n = Counter()
    for sid, book, ents in paras:
        ents = sorted(e for e in ents if e not in generic)
        if len(ents) > MAX_ENTS_PER_PARA:
            continue
        x_n.update(ents)
        for pr in combinations(ents, 2):
            pair_n[pr] += 1
            pair_books[pr][book] += 1
            pair_ex.setdefault(pr, sid)
    raw = len(pair_n)
    raw_ge3 = sum(1 for c in pair_n.values() if c >= args.min_count)

    rows = []
    n_fact = n_contained = 0
    for (a, b), c in pair_n.items():
        if c < args.min_count:
            continue
        if frozenset((a, b)) in fact_pairs:
            n_fact += 1
            continue
        if contained(a, b):
            n_contained += 1
            continue
        pmi = math.log(c * n_paras / (x_n[a] * x_n[b]))
        rows.append((a, b, c, round(pmi, 2)))
    filtered = len(rows)

    # cap per entity: best first, 2+ book pairs ahead of single-book ones
    label = {k: ents[0][1] for k, ents in by_key.items()}
    rows.sort(key=lambda r: (len(pair_books[r[0], r[1]]) < 2, -r[3], -r[2]))
    deg = Counter()
    kept = []
    for a, b, c, pmi in rows:
        if deg[a] < args.cap and deg[b] < args.cap:
            deg[a] += 1
            deg[b] += 1
            kept.append((a, b, c, pmi))

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    with open(GRAPH_DIR / "comention.jsonl", "w", encoding="utf-8") as out:
        for a, b, c, pmi in kept:
            books = sorted(pair_books[a, b], key=lambda x: -pair_books[a, b][x])
            out.write(json.dumps({"a": label[a], "b": label[b], "key_a": a, "key_b": b, "score": pmi, "passages": c,
                                  "books": books, "example": pair_ex[a, b], "tier": "comention"},
                                 separators=(",", ":")) + "\n")

    # share of degree-1 fact-graph leaves that gain a see-also neighbour (at the default threshold too)
    from rag.comention import DEFAULT_MIN_SCORE
    leaves = [k for k in by_key if len(fact_nbrs.get(k, ())) == 1]
    has_any, has_def = set(), set()
    for a, b, c, pmi in kept:
        has_any.update((a, b))
        if pmi >= DEFAULT_MIN_SCORE:
            has_def.update((a, b))
    stats = {"paragraphs_with_2plus_entities": n_paras, "generic_entities_excluded": len(generic),
             "pairs_raw": raw, "pairs_ge_min_count": raw_ge3, "dropped_fact_edge": n_fact, "dropped_contained": n_contained,
             "pairs_after_filters": filtered, "pairs_after_cap": len(kept),
             "pairs_cap_multibook": sum(1 for a, b, _, _ in kept if len(pair_books[a, b]) >= 2),
             "pairs_at_default_threshold": sum(1 for r in kept if r[3] >= DEFAULT_MIN_SCORE),
             "degree1_leaves": len(leaves), "leaves_with_neighbour_any": sum(k in has_any for k in leaves),
             "leaves_with_neighbour_default": sum(k in has_def for k in leaves),
             "build_seconds": round(time.time() - t0, 1)}
    print(json.dumps(stats, indent=1))


if __name__ == "__main__":
    main()
