"""Canonical concept pages over the certified ontology (wiki-style: every node answers "who points at me").

    concept("Tuberculosis")        -> {"id", "label", "type", "aliases", "outgoing": {predicate: [link]},
                                       "backlinks": {inverse name: [link]}, "books", "sections", "degree"}
    concept("rifampicin")["backlinks"]["treats"]   -> the conditions rifampicin treats
    related("Tuberculosis", k=10)  -> one-hop neighbours, ranked by shared links and corroboration
    search_concepts("tubercu")     -> label-prefix search for a search box

Every link carries a tier:
    "certified"  a direct fact: its verbatim quote was checked against the book (ontology_facts only loads those)
    "derived"    the same fact read backwards (an inverse edge). Same fact id, same quote, no new claim.
Nothing here creates a clinical claim, and nothing here may be passed to the answer prompt as evidence.
Everything is cached and returns empty when the ontology file is missing.
"""
from __future__ import annotations

import functools
from collections import Counter, defaultdict

from rag import ontology_facts

# How a predicate reads from the object's side, e.g. a drug page lists "treats" conditions.
# Wording is fixed here (not generated) so an inverse can never flip a meaning: CONTRAINDICATES reads
# "contraindicated in", never "treats".
INVERSE = {
    "TREATED_BY": "treats",                      # drug -> condition it treats
    "CONTRAINDICATES": "contraindicated in",     # drug -> condition (or stage) where it is contraindicated
    "MANIFESTS_AS": "manifestation of",          # symptom -> condition
    "CONFIRMED_BY": "confirms",                  # test -> condition
    "CAUSED_BY": "causes",                       # organism / cause -> condition
    "DISRUPTS_PATHWAY": "disrupted in",          # process -> condition
    "CAUSES_ADVERSE_EFFECT": "adverse effect of",
    "HAS_CLINICAL_STAGE": "stage of",
    "TARGETS_MECHANISM": "targeted by",          # target -> drug
    "DIFFERENTIAL_OF": "has differential",
    "INVOLVES_STRUCTURE": "involved in",         # anatomical structure -> condition affecting it (Gray's)
    "is_a": "has subtype",
}


def _link(f: dict, other: str, predicate: str, tier: str) -> dict:
    """One link as shown on a concept page. `other` is "object" or "subject": the end that is not this concept."""
    return {
        "predicate": predicate,
        "other_id": f[f"{other}_id"],
        "other_label": f[f"{other}_label"],
        "other_type": f[f"{other}_type"],
        "fact_id": f["id"],
        "books": ontology_facts.books(f),
        "sections": sorted({p["section_id"] for p in ontology_facts.sources(f)}),
        "tier": tier,
    }


@functools.cache
def _index() -> dict:
    """{"nodes": {id: record}, "by_label": {lowercase label: [ids]}}, one pass over the certified facts."""
    nodes: dict[str, dict] = {}
    labels: dict[str, Counter] = defaultdict(Counter)

    def node(nid: str, label: str, typ: str) -> dict:
        labels[nid][label] += 1
        return nodes.setdefault(nid, {"id": nid, "type": typ, "outgoing": defaultdict(list),
                                      "backlinks": defaultdict(list), "books": set(), "sections": set(), "degree": 0})

    for f in ontology_facts.facts():
        subj = node(f["subject_id"], f["subject_label"], f["subject_type"])
        obj = node(f["object_id"], f["object_label"], f["object_type"])
        subj["outgoing"][f["predicate"]].append(_link(f, "object", f["predicate"], "certified"))
        obj["backlinks"][INVERSE.get(f["predicate"], f["predicate"])].append(_link(f, "subject", f["predicate"], "derived"))
        books = set(ontology_facts.books(f))
        sections = {p["section_id"] for p in ontology_facts.sources(f)}
        for n in (subj, obj):
            n["books"] |= books
            n["sections"] |= sections
            n["degree"] += 1

    by_label: dict[str, list[str]] = defaultdict(list)
    for nid, n in nodes.items():
        n["label"] = labels[nid].most_common(1)[0][0]
        n["aliases"] = sorted(a for a in labels[nid] if a != n["label"])
        for lab in labels[nid]:
            by_label[lab.lower()].append(nid)
    # a label shared by two types resolves to the better-connected node
    for ids in by_label.values():
        ids.sort(key=lambda i: -nodes[i]["degree"])
    return {"nodes": nodes, "by_label": dict(by_label)}


