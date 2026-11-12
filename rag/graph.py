"""BODHI clinical graph (Eka Care, CC BY-NC 4.0) as an in-memory networkx graph, plus entity linking.

Nodes are keyed by their BODHI id (SNOMED for conditions/concepts), so BODHI-S conditions and BODHI-M concepts
with the same SNOMED id become ONE node -- that is what lets a hop go symptom -> condition -> drug.
Names come from nl_facts.jsonl, which is line-aligned with triples.jsonl.

Edges (direction as in BODHI):
  Symptom  -PRESENT_IN->      Condition    (likelihood_condition_given_symptom: high/medium/low)
  Condition-TREATED_BY->      Speciality
  Condition-IS_INFLUENCED_BY-> Condition   Condition-HAS_PREREQUISITE-> Condition
  Symptom  -RELATED_TO->      Symptom
  Concept  -CHILD_OF->        Concept      Concept-TREATED_BY-> Drug
  LabInvestigation-IMPACTS->  Concept      Concept-MONITORED_BY-> LabInvestigation
"""
from __future__ import annotations

import functools
import json
import math
import re
from pathlib import Path

import networkx as nx

BODHI_DIR = Path("data/bodhi")
TYPES = "Symptom|Condition|Speciality|Concept|Drug|LabInvestigation"
QUALIFIER = re.compile(r"\s*<[^>]+>\s*\S*")          # "Abdominal pain <severity> severe" -> "Abdominal pain"
LIKELIHOOD = {"high": 3, "medium": 2, "low": 1}


def _names(text: str, relation: str) -> tuple[str, str]:
    """Pull (head name, tail name) out of one nl_fact sentence."""
    head = re.match(rf"^(.*?) \(({TYPES})\) ", text)
    rest = text[head.end():]
    if relation == "HAS_PREREQUISITE":                 # "X (Condition) has Pregnant (Condition) as ..."
        tail = re.match(rf"^has (.*?) \(({TYPES})\)", rest)
    else:
        tail = re.search(rf"(?:present in|treated by the|treated by|influenced by|related to|sub-concept of|"
                         rf"monitored by|impacts) (.*?) \(({TYPES})\)", rest)
    return head.group(1).strip(), (tail.group(1).strip() if tail else "")


def base_name(name: str) -> str:
    return " ".join(QUALIFIER.sub(" ", name).split())


@functools.cache
def load_graph() -> nx.MultiDiGraph:
    g = nx.MultiDiGraph()
    for part in ("BODHI-S", "BODHI-M"):
        triples = (BODHI_DIR / part / "data/triples.jsonl").read_text().splitlines()
        facts = (BODHI_DIR / part / "data/nl_facts.jsonl").read_text().splitlines()
        for tl, fl in zip(triples, facts):
            t, text = json.loads(tl), json.loads(fl)["text"]
            hname, tname = _names(text, t["relation"])
            for nid, ntype, name in ((t["head"], t["head_type"], hname), (t["tail"], t["tail_type"], tname)):
                if nid not in g:
                    g.add_node(nid, type=ntype, name=base_name(name) or nid, full_name=name, sources={part})
                else:
                    g.nodes[nid]["sources"].add(part)
                    if ntype == "Condition":           # S calls it Condition, M calls it Concept: keep Condition
                        g.nodes[nid]["type"] = "Condition"
            g.add_edge(t["head"], t["tail"], key=t["relation"], relation=t["relation"], **t["properties"])
    return g


# ---------- entity linking ----------
@functools.cache
def _name_index() -> dict[str, list[str]]:
    """lower-cased base name -> node ids (symptom variants share a base name)."""
    idx: dict[str, list[str]] = {}
    for nid, d in load_graph().nodes(data=True):
        idx.setdefault(d["name"].lower(), []).append(nid)
    return idx


# Canonical medical synonyms mapped to standardized BODHI graph symptom entities
SYNONYMS: dict[str, str] = {
    # Coryza / runny nose / upper respiratory
    "coryza": "Catarrhal nasal discharge",
    "runny nose": "Catarrhal nasal discharge",
    "rhinorrhea": "Catarrhal nasal discharge",
    "nasal discharge": "Catarrhal nasal discharge",

    # Urinary / Polyuria
    "polyuria": "Increased frequency of urination",
    "frequent urination": "Increased frequency of urination",
    "excessive urination": "Increased frequency of urination",
    "increased urination": "Increased frequency of urination",
    "urinating frequently": "Increased frequency of urination",

    # Thirst / Polydipsia
    "excessive thirst": "Excessive thirst",
    "polydipsia": "Excessive thirst",

    # Weight loss / cachexia
    "weight loss": "Weight decreased (> 10% in 6 month)",
    "losing weight": "Weight decreased (> 10% in 6 month)",
    "unintentional weight loss": "Weight decreased (> 10% in 6 month)",
    "loss of weight": "Weight decreased (> 10% in 6 month)",

    # Radiating chest pain / Angina / MI
    "radiating to the left arm": "Chest pain in chest",
    "radiating to left arm": "Chest pain in chest",
    "radiating to arm": "Chest pain in chest",
    "radiating pain": "Chest pain in chest",
    "crushing chest pain": "Chest pain in chest",

    # Sweating / Diaphoresis
    "night sweats": "Night sweats",
    "night sweat": "Night sweats",
    "sweating attack": "Sweating attack",
    "sweating": "Sweating attack",
    "profuse sweating": "Sweating attack",
    "diaphoresis": "Sweating attack",
    "cold sweats": "Sweating attack",

    # Joint pains
    "polyarthralgias": "Joint pain",
    "polyarthralgia": "Joint pain",
}


