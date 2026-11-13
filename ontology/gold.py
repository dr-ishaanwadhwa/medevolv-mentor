"""Gold-set score for the ontology: precision and recall over hand-checked relationships.

tests/ontology_gold.jsonl holds triples only (no textbook text), one per line:
  {"condition": "Tuberculosis", "predicate": "TREATED_BY", "object": "Isoniazid", "expected": true}
expected=true  -> a correct relationship the ontology should contain;
expected=false -> a wrong relationship the ontology once contained and should not.
source="ontology" rows were drawn from the ontology (labelled by a haiku subagent, reviewed); source="added" rows
are key textbook relationships added from outside it, so recall_added is the honest recall figure.

  python -m ontology.gold      # prints {"precision": ..., "recall": ..., ...}

precision = of the gold triples the ontology (CERTIFIED) contains, the share that are expected=true.
recall    = of the expected=true triples, the share the ontology contains.
Names are compared with ontology.merge.merge_key, so 'Rifampicin' must be spelled as in the ontology.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ontology.merge import merge_key

GOLD = Path("tests/ontology_gold.jsonl")


def load_gold(path: Path = GOLD) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def split_of(g: dict) -> str:
    """Fixed half split: tune on "dev", report "heldout" as the headline."""
    h = hashlib.md5(f"{g['condition']}|{g['predicate']}|{g['object']}".lower().encode()).hexdigest()
    return "dev" if int(h, 16) % 2 == 0 else "heldout"


def score_split(facts: list[dict], gold: list[dict], match=None, lenient: bool = False) -> dict:
    out = {name: score(facts, [g for g in gold if split_of(g) == name], match, lenient) for name in ("dev", "heldout")}
    out["all"] = score(facts, gold, match, lenient)
    return out


def _contains(a: str, b: str) -> bool:
    """Lenient object match: one name's words contain the other's ('genexpert' ~ 'genexpert mtb rif',
    'potassium' ~ 'potassium chloride'). Reported separately from strict, never instead of it."""
    x, y = set(a.split()), set(b.split())
    return bool(x and y) and (x <= y or y <= x)


def score(facts: list[dict], gold: list[dict], match=None, lenient: bool = False) -> dict:
    """facts: CERTIFIED fact dicts (as in clinical_ontology.jsonl). Strict by default: the condition label must match.
    match=rag.ontology_facts.match_conditions scores what the app shows instead (the condition's label group,
    e.g. 'Type 2 diabetes mellitus' also reads facts filed under 'Diabetes mellitus')."""
    have = {(merge_key(f["subject_label"]), f["predicate"], merge_key(f["object_label"])) for f in facts}
    objs: dict = {}
    for s, p, o in have:
        objs.setdefault((s, p), set()).add(o)

    def found(g):
        conds = {merge_key(g["condition"])} | {merge_key(c) for c in (match(g["condition"]) if match else [])}
        o = merge_key(g["object"])
        if lenient:
            return any(_contains(o, x) for c in conds for x in objs.get((c, g["predicate"]), ()))
        return any((c, g["predicate"], o) in have for c in conds)
    hit = [g for g in gold if found(g)]
    pos = [g for g in gold if g["expected"]]
    tp = sum(1 for g in hit if g["expected"])
    return {
        "gold": len(gold),
        "present": len(hit),
        "precision": round(tp / len(hit), 3) if hit else None,
        "recall": round(sum(1 for g in pos if g in hit) / len(pos), 3) if pos else None,
        # recall over the key facts added from outside the ontology only (unbiased by how the gold was drawn)
        "recall_added": (round(sum(1 for g in pos if g.get("source") == "added" and g in hit)
                               / n_add, 3) if (n_add := sum(1 for g in pos if g.get("source") == "added")) else None),
        "wrong_still_present": [f"{g['condition']} -{g['predicate']}-> {g['object']}" for g in hit if not g["expected"]],
    }


def main() -> None:
    from rag import ontology_facts
    facts, gold = list(ontology_facts.facts()), load_gold()
    print(json.dumps({"strict": score_split(facts, gold),
                      "app_view": score_split(facts, gold, ontology_facts.match_conditions),
                      "lenient": score_split(facts, gold, ontology_facts.match_conditions, lenient=True)}, indent=1))


if __name__ == "__main__":
    main()