def _resolve(label_or_id: str) -> dict | None:
    idx = _index()
    if label_or_id in idx["nodes"]:
        return idx["nodes"][label_or_id]
    ids = idx["by_label"].get(label_or_id.strip().lower())
    return idx["nodes"][ids[0]] if ids else None


def concept(label_or_id: str) -> dict:
    """The page for one concept, or {} when it is unknown (or the ontology is missing).
    `same_label` lists other nodes with the same name under another type (e.g. Dyspnoea as symptom and as condition);
    they are shown side by side, never merged."""
    n = _resolve(label_or_id)
    if n is None:
        return {}
    same = [i for i in _index()["by_label"].get(n["label"].lower(), []) if i != n["id"]]
    return {
        "id": n["id"], "label": n["label"], "type": n["type"], "aliases": n["aliases"],
        "outgoing": {p: list(v) for p, v in n["outgoing"].items()},
        "backlinks": {p: list(v) for p, v in n["backlinks"].items()},
        "books": sorted(n["books"]), "sections": sorted(n["sections"]), "degree": n["degree"],
        "same_label": [{"id": i, "type": _index()["nodes"][i]["type"]} for i in same],
    }


def related(label_or_id: str, k: int = 10) -> list[dict]:
    """Concepts one hop away (either direction). Ranked by how many certified facts join the two, then by how
    many books state them (corroboration), then by the neighbour's own degree. Navigation only."""
    n = _resolve(label_or_id)
    if n is None:
        return []
    agg: dict[str, dict] = {}
    for links in list(n["outgoing"].values()) + list(n["backlinks"].values()):
        for lk in links:
            r = agg.setdefault(lk["other_id"], {"id": lk["other_id"], "label": lk["other_label"],
                                                "type": lk["other_type"], "facts": set(), "books": set(),
                                                "predicates": set(), "tier": "derived"})
            r["facts"].add(lk["fact_id"])
            r["books"] |= set(lk["books"])
            r["predicates"].add(lk["predicate"])
            if lk["tier"] == "certified":
                r["tier"] = "certified"               # at least one direct fact leaves this concept
    nodes = _index()["nodes"]
    out = [{"id": r["id"], "label": r["label"], "type": r["type"], "shared_facts": len(r["facts"]),
            "n_books": len(r["books"]), "predicates": sorted(r["predicates"]), "tier": r["tier"]}
           for r in agg.values() if r["id"] != n["id"]]
    out.sort(key=lambda r: (-r["shared_facts"], -r["n_books"], -nodes[r["id"]]["degree"], r["label"]))
    return out[:k]


def search_concepts(prefix: str, limit: int = 20) -> list[dict]:
    """Concepts whose label starts with `prefix` (case-insensitive), then those with a word that does.
    Within each group the better-connected concept comes first."""
    p = prefix.strip().lower()
    if not p:
        return []
    starts, words = [], []
    for n in _index()["nodes"].values():
        lab = n["label"].lower()
        if lab.startswith(p):
            starts.append(n)
        elif any(w.startswith(p) for w in lab.replace("-", " ").split()):
            words.append(n)
    ranked = sorted(starts, key=lambda n: (-n["degree"], n["label"])) + sorted(words, key=lambda n: (-n["degree"], n["label"]))
    return [{"id": n["id"], "label": n["label"], "type": n["type"], "degree": n["degree"]} for n in ranked[:limit]]