def link_entities(question: str, types: tuple[str, ...] = ("Symptom", "Condition", "Concept")) -> list[dict]:
    """Find graph nodes whose names appear in the question (synonym map -> exact match -> lay single word -> semantic)."""
    g, q = load_graph(), " " + re.sub(r"[^a-z0-9 ]", " ", question.lower()) + " "
    q = re.sub(r"\s+", " ", q)
    found, taken = [], []

    # Priority 0: Medical synonym map (deterministic mapping of high-yield clinical terms)
    for phrase in sorted(SYNONYMS, key=len, reverse=True):
        clean = " " + phrase + " "
        pos = q.find(clean)
        if pos < 0:
            continue
        start, end = pos + 1, pos + len(phrase) + 1
        if any(start < e and s < end for s, e in taken):
            continue
        target = SYNONYMS[phrase]
        ids = [i for i in _name_index().get(target.lower(), []) if g.nodes[i]["type"] in types]
        if ids:
            taken.append((start, end))
            found.append({"name": g.nodes[ids[0]]["name"], "type": "Symptom", "ids": ids, "via": phrase})

    # Priority 1: Exact name index matches (longest first)
    for name in sorted(_name_index(), key=len, reverse=True):
        if len(name) < 4:
            continue
        clean = " " + re.sub(r"[^a-z0-9 ]", " ", name).strip() + " "
        clean = re.sub(r"\s+", " ", clean)
        pos = q.find(clean)
        if pos < 0:
            continue
        start, end = pos + 1, pos + len(clean) - 1            # span without the padding spaces
        if any(start < e and s < end for s, e in taken):
            continue
        ids = [i for i in _name_index()[name] if g.nodes[i]["type"] in types]
        if ids:
            taken.append((start, end))
            found.append({"name": g.nodes[ids[0]]["name"], "type": g.nodes[ids[0]]["type"], "ids": ids})

    # Fallback for lay single words BODHI only has in a longer form: "rash" -> "skin rash".
    for m in re.finditer(r"[a-z]{4,}", q):
        if any(m.start() < e and s < m.end() for s, e in taken) or m.group() in STOPWORDS:
            continue
        cands = [n for n in _name_index() if n.endswith(" " + m.group()) and len(n.split()) == 2
                 and n.split()[0] in GENERIC_PREFIXES
                 and any(g.nodes[i]["type"] == "Symptom" for i in _name_index()[n])]
        if cands:
            best = max(cands, key=lambda n: sum(g.out_degree(i) for i in _name_index()[n]))
            ids = [i for i in _name_index()[best] if g.nodes[i]["type"] in types]
            taken.append((m.start(), m.end()))
            found.append({"name": g.nodes[ids[0]]["name"], "type": "Symptom", "ids": ids, "via": m.group()})

    # Semantic fallback: clinical phrasing BODHI words differently ("burning micturition" -> "Painful urination").
    found += _semantic_symptoms(q, taken, {f["name"] for f in found})
    return found


TIME_WORDS = {"week", "weeks", "day", "days", "month", "months", "year", "years", "hour", "hours", "since", "for"}
GENERIC_PREFIXES = {"skin", "excessive", "generalized", "general", "body", "severe", "persistent", "recurrent"}
SEMANTIC_MIN_SIM = 0.86   # bge-small cosine; tuned on a handful of phrasings, recheck with eval questions


@functools.cache
def _symptom_name_vectors():
    from rag.backends import _local_model    # always the local model: fast, offline, no API cost
    # Only canonical names: skip duration/onset variants like "Weight Changes weeks to 8 weeks".
    names = sorted({d["name"] for _, d in load_graph().nodes(data=True) if d["type"] == "Symptom"
                    and not re.search(r"\d|\b(week|weeks|day|days|month|months|year|years|hour|hours)\b",
                                      d["name"].lower())})
    vecs = _local_model().encode(names, normalize_embeddings=True, batch_size=128)
    return names, vecs


