"""Graph metrics of the certified ontology, so every stage of docs/graph_networking_plan.md re-measures the same way.

    .venv/bin/python scripts/graph_metrics.py

Writes reports/graph_metrics_<date>.json (counts and labels only, no textbook text), prints a table, and writes
reports/merge_proposals.csv. The CSV is a list of PROPOSALS for a human to review; nothing here changes the ontology.
"""
from __future__ import annotations

import csv
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import networkx as nx  # noqa: E402

from ontology.merge import merge_key  # noqa: E402
from rag import ontology_facts  # noqa: E402

CONDITION = "PathologicalCondition"
PHENOTYPE = "ClinicalPhenotype"
TEST_TYPE = "DiagnosticModality"       # the data's name for a diagnostic test
STOPWORDS = {"of", "the", "and", "in", "with", "for", "to", "by", "on", "at", "from", "due"}
MODIFIERS = {"acute", "chronic", "severe", "mild", "moderate", "primary", "secondary", "early", "late", "advanced",
             "recurrent", "idiopathic", "congenital", "acquired"}


def pct(a: int, b: int) -> float:
    return round(100 * a / b, 1) if b else 0.0


def load_nodes(facts) -> tuple[dict, dict]:
    """({id: {"label", "type", "books", "sections"}}, {id: degree}); degree counts every fact touching the node."""
    labels: dict[str, Counter] = defaultdict(Counter)
    nodes: dict[str, dict] = {}
    degree: Counter = Counter()
    for f in facts:
        books = set(ontology_facts.books(f))
        sections = {p["section_id"] for p in ontology_facts.sources(f)}
        for side in ("subject", "object"):
            nid = f[f"{side}_id"]
            labels[nid][f[f"{side}_label"]] += 1
            n = nodes.setdefault(nid, {"type": f[f"{side}_type"], "books": set(), "sections": set()})
            n["books"] |= books
            n["sections"] |= sections
            degree[nid] += 1
    for nid, n in nodes.items():
        n["label"] = labels[nid].most_common(1)[0][0]
    return nodes, degree


def bodhi_ids() -> set[str] | None:
    try:
        from rag.graph import load_graph
        return set(load_graph().nodes)
    except (OSError, ImportError):
        return None


def total_sections() -> int | None:
    """Sections in the book index (data/okf/<book>/sections/*.md); None when the corpus is not on this machine."""
    n = len(list((ROOT / "data/okf").glob("*/sections/*.md")))
    return n or None


def compute(facts) -> dict:
    nodes, degree = load_nodes(facts)
    g = nx.MultiGraph()
    g.add_edges_from((f["subject_id"], f["object_id"]) for f in facts)
    comps = sorted((len(c) for c in nx.connected_components(g)), reverse=True)
    degs = [degree[n] for n in nodes]

    # condition completeness: does the condition have at least one drug / test / symptom fact
    has = defaultdict(set)
    for f in facts:
        has[f["subject_id"]].add(f["predicate"])
    conds = [n for n, d in nodes.items() if d["type"] == CONDITION]
    need = {"drug": "TREATED_BY", "test": "CONFIRMED_BY", "symptom": "MANIFESTS_AS"}
    comp = {k: sum(p in has[c] for c in conds) for k, p in need.items()}
    all3 = sum(all(p in has[c] for p in need.values()) for c in conds)
    none3 = sum(not any(p in has[c] for p in need.values()) for c in conds)

    multi_book = sum(len(n["books"]) >= 2 for n in nodes.values())
    reach = {s for n in nodes.values() for s in n["sections"]}
    n_sections = total_sections()

    bodhi = bodhi_ids()
    def crosswalk(kind: str) -> tuple[int, int]:
        ids = [n for n, d in nodes.items() if d["type"] == kind]
        hit = sum((n in bodhi) if bodhi is not None else n.isdigit() for n in ids)
        return hit, len(ids)
    cond_hit, cond_n = crosswalk(CONDITION)
    phen_hit, phen_n = crosswalk(PHENOTYPE)

    return {
        "date": date.today().isoformat(),
        "certified_facts": len(facts),
        "nodes": len(nodes),
        "edges": g.number_of_edges(),
        "unique_edge_pairs": nx.Graph(g).number_of_edges(),
        "components": len(comps),
        "largest_component_nodes": comps[0] if comps else 0,
        "largest_component_pct": pct(comps[0], len(nodes)) if comps else 0.0,
        "single_fact_components": sum(c == 2 for c in comps),
        "degree1_nodes": sum(d == 1 for d in degs),
        "degree1_pct": pct(sum(d == 1 for d in degs), len(degs)),
        "median_degree": statistics.median(degs) if degs else 0,
        "mean_degree": round(statistics.mean(degs), 2) if degs else 0,
        "conditions": len(conds),
        "conditions_with_drug_pct": pct(comp["drug"], len(conds)),
        "conditions_with_test_pct": pct(comp["test"], len(conds)),
        "conditions_with_symptom_pct": pct(comp["symptom"], len(conds)),
        "conditions_with_all_three_pct": pct(all3, len(conds)),
        "conditions_with_none_pct": pct(none3, len(conds)),
        "nodes_in_2plus_books": multi_book,
        "nodes_in_2plus_books_pct": pct(multi_book, len(nodes)),
        "bodhi_available": bodhi is not None,
        "conditions_with_bodhi_id": cond_hit,
        "conditions_with_bodhi_id_pct": pct(cond_hit, cond_n),
        "phenotypes_with_bodhi_id": phen_hit,
        "phenotypes_with_bodhi_id_pct": pct(phen_hit, phen_n),
        "sections_reachable": len(reach),
        "sections_total": n_sections,
        "sections_reachable_pct": pct(len(reach), n_sections) if n_sections else None,
    }


