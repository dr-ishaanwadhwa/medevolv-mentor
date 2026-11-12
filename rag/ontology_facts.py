"""Query layer over the certified clinical ontology (data/ontology/clinical_ontology.jsonl).

Only CERTIFIED facts are used: their quote was found verbatim in the source section (see ontology/reconciler.py).
Everything here returns [] / {} when the file is missing, so the app still works without the ontology.

    match_conditions("Pulmonary tuberculosis")   -> ["Tuberculosis"]
    first_line_drugs_for("Tuberculosis")          -> [fact, ...]
    profile("Tuberculosis")                       -> {"presentation": [...], "therapy": {...}, ...}
    catalog()                                      -> {organ system: {category: {condition: n_facts}}}
"""
from __future__ import annotations

import functools
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

PATH = Path("data/ontology/clinical_ontology.jsonl")
CONDITION_TYPES = {"PathologicalCondition", "ClinicalStage"}
GENERIC = {"acute", "chronic", "severe", "mild", "primary", "secondary", "disease", "disorder", "syndrome",
           "infection", "infections", "pulmonary", "fever", "with", "without", "type", "unspecified", "general"}
LINE_ORDER = ["FIRST_LINE", "SECOND_LINE", "ADJUNCT", "REFRACTORY", "SUPPORTIVE", None]
LINE_LABEL = {"FIRST_LINE": "First line", "SECOND_LINE": "Second line", "ADJUNCT": "Adjunct",
              "REFRACTORY": "Refractory", "SUPPORTIVE": "Supportive", None: "Other"}

# Source chapter -> (organ system, disease category). Presentation grouping for the drill-down only;
# never used for ranking or answering.
CHAPTER_GROUPS = [
    (r"diabet", "Endocrine & metabolic", "Diabetes mellitus"),
    (r"myocardial|coronary", "Cardiovascular", "Acute coronary syndromes"),
    (r"hemodynamic|haemodynamic|shock|thrombo", "Cardiovascular", "Shock & haemodynamic disorders"),
    (r"tubercul|mycobact", "Infectious", "Mycobacterial infections"),
    (r"seizure|epilep", "Nervous system", "Epilepsy & seizures"),
    (r"neurology", "Nervous system", "Neurology (general)"),
    (r"salmonell|enteric", "Infectious", "Enteric fever & salmonellosis"),
    (r"arthropod|arbovir|hemorrhagic|haemorrhagic|dengue", "Infectious", "Arboviral fevers"),
    (r"infectious disease", "Infectious", "Infectious disease (general)"),
]


@functools.cache
def facts() -> tuple[dict, ...]:
    if not PATH.exists():
        return ()
    out = []
    for line in PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            if f.get("status") == "CERTIFIED":
                out.append(f)
    return tuple(out)


def available() -> bool:
    return bool(facts())


def _keys(label: str) -> frozenset:
    """Distinctive words of a name; digits are kept so 'type 1' and 'type 2' diabetes stay apart."""
    return frozenset(w for w in re.findall(r"[a-z]+|\d+", label.lower())
                     if (w.isdigit() or len(w) >= 4) and w not in GENERIC)


@functools.cache
def _counts() -> Counter:
    return Counter(f["subject_label"] for f in facts() if f["subject_type"] in CONDITION_TYPES)


@functools.cache
def condition_labels() -> tuple[str, ...]:
    """Condition labels by how many facts describe them (most-described first)."""
    c = Counter(f["subject_label"] for f in facts() if f["subject_type"] in CONDITION_TYPES)
    return tuple(label for label, _ in c.most_common())


def match_conditions(name: str) -> list[str]:
    """Ontology condition labels for one condition name, as a single concept group.

    Candidates share distinctive words with the name: the same words, a more general label (fewer words), or a
    slightly more specific one (at most 2 extra words, e.g. 'Myocardial infarction' -> 'ST-Segment Elevation
    Myocardial Infarction'). The best candidate is an exact match with at least 5 facts, otherwise the one with
    the most facts; every label with exactly the same words as it is returned with it."""
    k = _keys(name)
    if not k:
        return []
    n = _counts()
    cands = [c for c in condition_labels() if (kc := _keys(c))
             and (kc == k or kc < k or (k < kc and len(kc - k) <= 2))]
    if not cands:
        return []
    best = max(cands, key=lambda c: (_keys(c) == k and n[c] >= 5, n[c]))
    # the winner's concept group, plus any exact-name labels (they describe the asked condition itself)
    return [c for c in cands if _keys(c) == _keys(best) or _keys(c) == k]


def _about(labels: list[str] | str, predicate: str | None = None) -> list[dict]:
    labels = {labels} if isinstance(labels, str) else set(labels)
    return [f for f in facts() if f["subject_label"] in labels and (predicate is None or f["predicate"] == predicate)]


def first_line_drugs_for(name: str) -> list[dict]:
    return [f for f in _about(match_conditions(name), "TREATED_BY")
            if f["clinical_facets"].get("line_of_therapy") == "FIRST_LINE"]


