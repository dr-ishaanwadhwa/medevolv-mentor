"""Build the data for the /how scroll story: a 3D map of every textbook passage plus one real question's journey.

    ../med-rag/.venv/bin/python -m scripts.build_library_map [--fast]

Writes (all git-ignored: derived from the textbooks, though they hold no text):
    apps/web/public/story/library.bin   Float32 xyz (t-SNE layout) + Float32 xyz (book-cluster layout) + Uint8 book index
    apps/web/public/story/story.json     books, counts, centroids, and the traced journey (indices into the map only)
    var/story_facts.json                 the facts sheet the narration is written from (scripts/build_story_narration.py)
    var/library_pca.npz                  mean + 3 components, so the API can place a live question on the same map

The journey is the real pipeline: answer_multihop() on the story question, with the step trace recorded. Each passage
the pipeline saw is located on the map by its Chroma id; nothing here is illustrative.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from rag import config, retrieve, trace
from rag.answer import answer_multihop
from rag.index import get_collection

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "apps/web/public/story"
VAR = ROOT / "var"
QUESTION = "A patient with pheochromocytoma is posted for surgery. What drug should be started first and why?"
DECLINED = "Who won the 2011 cricket world cup?"
REFUSED = "My mother has TB, what dose of rifampicin should she take?"
BOOK_ORDER = ["grays", "guyton", "tripathi", "robbins", "micro", "davidson", "harrison"]
NEIGHBOURS = 20          # per sub-question, to show what sits just below the relevance floor


def load():
    c = get_collection()
    ids, embs, books, titles = [], [], [], {}
    for off in range(0, c.count(), 5000):
        b = c.get(include=["embeddings", "metadatas"], limit=5000, offset=off)
        ids += b["ids"]
        embs.append(np.asarray(b["embeddings"], dtype=np.float32))
        for m in b["metadatas"]:
            books.append(m["book_id"])
            titles.setdefault(m["book_id"], m.get("book", m["book_id"]))
    return ids, np.vstack(embs), books, titles


def normalise(p: np.ndarray, radius: float = 1.0) -> np.ndarray:
    p = p - p.mean(0)
    return p / np.percentile(np.linalg.norm(p, axis=1), 98) * radius


def layouts(X: np.ndarray, books: list[str], fast: bool):
    mean = X.mean(0)
    _, _, vt = np.linalg.svd((X - mean)[::5], full_matrices=False)
    pca3 = (X - mean) @ vt[:3].T
    if fast:
        galaxy = normalise(pca3)
    else:
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE
        t = time.time()
        x50 = PCA(50, random_state=0).fit_transform(X)
        galaxy = normalise(TSNE(3, perplexity=40, init="pca", random_state=0, n_jobs=-1).fit_transform(x50))
        print(f"t-SNE {time.time() - t:.0f}s")
    # book-cluster layout: each book's points keep their galaxy shape, shrunk around a point on a ring
    B = np.array(books)
    clusters = np.zeros_like(galaxy)
    for i, b in enumerate(BOOK_ORDER):
        a = 2 * np.pi * i / len(BOOK_ORDER)
        centre = np.array([np.cos(a) * 1.1, np.sin(a) * 0.35, np.sin(a) * 1.1])
        sel = B == b
        g = galaxy[sel] - galaxy[sel].mean(0)
        clusters[sel] = centre + g * (0.28 * np.sqrt(sel.sum() / len(B)) ** 0.5)
    return galaxy.astype(np.float32), clusters.astype(np.float32), mean, vt[:3], pca3


def journey(index: dict[str, int]) -> dict:
    steps = []
    trace.start(lambda s: steps.append(s))
    t0 = time.perf_counter()
    try:
        ans = answer_multihop(QUESTION)
    finally:
        trace.stop()
    total = (time.perf_counter() - t0) * 1000
    plan = ans.plan
    subs = [h.query for h in (plan.hops if plan else []) if h.kind == "retrieve"] or [QUESTION]
    near = []
    for q in subs:
        hits = retrieve.search(q, k=NEIGHBOURS)
        near.append({"query": q, "neighbours": [{"i": index[h.id], "sim": round(h.similarity, 3),
                                                  "book": h.meta.get("book_id")} for h in hits if h.id in index]})
    evidence = [{"n": n, "i": index[h.id], "book": h.meta.get("book_id"), "sim": round(h.similarity, 3),
                 "where": h.citation(), "cited": n in ans.cited}
                for n, h in enumerate(ans.hits, 1) if h.id in index]
    return {
        "question": QUESTION, "status": ans.status, "route": plan.route if plan else "single",
        "sub_questions": subs, "near": near, "evidence": evidence, "answer": ans.text, "ms": round(total),
        "steps": [{"stage": s.stage, "title": s.title, "detail": s.detail[:240], "ms": round(s.ms)} for s in steps],
    }


def refusal() -> dict:
    steps = []
    trace.start(lambda s: steps.append(s))
    try:
        ans = answer_multihop(REFUSED)
    finally:
        trace.stop()
    return {"question": REFUSED, "status": ans.status, "text": ans.text,
            "steps": [{"stage": s.stage, "title": s.title, "ms": round(s.ms)} for s in steps]}


def declined(index: dict[str, int]) -> dict:
    """The relevance floor in action: an off-topic question's nearest passages all fall below MIN_SIMILARITY."""
    hits = retrieve.search(DECLINED, k=NEIGHBOURS)
    ans = answer_multihop(DECLINED)
    return {"question": DECLINED, "status": ans.status, "best": round(hits[0].similarity, 3) if hits else None,
            "neighbours": [{"i": index[h.id], "sim": round(h.similarity, 3), "book": h.meta.get("book_id")}
                           for h in hits if h.id in index]}


