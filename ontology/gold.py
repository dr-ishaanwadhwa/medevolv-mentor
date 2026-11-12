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

import json
from pathlib import Path

from ontology.merge import merge_key

GOLD = Path("tests/ontology_gold.jsonl")


def load_gold(path: Path = GOLD) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def score(facts: list[dict], gold: list[dict]) -> dict:
    """facts: CERTIFIED fact dicts (as in clinical_ontology.jsonl)."""
    have = {(merge_key(f["subject_label"]), f["predicate"], merge_key(f["object_label"])) for f in facts}
    hit = [g for g in gold if (merge_key(g["condition"]), g["predicate"], merge_key(g["object"])) in have]
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
    print(json.dumps(score(list(ontology_facts.facts()), load_gold()), indent=1))


if __name__ == "__main__":
    main()
