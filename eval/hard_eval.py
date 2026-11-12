"""Hard multi-axis clinical cases: does the answer cover what each clinical axis needs, and avoid the trap?

    .venv/bin/python -m eval.hard_eval run --arm after            # three-axis decomposition + axis-aware answer prompt
    .venv/bin/python -m eval.hard_eval run --arm plain            # three-axis decomposition, plain answer prompt
    .venv/bin/python -m eval.hard_eval run --arm before           # axis split switched off (older focus/queries split)
    .venv/bin/python -m eval.hard_eval compare reports/hard_eval_before.json reports/hard_eval_after.json

eval/hard_cases.jsonl holds acute cases (h*) that need all three axes -- etiology & differential, emergency
stabilisation, definitive pharmacology & contraindications -- each with a contraindication trap, plus chronic
controls (c*) where the emergency axis should be skipped. Every case has rubric points tagged by axis.

Per answer an LLM judge marks which rubric points the answer states and which traps it falls into (the answer only;
it is not told the evidence), and product_eval's groundedness judge checks it against its evidence. The judges are
the same LLM family as the answerer, so treat the numbers as indicative. Reports go to reports/ (git-ignored).
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

from rag import config, hops
from rag.answer import answer_multihop
from rag.backends import chat

AXES = list(hops.AXES)
RUBRIC_JUDGE = """You grade a medical study-aid answer against a marking rubric. For each rubric point, decide whether
the answer clearly states it (same meaning in different words counts; a vague nod does not). For each trap, decide
whether the answer recommends or endorses it (mentioning it only to warn against it does NOT count as a trap).
Return JSON: {"covered": ["<point id>", ...], "traps_hit": ["<trap id>", ...]}"""


def judge_rubric(case: dict, text: str) -> dict:
    pts = "\n".join(f"{p['id']}: {p['point']}" for p in case["rubric"])
    traps = "\n".join(f"{t['id']}: {t['trap']}" for t in case["traps"]) or "(none)"
    raw = chat(RUBRIC_JUDGE, f"Rubric points:\n{pts}\n\nTraps:\n{traps}\n\nAnswer:\n{text}", temperature=0.0,
               max_tokens=400, json_mode=True, purpose="Grade answer against rubric")
    try:
        d = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except ValueError:
        return {"covered": [], "traps_hit": [], "judge_error": True}
    ids = {p["id"] for p in case["rubric"]}
    tids = {t["id"] for t in case["traps"]}
    return {"covered": sorted(set(map(str, d.get("covered", []))) & ids),
            "traps_hit": sorted(set(map(str, d.get("traps_hit", []))) & tids)}


def axes_used(plan) -> list[str]:
    """Axes the case route searched, read from the plan's retrieve hops ('[etiology] ...')."""
    out = []
    for h in getattr(plan, "hops", []) or []:
        if h.kind == "retrieve" and h.query.startswith("["):
            a = h.query[1:h.query.find("]")]
            if a in AXES and a not in out:
                out.append(a)
    return out