def main(fast: bool, journey_only: bool = False) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    VAR.mkdir(exist_ok=True)
    ids, X, books, titles = load()
    index = {pid: i for i, pid in enumerate(ids)}
    book_ix = np.array([BOOK_ORDER.index(b) for b in books], dtype=np.uint8)
    n = len(ids)
    if journey_only:      # reuse the layouts already on disk (t-SNE takes minutes); same Chroma order
        raw = np.frombuffer((OUT / "library.bin").read_bytes()[: n * 24], dtype=np.float32)
        galaxy, clusters = raw[: n * 3].reshape(n, 3), raw[n * 3:].reshape(n, 3)
    else:
        galaxy, clusters, mean, comps, _ = layouts(X, books, fast)
        with open(OUT / "library.bin", "wb") as f:
            f.write(galaxy.tobytes()); f.write(clusters.tobytes()); f.write(book_ix.tobytes())
        np.savez(VAR / "library_pca.npz", mean=mean, components=comps)

    j = journey(index)
    r = refusal()
    d = declined(index)
    counts = {b: int((book_ix == k).sum()) for k, b in enumerate(BOOK_ORDER)}
    story = {
        "n": len(ids), "books": [{"id": b, "title": titles[b], "count": counts[b],
                                   "centroid": clusters[book_ix == k].mean(0).round(3).tolist(),
                                   "galaxy_centroid": galaxy[book_ix == k].mean(0).round(3).tolist()}
                                  for k, b in enumerate(BOOK_ORDER)],
        "min_similarity": config.MIN_SIMILARITY, "top_k": config.TOP_K,
        "journey": {k: v for k, v in j.items() if k != "answer"}, "answer": j["answer"], "refusal": r, "declined": d,
    }
    (OUT / "story.json").write_text(json.dumps(story, ensure_ascii=False))
    (VAR / "story_facts.json").write_text(json.dumps(story, ensure_ascii=False, indent=1))
    print(f"{len(ids)} passages; route {j['route']}; {len(j['evidence'])} evidence, "
          f"{sum(e['cited'] for e in j['evidence'])} cited; refusal {r['status']}; declined {d['status']} best {d['best']}; "
          f"library.bin {(OUT / 'library.bin').stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="PCA layout instead of t-SNE (seconds, not minutes)")
    ap.add_argument("--journey-only", action="store_true", help="keep library.bin, re-run only the traced questions")
    a = ap.parse_args()
    main(a.fast, a.journey_only)
