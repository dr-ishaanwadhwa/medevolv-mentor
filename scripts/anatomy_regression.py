"""No-regression check for the anatomy relations: run from a directory whose data/ontology holds the ontology to test.

    cd <dir>; PYTHONPATH=<repo> python <repo>/scripts/anatomy_regression.py --out out.json [--answers]

Deterministic part: the facts that can reach answers (rag.ontology_facts.facts) and graph_facts_for over every condition
label. With --answers it also runs the anatomy smoke set through answer_multihop (LLM calls, a few cents).
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag import ontology_facts as o  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
ap.add_argument("--answers", action="store_true")
a = ap.parse_args()
labels = sorted({f["subject_label"] for f in o.facts() if f["subject_type"] in o.CONDITION_TYPES})
lines = {l: o.graph_facts_for(l) for l in labels}
out = {"answer_facts": len(o.facts()), "anatomy_facts": len(o.anatomy_facts()), "conditions": len(labels),
       "graph_facts_hash": hashlib.md5(json.dumps(lines, sort_keys=True).encode()).hexdigest(),
       "conditions_with_graph_facts": sum(1 for v in lines.values() if v)}
if a.answers:
    from rag.answer import answer_multihop
    rows = []
    for q in map(json.loads, Path(__file__).resolve().parent.parent.joinpath("eval/anatomy_smoke.jsonl").read_text().splitlines()):
        res = answer_multihop(q["question"])
        books = sorted({res.hits[i - 1].meta.get("book_id") for i in res.cited})
        rows.append({"id": q["id"], "status": res.status, "route": res.plan.route if res.plan else "-", "cited_books": books,
                     "n_cited": len(res.cited), "n_graph_facts": len(getattr(res.plan, "graph_facts", []) or []),
                     "graph_facts_hash": hashlib.md5(json.dumps(getattr(res.plan, "graph_facts", []) or []).encode()).hexdigest(),
                     "answer": res.text})
    out["smoke"] = rows
Path(a.out).write_text(json.dumps(out, indent=1))
print({k: v for k, v in out.items() if k != "smoke"})
if a.answers:
    print([(r["id"], r["status"], r["cited_books"], r["n_graph_facts"]) for r in out["smoke"]])
