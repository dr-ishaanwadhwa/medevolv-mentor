"""Write a seeded random sample of CERTIFIED anatomy facts for a human / subagent audit.

    .venv/bin/python scripts/anatomy_audit_sample.py --n 100 --seed 1 --out <file.jsonl>
Each line: {i, id, s, sk, p, o, ok, quote}. The audit file holds textbook quotes: keep it outside the repo.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ontology.anatomy import ANATOMY_PREDICATES  # noqa: E402
from ontology.compiler import ONTOLOGY_FILE  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n", type=int, default=100)
ap.add_argument("--seed", type=int, default=1)
ap.add_argument("--out", required=True)
a = ap.parse_args()
preds = {p.value for p in ANATOMY_PREDICATES}
fs = [json.loads(l) for l in ONTOLOGY_FILE.read_text().splitlines() if l.strip()]
fs = sorted((f for f in fs if f["predicate"] in preds and f["status"] == "CERTIFIED"), key=lambda f: f["id"])
random.Random(a.seed).shuffle(fs)
rows = [{"i": i, "id": f["id"], "s": f["subject_label"], "sk": f["clinical_facets"].get("structure_kind"), "p": f["predicate"],
         "o": f["object_label"], "ok": f["clinical_facets"].get("object_structure_kind"), "quote": f["provenance"]["verbatim_quote"]}
        for i, f in enumerate(fs[: a.n])]
Path(a.out).write_text("\n".join(json.dumps(r) for r in rows) + "\n")
print(len(rows), "of", len(fs))