def contraindications_for(name: str) -> list[dict]:
    order = {"STRICT": 0, "CAUTIONARY": 1}
    out = _about(match_conditions(name), "CONTRAINDICATES")
    return sorted(out, key=lambda f: order.get(f["clinical_facets"].get("contraindication_severity"), 2))


def diagnostics_for(name: str) -> list[dict]:
    return _about(match_conditions(name), "CONFIRMED_BY")


def cite(f: dict) -> str:
    p = f["provenance"]
    pages = p.get("pages") or []
    pg = (f"p. {pages[0]}" if len(pages) == 1 else f"pp. {pages[0]}–{pages[-1]}") if pages else ""
    chapter = re.sub(r"^\d+\.?\s*", "", p.get("chapter", ""))
    return ", ".join(x for x in (p.get("book_title", p["book_id"]), chapter, pg) if x)


def _dedupe(fs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in fs:
        key = (f["predicate"], f["object_label"].lower())
        if key not in seen:
            seen.add(key)
            out.append(f)
    return out


def profile(label: str) -> dict:
    """Every certified fact about one condition, grouped by clinical facet (for the drill-down view)."""
    fs = _about(label)
    by = defaultdict(list)
    for f in fs:
        by[f["predicate"]].append(f)
    therapy: dict[str, list[dict]] = {}
    for line in LINE_ORDER:
        items = _dedupe([f for f in by["TREATED_BY"] if f["clinical_facets"].get("line_of_therapy") == line])
        if items:
            therapy[LINE_LABEL[line]] = items
    drugs = {f["object_label"] for f in by["TREATED_BY"]}
    drug_facts = [f for f in facts() if f["subject_label"] in drugs
                  and f["predicate"] in ("CAUSES_ADVERSE_EFFECT", "TARGETS_MECHANISM")]
    return {
        "stages": _dedupe(by["HAS_CLINICAL_STAGE"]),
        "presentation": _dedupe(by["MANIFESTS_AS"]),
        "etiology": _dedupe(by["CAUSED_BY"]),
        "mechanism": _dedupe(by["DISRUPTS_PATHWAY"]),
        "diagnostics": _dedupe(by["CONFIRMED_BY"]),
        "therapy": therapy,
        "warnings": contraindications_for(label) if match_conditions(label) == [label] else _dedupe(by["CONTRAINDICATES"]),
        "differentials": _dedupe(by["DIFFERENTIAL_OF"]),
        "is_a": _dedupe(by["is_a"]),
        "drug_effects": _dedupe([f for f in drug_facts if f["predicate"] == "CAUSES_ADVERSE_EFFECT"]),
        "drug_mechanisms": _dedupe([f for f in drug_facts if f["predicate"] == "TARGETS_MECHANISM"]),
        "n_facts": len(fs),
    }


def group_of(chapter: str) -> tuple[str, str]:
    for pattern, system, category in CHAPTER_GROUPS:
        if re.search(pattern, chapter, re.I):
            return system, category
    return "Other", re.sub(r"^\d+\.?\s*", "", chapter)[:60] or "Other"


@functools.cache
def catalog() -> dict:
    """{organ system: {category: {condition label: n_facts}}}. A condition goes under the chapter that
    contributes most of its facts."""
    chapters: dict[str, Counter] = defaultdict(Counter)
    for f in facts():
        if f["subject_type"] in CONDITION_TYPES:
            chapters[f["subject_label"]][f["provenance"].get("chapter", "")] += 1
    out: dict = defaultdict(lambda: defaultdict(dict))
    for label, cnt in chapters.items():
        system, category = group_of(cnt.most_common(1)[0][0])
        out[system][category][label] = sum(cnt.values())
    return {s: dict(c) for s, c in sorted(out.items())}


def graph_facts_for(condition: str, max_drugs: int = 5, max_tests: int = 3, max_warnings: int = 3) -> list[str]:
    """Short, cited fact strings about one condition for the answer prompt ([G#] evidence)."""
    labels = match_conditions(condition)
    if not labels:
        return []
    out = []
    fl = _dedupe(first_line_drugs_for(condition))[:max_drugs]
    if fl:
        out.append(f"Textbook ontology: first-line treatment for {labels[0]}: "
                   + "; ".join(f"{f['object_label']} ({cite(f)})" for f in fl) + ".")
    dx = _dedupe(diagnostics_for(condition))[:max_tests]
    if dx:
        out.append(f"Textbook ontology: {labels[0]} is confirmed by: "
                   + "; ".join(f"{f['object_label']} ({cite(f)})" for f in dx) + ".")
    for f in contraindications_for(condition)[:max_warnings]:
        sev = (f["clinical_facets"].get("contraindication_severity") or "").lower()
        why = f["clinical_facets"].get("rationale") or ""
        out.append(f"WARNING (textbook ontology): {f['object_label']} is {'strictly ' if sev == 'strict' else ''}"
                   f"contraindicated in {f['subject_label']}" + (f": {why}" if why else "") + f" ({cite(f)}).")
    return out