def run(arm: str, out: Path, only: set[str] | None) -> None:
    from eval.product_eval import judge as ground_judge
    if arm == "plain":
        from rag import answer as answer_mod
        answer_mod.AXIS_AWARE = False
    if arm == "before":
        hops.decompose_axes = lambda q: (None, "axis split disabled (A/B arm 'before')")
    cases = [json.loads(l) for l in Path("eval/hard_cases.jsonl").read_text().splitlines() if l.strip()]
    rows = []
    for c in cases:
        if only and c["id"] not in only:
            continue
        t = time.time()
        try:
            res, err = answer_multihop(c["question"]), None
        except Exception as e:                            # record, don't abort the run
            res, err = None, f"{type(e).__name__}: {e}"
        row = {"id": c["id"], "condition": c["condition"], "expected_axes": c["expected_axes"],
               "latency_s": round(time.time() - t, 2), "error": err}
        if res is not None:
            g = judge_rubric(c, res.text) if res.status == "answered" else {"covered": [], "traps_hit": []}
            cited_books = sorted({res.hits[i - 1].meta.get("book_id") for i in res.cited})
            row.update(status=res.status, route=res.plan.route if res.plan else "-", axes_used=axes_used(res.plan),
                       n_graph_facts=len(getattr(res.plan, "graph_facts", []) or []), n_hits=len(res.hits),
                       cited_books=cited_books, gold_book_hit=bool(set(cited_books) & set(c["gold_books"])),
                       points={p["id"]: p["axis"] for p in c["rubric"]}, **g,
                       ground=ground_judge(res), answer=res.text)
        rows.append(row)
        print(f"{arm:6} {c['id']} {row.get('status', 'error'):12} axes={','.join(a[:5] for a in row.get('axes_used', [])) or '-':20} "
              f"rubric={len(row.get('covered', []))}/{len(c['rubric'])} traps={row.get('traps_hit')} {row['latency_s']:.1f}s",
              flush=True)
    report = {"when": time.strftime("%Y-%m-%d %H:%M"), "arm": arm, "llm": f"{config.LLM_BACKEND}",
              "rows": rows, "summary": summarise(rows)}
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"], indent=1))


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if not r.get("error")]
    per_axis = {}
    for a in AXES:
        pts = [(pid in r.get("covered", [])) for r in ok for pid, ax in r.get("points", {}).items() if ax == a]
        per_axis[a] = round(sum(pts) / len(pts), 3) if pts else None
    all_pts = [(pid in r.get("covered", [])) for r in ok for pid in r.get("points", {})]
    n_traps = sum(len(r.get("traps_hit", [])) for r in ok)
    ground = [r["ground"] for r in ok if r.get("ground")]
    # axis selection vs expected (only meaningful when the axis split ran)
    sel = [r for r in ok if r.get("axes_used")]
    tp = sum(len(set(r["axes_used"]) & set(r["expected_axes"])) for r in sel)
    fp = sum(len(set(r["axes_used"]) - set(r["expected_axes"])) for r in sel)
    fn = sum(len(set(r["expected_axes"]) - set(r["axes_used"])) for r in sel)
    lat = [r["latency_s"] for r in ok]
    return {
        "cases": len(rows), "errors": len(rows) - len(ok),
        "answered": sum(r.get("status") == "answered" for r in ok),
        "rubric_recall": round(sum(all_pts) / len(all_pts), 3) if all_pts else None,
        "rubric_recall_by_axis": per_axis,
        "cases_with_trap": sum(bool(r.get("traps_hit")) for r in ok), "traps_hit": n_traps,
        "groundedness": round(sum(j["supported"] for j in ground) / sum(j["claims"] for j in ground), 3) if ground else None,
        "gold_book_hit": f"{sum(bool(r.get('gold_book_hit')) for r in ok)}/{len(ok)}",
        "axis_selection": ({"precision": round(tp / (tp + fp), 3) if tp + fp else None,
                            "recall": round(tp / (tp + fn), 3) if tp + fn else None,
                            "stabilization_on_controls": sum("stabilization" in r["axes_used"] for r in sel
                                                             if r["id"].startswith("c"))} if sel else None),
        "latency_p50_s": statistics.median(lat) if lat else None,
    }


def compare(paths: list[Path]) -> None:
    reps = [json.loads(p.read_text()) for p in paths]
    keys = ["answered", "rubric_recall", "cases_with_trap", "traps_hit", "groundedness", "gold_book_hit", "latency_p50_s"]
    print("metric".ljust(28) + "".join(r["arm"].rjust(14) for r in reps))
    for k in keys:
        print(k.ljust(28) + "".join(str(r["summary"][k]).rjust(14) for r in reps))
    for a in AXES:
        print(f"recall: {a}".ljust(28) + "".join(str(r["summary"]["rubric_recall_by_axis"][a]).rjust(14) for r in reps))
    print("\nper case (rubric covered / traps):")
    by = [{r["id"]: r for r in rep["rows"]} for rep in reps]
    for cid in by[0]:
        cells = [f"{len(b[cid].get('covered', []))}/{len(b[cid].get('points', {}))} {''.join(b[cid].get('traps_hit', [])) or '-'}"
                 if cid in b else "-" for b in by]
        print(cid.ljust(28) + "".join(c.rjust(14) for c in cells))


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--arm", choices=["before", "plain", "after"], default="after")
    r.add_argument("--out", type=Path)
    r.add_argument("--only", help="comma-separated case ids")
    c = sub.add_parser("compare")
    c.add_argument("reports", nargs="+", type=Path)
    a = ap.parse_args()
    if a.cmd == "run":
        run(a.arm, a.out or Path(f"reports/hard_eval_{a.arm}.json"), set(a.only.split(",")) if a.only else None)
    else:
        compare(a.reports)


if __name__ == "__main__":
    main()
