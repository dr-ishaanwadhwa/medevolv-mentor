"""Evaluation harness.

Retrieval mode (no LLM needed): how often does each retriever put the right chapter / section first?
  python -m eval.run_eval retrieval --book tripathi --retrievers vector,router,stair

  Questions come from two places:
    * stair/data/<book>/val.jsonl  -- held-out generated questions with gold chapter + section (many, automatic)
    * eval/questions.jsonl         -- hand-written questions with gold_sections (few, authoritative)
  Caveat for the generated set: questions were written from the passages themselves, which favours vector search
  (shared wording). The hand-written set is the fair comparison.

Answer mode (needs the LLM): status/refusal accuracy and citation hits on eval/questions.jsonl
  python -m eval.run_eval answers [--hops]

Results are appended to reports/eval_<mode>.jsonl and printed as a table.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from rag import config

REPORTS = Path("reports")


# ---------- question sets ----------
def generated_questions(book: str, limit: int) -> list[dict]:
    rows = [json.loads(l) for l in Path(f"stair/data/{book}/val.jsonl").read_text().splitlines() if l]
    by_q: dict[str, dict] = {}
    for r in rows:
        q = re.search(r"Question: (.*)$", r["messages"][1]["content"], re.S).group(1).strip()
        item = by_q.setdefault(q, {"question": q, "chapter": None, "section": None, "source": "generated"})
        if r["stage"] == "A":
            item["chapter"] = r["target"]
        else:
            item["section"] = r["target"]
    items = [i for i in by_q.values() if i["chapter"]]
    return items[:limit] if limit else items


def handwritten_questions() -> list[dict]:
    p = Path("eval/questions.jsonl")
    if not p.exists():
        return []
    out = []
    for l in p.read_text().splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("gold_sections"):
            first = r["gold_sections"][0]                       # "chapter › section"
            out.append({"question": r["question"], "chapter": first.split(" › ")[0], "section": first,
                        "source": "handwritten", "all_gold": r["gold_sections"]})
    return out


# ---------- retrievers: question -> ranked list of (chapter, section) ----------
def vector_retriever(book: str):
    from rag.retrieve import search

    def run(q: str, k: int = 5):
        return [h.labels() for h in search(q, k=k * 3, book_ids=[book])]
    return run


def router_retriever(book: str):
    from rag.router import route

    def run(q: str, k: int = 5):
        return route(q, book=book, k=k)
    return run


def stair_retriever(book: str):
    from stair.serve import retrieve

    def run(q: str, k: int = 5):
        return retrieve(q, book=book, k=k)
    return run


RETRIEVERS = {"vector": vector_retriever, "router": router_retriever, "stair": stair_retriever}


def dedupe(ranked: list[tuple[str, str]], key: int) -> list[str]:
    seen, out = set(), []
    for item in ranked:
        v = item[key]
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def score_retrieval(items: list[dict], name: str, run) -> dict:
    n = len(items)
    hits = {"ch@1": 0, "ch@3": 0, "sec@1": 0, "sec@3": 0}
    n_sec = 0
    t0 = time.time()
    misses = []
    for it in items:
        ranked = run(it["question"])
        chapters, sections = dedupe(ranked, 0), dedupe(ranked, 1)
        gold_secs = set(it.get("all_gold") or [it["section"]] if it["section"] else [])
        hits["ch@1"] += chapters[:1] == [it["chapter"]]
        hits["ch@3"] += it["chapter"] in chapters[:3]
        if gold_secs:
            n_sec += 1
            hits["sec@1"] += bool(set(sections[:1]) & gold_secs)
            hits["sec@3"] += bool(set(sections[:3]) & gold_secs)
        if chapters[:1] != [it["chapter"]] and len(misses) < 5:
            misses.append({"q": it["question"], "gold": it["chapter"], "got": chapters[:1]})
    dt = (time.time() - t0) / max(n, 1)
    return {"retriever": name, "n": n, "n_section": n_sec,
            "chapter@1": hits["ch@1"] / n, "chapter@3": hits["ch@3"] / n,
            "section@1": hits["sec@1"] / max(n_sec, 1), "section@3": hits["sec@3"] / max(n_sec, 1),
            "sec_per_q": round(dt, 3), "example_misses": misses}


def retrieval_mode(a) -> None:
    sets = {"generated": generated_questions(a.book, a.limit), "handwritten": handwritten_questions()}
    rows = []
    for set_name, items in sets.items():
        if not items:
            print(f"(no {set_name} questions)")
            continue
        for name in a.retrievers.split(","):
            try:
                run = RETRIEVERS[name](a.book)
            except Exception as e:  # noqa: BLE001 -- e.g. STAIR adapter not trained yet
                print(f"skip {name}: {type(e).__name__}: {e}")
                continue
            r = score_retrieval(items, name, run) | {"set": set_name, "book": a.book,
                                                     "embed": config.EMBED_BACKEND, "llm": config.LLM_BACKEND,
                                                     "time": time.strftime("%Y-%m-%d %H:%M")}
            rows.append(r)
    REPORTS.mkdir(exist_ok=True)
    with open(REPORTS / "eval_retrieval.jsonl", "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"\n{'set':12} {'retriever':9} {'n':>4} {'ch@1':>6} {'ch@3':>6} {'sec@1':>6} {'sec@3':>6} {'s/q':>6}")
    for r in rows:
        print(f"{r['set']:12} {r['retriever']:9} {r['n']:>4} {r['chapter@1']:>6.1%} {r['chapter@3']:>6.1%} "
              f"{r['section@1']:>6.1%} {r['section@3']:>6.1%} {r['sec_per_q']:>6}")


# ---------- answers ----------
def answers_mode(a) -> None:
    from rag.answer import answer, answer_multihop

    p = Path("eval/questions.jsonl")
    if not p.exists():
        raise SystemExit("eval/questions.jsonl not found -- copy eval/questions.template.jsonl and fill it in.")
    items = [json.loads(l) for l in p.read_text().splitlines() if l.strip()]
    fn = answer_multihop if a.hops else answer
    rows, ok_status, ok_cite, n_cite = [], 0, 0, 0
    for it in items:
        t0 = time.time()
        res = fn(it["question"])
        expect = it.get("expect_status", "answered")
        status_ok = (res.status == expect) or (expect == "not_in_sources" and res.status == "insufficient")
        ok_status += status_ok
        cite_ok = None
        if it.get("gold_sections") and res.status == "answered":
            n_cite += 1
            cited = {res.hits[i - 1].labels()[1] for i in res.cited if i <= len(res.hits)}
            cite_ok = bool(cited & set(it["gold_sections"]))
            ok_cite += cite_ok
        rows.append({"id": it.get("id"), "type": it.get("type"), "expect": expect, "got": res.status,
                     "status_ok": status_ok, "cited_gold": cite_ok, "seconds": round(time.time() - t0, 1),
                     "answer": res.text})
        print(f"{'OK ' if status_ok else 'BAD'} {it.get('type', ''):12} {res.status:16} cite={cite_ok}  "
              f"{it['question'][:60]}")
    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"eval_answers_{'hops' if a.hops else 'baseline'}_{time.strftime('%Y%m%d-%H%M')}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    print(f"\nstatus accuracy {ok_status}/{len(items)} | gold section cited {ok_cite}/{n_cite} | {out}")
    print("Correctness and faithfulness are judged by a domain expert from the saved answers.")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="mode", required=True)
    r = sub.add_parser("retrieval")
    r.add_argument("--book", default="tripathi")
    r.add_argument("--retrievers", default="vector")
    r.add_argument("--limit", type=int, default=0)
    s = sub.add_parser("answers")
    s.add_argument("--hops", action="store_true")
    a = ap.parse_args()
    (retrieval_mode if a.mode == "retrieval" else answers_mode)(a)


if __name__ == "__main__":
    main()