def _semantic_symptoms(q: str, taken: list[tuple[int, int]], already: set[str]) -> list[dict]:
    words = [(m.group(), m.start(), m.end()) for m in re.finditer(r"[a-z]+", q)]
    grams = []
    for n in (3, 2):
        for i in range(len(words) - n + 1):
            s, e = words[i][1], words[i + n - 1][2]
            gram_words = [w for w, *_ in words[i:i + n]]
            if any(s < te and ts < e for ts, te in taken) or all(w in STOPWORDS for w in gram_words) \
                    or any(w in TIME_WORDS for w in gram_words):
                continue
            grams.append((" ".join(w for w, *_ in words[i:i + n]), s, e))
    if not grams:
        return []
    from rag.backends import _local_model
    names, vecs = _symptom_name_vectors()
    gv = _local_model().encode([t for t, *_ in grams], normalize_embeddings=True)
    sims = gv @ vecs.T
    out, g, idx = [], load_graph(), _name_index()
    for k in sims.max(axis=1).argsort()[::-1]:          # best-scoring phrases first
        best = int(sims[k].argmax())
        text, s, e = grams[k]
        if sims[k][best] < SEMANTIC_MIN_SIM or names[best] in already:
            continue
        if any(s < te and ts < e for ts, te in taken):
            continue
        ids = [i for i in idx[names[best].lower()] if g.nodes[i]["type"] == "Symptom"]
        taken.append((s, e))
        already.add(names[best])
        out.append({"name": names[best], "type": "Symptom", "ids": ids, "via": text,
                    "similarity": round(float(sims[k][best]), 3)})
    return out


STOPWORDS = {"patient", "presents", "likely", "diagnosis", "treatment", "drug", "drugs", "what", "which", "with",
             "years", "year", "old", "male", "female", "woman", "history", "since", "days", "weeks", "first", "line",
             "choice", "best", "management", "should", "given", "used", "about", "from", "this", "that", "their"}


# ---------- hops ----------
def conditions_for_symptoms(symptom_ids: list[list[str]], top: int = 5, question: str = "") -> list[dict]:
    """Rank conditions by how many symptoms point to them, then likelihood, then symptom specificity
    (inverse condition frequency: a rare symptom says more than fever). Purely from the graph; the
    textbook check that re-ranks this pool lives in rag/hops.py."""
    g, scores, hits, spec_scores = load_graph(), {}, {}, {}
    for group in symptom_ids:                          # one group = all variant nodes of one symptom
        best: dict[str, int] = {}
        # Symptom group specificity: rare symptoms have higher discriminative power
        edges = sum(1 for n in group for _, _, d in g.out_edges(n, data=True) if d.get("relation") == "PRESENT_IN")
        icf = math.log(1.0 + 1000.0 / max(edges, 1))
        for sid in group:
            for _, cid, d in g.out_edges(sid, data=True):
                if d["relation"] == "PRESENT_IN":
                    w = LIKELIHOOD.get(d.get("likelihood_condition_given_symptom", "low"), 1)
                    best[cid] = max(best.get(cid, 0), w)
        for cid, w in best.items():
            scores[cid] = scores.get(cid, 0) + w
            hits[cid] = hits.get(cid, 0) + 1
            spec_scores[cid] = spec_scores.get(cid, 0.0) + (w * icf)

    ranked = sorted(scores, key=lambda c: (hits[c], scores[c], spec_scores[c]), reverse=True)[:top]
    return [{"id": c, "name": g.nodes[c]["name"], "symptoms_matched": hits[c], "score": scores[c],
             "spec": round(spec_scores[c], 2)} for c in ranked]


def specialities_for(condition_id: str) -> list[str]:
    g = load_graph()
    return [g.nodes[t]["name"] for _, t, d in g.out_edges(condition_id, data=True) if d["relation"] == "TREATED_BY"
            and g.nodes[t]["type"] == "Speciality"]


def drugs_for(condition_id: str, max_up: int = 3) -> list[str]:
    """Drugs linked to the condition, or to its nearest ancestor concept that has any (BODHI-M CHILD_OF)."""
    g = load_graph()
    frontier, seen = [condition_id], set()
    for _ in range(max_up + 1):
        drugs = sorted({g.nodes[t]["name"] for n in frontier for _, t, d in g.out_edges(n, data=True)
                        if d["relation"] == "TREATED_BY" and g.nodes[t]["type"] == "Drug"})
        if drugs:
            return drugs
        seen.update(frontier)
        frontier = [t for n in frontier for _, t, d in g.out_edges(n, data=True)
                    if d["relation"] == "CHILD_OF" and t not in seen]
        if not frontier:
            break
    return []


if __name__ == "__main__":
    g = load_graph()
    types = {}
    for _, d in g.nodes(data=True):
        types[d["type"]] = types.get(d["type"], 0) + 1
    print(f"{g.number_of_nodes()} nodes {g.number_of_edges()} edges", types)
    q = "A patient presents with fever, joint pain and rash. What is the likely diagnosis and treatment?"
    ents = link_entities(q)
    print("linked:", [(e["name"], e["type"]) for e in ents])
    conds = conditions_for_symptoms([e["ids"] for e in ents if e["type"] == "Symptom"])
    for c in conds:
        print(f"  {c['name']:40} matched={c['symptoms_matched']} score={c['score']} "
              f"spec={specialities_for(c['id'])[:2]} drugs={drugs_for(c['id'])[:4]}")
