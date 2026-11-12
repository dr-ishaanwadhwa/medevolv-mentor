"""Product-level evaluation: every question type, both answer modes, with an LLM groundedness judge.

    .venv/bin/python -m eval.product_eval [--modes base,multihop] [--no-judge]

Per answer: status vs expected (answered / not_in_sources|insufficient / personal_refusal), whether a cited passage
comes from a gold book, citation count, latency, and a judge score = share of the answer's claims supported by the
evidence it was given. The judge is the same LLM family as the answerer, so treat it as indicative, not ground truth.
Writes reports/product_eval.json (git-ignored: it contains model output grounded in the books).
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from rag import config
from rag.answer import answer, answer_multihop
from rag.backends import chat

REFUSED = {"not_in_sources", "insufficient"}
JUDGE = """You check a study-aid answer against the evidence it was given. Split the answer into its factual claims.
A claim is supported only if the evidence states it (graph facts [G#] count as evidence). Ignore refusals and
statements that something is not covered. Return JSON: {"claims": <int>, "supported": <int>, "unsupported": ["..."]}"""


def status_ok(expected: str, got: str) -> bool:
    return got in REFUSED if expected == "not_in_sources" else got == expected


def judge(res) -> dict | None:
    if res.status != "answered":
        return None
    facts = "\n".join(f"[G{i}] {f}" for i, f in enumerate(getattr(res.plan, "graph_facts", []) or [], 1))
    ev = "\n\n".join(f"[{i}] {h.passage}" for i, h in enumerate(res.hits, 1))
    raw = chat(JUDGE, f"Evidence:\n{facts}\n\n{ev}\n\nAnswer:\n{res.text}", temperature=0.0, max_tokens=700,
               json_mode=True)
    try:
        j = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        n = max(int(j.get("claims", 0)), 1)
        return {"claims": n, "supported": min(int(j.get("supported", 0)), n), "unsupported": j.get("unsupported", [])[:5]}
    except (ValueError, TypeError):
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="base,multihop")
    ap.add_argument("--no-judge", action="store_true")
    a = ap.parse_args()
    qs = [json.loads(l) for l in Path("eval/product_questions.jsonl").read_text().splitlines() if l.strip()]
    fns = {"base": answer, "multihop": answer_multihop}
    rows = []
    for mode in a.modes.split(","):
        for q in qs:
            t = time.time()
            try:
                res = fns[mode](q["question"])
                err = None
            except Exception as e:                       # record, don't abort the run
                res, err = None, f"{type(e).__name__}: {e}"
            dt = time.time() - t
            row = {"mode": mode, **{k: q[k] for k in ("id", "type", "subject", "question", "expect_status")},
                   "latency_s": round(dt, 2), "error": err}
            if res is not None:
                cited_books = sorted({res.hits[i - 1].meta.get("book_id") for i in res.cited})
                row.update(status=res.status, status_ok=status_ok(q["expect_status"], res.status),
                           route=res.plan.route if res.plan else "-", n_hits=len(res.hits), n_cited=len(res.cited),
                           n_graph_cited=len(res.graph_cited), cited_books=cited_books,
                           gold_book_hit=(bool(set(cited_books) & set(q["gold_books"])) if q["gold_books"] else None),
                           bodhi_agree=res.agreed_drugs[:3], answer_chars=len(res.text))
                if not a.no_judge:
                    row["judge"] = judge(res)
            else:
                row.update(status="error", status_ok=False)
            rows.append(row)
            print(f"{mode:8} {q['id']} {row['status']:16} ok={row['status_ok']!s:5} {dt:5.1f}s "
                  f"cited={row.get('n_cited')} gold={row.get('gold_book_hit')} "
                  f"judge={(row.get('judge') or {}).get('supported')}/{(row.get('judge') or {}).get('claims')}",
                  flush=True)
    out = {"when": time.strftime("%Y-%m-%d %H:%M"), "llm": f"{config.LLM_BACKEND}:{config.DEEPSEEK_MODEL if config.LLM_BACKEND == 'deepseek' else config.OLLAMA_MODEL}",
           "embed": config.EMBED_BACKEND, "rows": rows, "summary": summarise(rows)}
    Path("reports").mkdir(exist_ok=True)
    Path("reports/product_eval.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["summary"], indent=1))


def summarise(rows: list[dict]) -> dict:
    s = {}
    for mode in sorted({r["mode"] for r in rows}):
        rs = [r for r in rows if r["mode"] == mode]
        ans = [r for r in rs if r.get("status") == "answered"]
        judged = [r["judge"] for r in ans if r.get("judge")]
        gold = [r["gold_book_hit"] for r in rs if r.get("gold_book_hit") is not None]
        lat = sorted(r["latency_s"] for r in rs if r.get("status") not in ("personal_refusal",))
        by_type = {}
        for t in sorted({r["type"] for r in rs}):
            tr = [r for r in rs if r["type"] == t]
            by_type[t] = f"{sum(r['status_ok'] for r in tr)}/{len(tr)}"
        s[mode] = {
            "questions": len(rs), "status_accuracy": round(sum(r["status_ok"] for r in rs) / len(rs), 3),
            "status_by_type": by_type, "errors": sum(1 for r in rs if r.get("error")),
            "gold_book_hit_rate": round(sum(gold) / len(gold), 3) if gold else None,
            "answered_with_citation": f"{sum(1 for r in ans if r['n_cited'] or r['n_graph_cited'])}/{len(ans)}",
            "groundedness": round(sum(j["supported"] for j in judged) / sum(j["claims"] for j in judged), 3) if judged else None,
            "fully_grounded_answers": f"{sum(1 for j in judged if j['supported'] == j['claims'])}/{len(judged)}",
            "latency_p50_s": statistics.median(lat) if lat else None,
            "latency_p95_s": lat[int(0.95 * (len(lat) - 1))] if lat else None,
        }
    return s


if __name__ == "__main__":
    main()