# ---------- duplicate-merge proposals (never applied) ----------
def words(label: str) -> list[str]:
    return merge_key(label).split()


def proposals(nodes: dict, degree: Counter) -> list[dict]:
    """Candidate duplicates for a human to review.
    word_order         same type, same words in another order or with a stopword ('CSF culture' / 'Culture of CSF')
    modifier_base      same type, 'Acute X' vs 'X'; often a subtype, so the suggestion is is_a review, not a merge
    cross_type         same label under two types (a symptom and a condition); suggestion is a same_concept_as link
    same_key_synonym   same normalised name or known synonym, same type, different id (thyroxine / levothyroxine)"""
    out = []

    def row(kind, a, b, suggestion):
        out.append({"kind": kind, "type_a": nodes[a]["type"], "id_a": a, "label_a": nodes[a]["label"], "degree_a": degree[a],
                    "type_b": nodes[b]["type"], "id_b": b, "label_b": nodes[b]["label"], "degree_b": degree[b],
                    "suggestion": suggestion})

    by_type_key = defaultdict(list)       # (type, merge_key) -> ids
    by_type_set = defaultdict(list)       # (type, frozenset of non-stopword words)
    by_type_base = defaultdict(list)      # (type, words without modifiers)
    by_key = defaultdict(list)            # merge_key -> ids, any type
    for nid, n in nodes.items():
        w = words(n["label"])
        if not w:
            continue
        by_type_key[(n["type"], " ".join(w))].append(nid)
        content = frozenset(x for x in w if x not in STOPWORDS)
        if content:
            by_type_set[(n["type"], content)].append(nid)
        base = tuple(x for x in w if x not in MODIFIERS)
        if base and len(base) < len(w) and n["type"] == CONDITION:
            by_type_base[(n["type"], frozenset(base))].append(nid)
        by_key[" ".join(w)].append(nid)

    seen = set()
    def pairs(ids):
        ids = sorted(ids)
        return [(a, b) for i, a in enumerate(ids) for b in ids[i + 1:]]

    for ids in by_type_key.values():
        for a, b in pairs(ids):
            seen.add((a, b))
            row("same_key_synonym", a, b, "merge (check)")
    for ids in by_type_set.values():
        for a, b in pairs(ids):
            if (a, b) not in seen:
                seen.add((a, b))
                row("word_order", a, b, "merge (check)")
    # modifier_base: a modified label against the plain label of the same condition
    plain = defaultdict(list)
    for nid, n in nodes.items():
        if n["type"] == CONDITION:
            plain[frozenset(words(n["label"]))].append(nid)
    for (_, base), ids in by_type_base.items():
        for a in ids:
            for b in plain.get(base, []):
                if a != b and (min(a, b), max(a, b)) not in seen:
                    seen.add((min(a, b), max(a, b)))
                    row("modifier_base", a, b, "is_a review, not a merge")
    for ids in by_key.values():
        types = {nodes[i]["type"] for i in ids}
        if len(types) > 1:
            for a, b in pairs(ids):
                if nodes[a]["type"] != nodes[b]["type"]:
                    row("cross_type", a, b, "same_concept_as link, keep both nodes")
    return out


def main() -> None:
    facts = ontology_facts.facts()
    if not facts:
        sys.exit("No certified ontology found at data/ontology/clinical_ontology.jsonl")
    m = compute(facts)
    out = ROOT / f"reports/graph_metrics_{m['date']}.json"
    out.write_text(json.dumps(m, indent=2), encoding="utf-8")

    nodes, degree = load_nodes(facts)
    props = proposals(nodes, degree)
    cols = ["kind", "type_a", "id_a", "label_a", "degree_a", "type_b", "id_b", "label_b", "degree_b", "suggestion"]
    with open(ROOT / "reports/merge_proposals.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(sorted(props, key=lambda r: (r["kind"], r["label_a"].lower())))

    for k, v in m.items():
        print(f"{k:34} {v}")
    kinds = Counter(p["kind"] for p in props)
    print("\nmerge proposals (reports/merge_proposals.csv): " + ", ".join(f"{k}={n}" for k, n in sorted(kinds.items())))
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
