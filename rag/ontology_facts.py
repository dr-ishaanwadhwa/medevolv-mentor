"""Query layer over the certified clinical ontology (data/ontology/clinical_ontology.jsonl).

Only CERTIFIED facts are used: their quote was found verbatim in the source section (see ontology/reconciler.py).
Everything here returns [] / {} when the file is missing, so the app still works without the ontology.

    match_conditions("Pulmonary tuberculosis")   -> ["Tuberculosis"]
    first_line_drugs_for("Tuberculosis")          -> [fact, ...]
    profile("Tuberculosis")                       -> {"presentation": [...], "therapy": {...}, ...}
    catalog()                                      -> {organ system: {category: {condition: n_facts}}}
    books(fact) / corroboration(fact)              -> ["davidson", "harrison"] / 2  (books that state it)
    contradictions_for("Tuberculosis")             -> [{"kind", "condition", "drug"/"by_book", "note", ...}]
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
    (r"seizure|epilep", "Nervous system & psychiatry", "Epilepsy & seizures"),
    (r"neurology", "Nervous system & psychiatry", "Neurology (general)"),
    (r"salmonell|enteric", "Infectious", "Enteric fever & salmonellosis"),
    (r"arthropod|arbovir|hemorrhagic|haemorrhagic|dengue", "Infectious", "Arboviral fevers"),
    (r"infectious disease", "Infectious", "Infectious disease (general)"),
    # System-level rules (category None = use the source chapter's own title, like the book's contents page)
    (r"heart|cardiac|cardiolog|hypertension|antianginal|anti-ischaemic|blood vessels|antiadrenergic|"
     r"antihypertensive|hypolipid", "Cardiovascular", None),
    (r"pneumonia|lung|asthma|cough|respirat", "Respiratory", None),
    (r"kidney|nephro|dialysis|renal", "Renal & urinary", None),
    (r"thyroid|endocrin|obesity|menopaus|androgen|estrogen|progestin|corticosteroid|vitamin|nutritional|"
     r"biochem|metabolic|insulin|glucagon", "Endocrine & metabolic", None),
    (r"mening|migraine|headache|dementia|subarachnoid|central nervous|mental illness|antipsychotic|"
     r"antidepress|cholinergic|parkinson|hydroxytryptamine|\bpain\b", "Nervous system & psychiatry", None),
    (r"hepat|liver|peptic|gastro|constipation|diarrh", "Gastrointestinal & liver", None),
    (r"anaemi|anemi|antiphospholipid|immunosuppress", "Blood & immunology", None),
    (r"antirheumatoid|antigout|rheumat", "Musculoskeletal & rheumatology", None),
    (r"fungal|antimicrobial|antiprotozoal|antiamoebic|antileprotic|vaccine|hiv|antibacterial|macrolide",
     "Infectious", None),
    (r"virolog|bacteriolog|antiviral|antimalarial|sexually transmitted|infections?\b|streptococ|staphylococ|"
     r"pertussis|malaria|brucell|leptospir", "Infectious", None),
    (r"acute medicine|critical illness|critical care", "Critical care", None),
    (r"maternal|obstetric|pregnan", "Reproductive & breast", None),
    (r"haematolog|hematolog|transfusion|immunolog", "Blood & immunology", None),
    (r"antiarrhythmic|arrhythm", "Cardiovascular", None),
    (r"calcium balance|bone|parathyroid", "Endocrine & metabolic", None),
    (r"nonsteroidal|analgesic|antipyretic", "Musculoskeletal & rheumatology", None),
    (r"poison|environmental", "Toxicology & environment", None),
    (r"dermatolog|skin", "Skin", None),
    (r"cell injury|inflammation and repair", "General pathology", None),
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
    the most facts. Returned: that group, the best-documented candidate's group (so 'acute myocardial infarction'
    also gets STEMI's facts), and every exact-name label."""
    k = _keys(name)
    if not k:
        return []
    n = _counts()
    cands = [c for c in condition_labels() if (kc := _keys(c))
             and (kc == k or kc < k or (k < kc and len(kc - k) <= 2))]
    if not cands:
        return []
    best = max(cands, key=lambda c: (_keys(c) == k and n[c] >= 5, n[c]))
    # best-documented MORE SPECIFIC (or same) label, e.g. STEMI for 'acute myocardial infarction'; never a more
    # general one (that would give 'type 1 diabetes' the type 2 drugs filed under plain 'diabetes mellitus')
    richest = max((c for c in cands if _keys(c) > k and n[c] >= 5), key=lambda c: n[c], default=best)
    groups = {_keys(best), _keys(richest), k}
    # the winner's concept group, the best-documented related label, and any exact-name labels
    return [c for c in cands if _keys(c) in groups]


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


def sources(f: dict) -> list[dict]:
    """Every textbook passage that supports the fact (older files have only the primary provenance)."""
    return f.get("sources") or [f["provenance"]]


def books(f: dict) -> list[str]:
    return sorted({p["book_id"] for p in sources(f)})


def corroboration(f: dict) -> int:
    """How many different books state this fact. UI: show "stated in N books" when N >= 2."""
    return len(books(f))


def cite_all(f: dict) -> str:
    """One citation per book, e.g. 'Harrison's ..., p. 12; Davidson's ..., p. 40'."""
    seen, out = set(), []
    for p in sources(f):
        if p["book_id"] not in seen:
            seen.add(p["book_id"])
            out.append(cite({"provenance": p}))
    return "; ".join(out)


def _dedupe(fs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in sorted(fs, key=corroboration, reverse=True):     # stable: facts stated by more books come first
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


# Harrison 22e: chapter-number ranges from the book's own PART/SECTION tree (data/okf/harrison section_path).
HARRISON_SYSTEMS = [
    (1, 13, "General medicine"), (14, 33, "Cardinal symptoms & signs"), (34, 38, "Eye, ENT & oral"),
    (39, 58, "Cardinal symptoms & signs"), (59, 64, "Skin"), (65, 70, "Cardinal symptoms & signs"), (71, 72, "General medicine"),
    (73, 100, "Oncology"), (101, 123, "Blood & immunology"), (124, 242, "Infectious"),
    (243, 294, "Cardiovascular"), (295, 310, "Respiratory"), (311, 318, "Critical care"),
    (319, 331, "Renal & urinary"), (332, 359, "Gastrointestinal & liver"), (360, 381, "Blood & immunology"),
    (382, 387, "Musculoskeletal & rheumatology"), (388, 432, "Endocrine & metabolic"),
    (433, 468, "Nervous system & psychiatry"), (469, 478, "Toxicology & environment"), (479, 505, "General medicine"),
]
ROBBINS_SYSTEMS = {
    1: "General pathology", 2: "General pathology", 3: "General pathology", 4: "Cardiovascular",
    5: "General pathology", 6: "Blood & immunology", 7: "Oncology", 8: "Infectious", 9: "Toxicology & environment",
    10: "General pathology", 11: "Cardiovascular", 12: "Cardiovascular", 13: "Blood & immunology",
    14: "Blood & immunology", 15: "Respiratory", 16: "Eye, ENT & oral", 17: "Gastrointestinal & liver",
    18: "Gastrointestinal & liver", 19: "Gastrointestinal & liver", 20: "Renal & urinary",
    21: "Renal & urinary", 22: "Reproductive & breast", 23: "Reproductive & breast", 24: "Endocrine & metabolic",
    25: "Skin", 26: "Musculoskeletal & rheumatology", 27: "Nervous system & psychiatry",
    28: "Nervous system & psychiatry", 29: "Eye, ENT & oral",
}


def _book_system(book: str, chapter: str) -> str | None:
    m = re.match(r"(\d+)", chapter)
    if not m:
        return None
    n = int(m.group(1))
    if book == "harrison":
        return next((s for lo, hi, s in HARRISON_SYSTEMS if lo <= n <= hi), None)
    if book == "robbins":
        return ROBBINS_SYSTEMS.get(n)
    return None


def _book_default(book: str) -> str | None:
    return "Infectious" if book == "micro" else None     # the microbiology book is all infection


def group_of(chapter: str, book: str = "") -> tuple[str, str]:
    """(organ system, category) for a source chapter. Named disease categories first (Diabetes mellitus, ...),
    then the book's own structure (Harrison parts, Robbins chapters), then system keywords; the category is
    otherwise the chapter's title, like the book's contents page."""
    title = re.sub(r"^\d+[a-z]?\.?\s*", "", chapter)[:60]
    for pattern, system, category in CHAPTER_GROUPS:
        if category and re.search(pattern, chapter, re.I):
            return system, category
    if system := _book_system(book, chapter):
        return system, title or system
    for pattern, system, category in CHAPTER_GROUPS:
        if not category and re.search(pattern, chapter, re.I):
            return system, title or system
    if system := _book_default(book):
        return system, title or system
    return "Other", title or "Other"


@functools.cache
def catalog() -> dict:
    """{organ system: {category: {condition label: n_facts}}}. A condition goes under the chapter that
    contributes most of its facts."""
    chapters: dict[str, Counter] = defaultdict(Counter)
    for f in facts():
        if f["subject_type"] in CONDITION_TYPES:
            p = f["provenance"]
            chapters[f["subject_label"]][(p.get("book_id", ""), p.get("chapter", ""))] += 1
    out: dict = defaultdict(lambda: defaultdict(dict))
    for label, cnt in chapters.items():
        book, chapter = cnt.most_common(1)[0][0]
        system, category = group_of(chapter, book)
        out[system][category][label] = sum(cnt.values())
    return {s: dict(c) for s, c in sorted(out.items())}


def _for(f: dict, label: str) -> str:
    """' for <subtype>' when a fact is about a more specific label than the one asked about
    (e.g. moxifloxacin is first-line for multidrug-resistant TB, not for TB)."""
    return "" if _keys(f["subject_label"]) == _keys(label) else f" (for {f['subject_label']})"


def graph_facts_for(condition: str, max_drugs: int = 5, max_tests: int = 3, max_warnings: int = 3) -> list[str]:
    """Short, cited fact strings about one condition for the answer prompt ([G#] evidence)."""
    labels = match_conditions(condition)
    if not labels:
        return []
    out = []
    fl = _dedupe(first_line_drugs_for(condition))[:max_drugs]
    if fl:
        out.append(f"Textbook ontology: first-line treatment for {labels[0]}: "
                   + "; ".join(f"{f['object_label']}{_for(f, labels[0])} ({cite(f)})" for f in fl) + ".")
    dx = _dedupe(diagnostics_for(condition))[:max_tests]
    if dx:
        out.append(f"Textbook ontology: {labels[0]} is confirmed by: "
                   + "; ".join(f"{f['object_label']}{_for(f, labels[0])} ({cite(f)})" for f in dx) + ".")
    for f in contraindications_for(condition)[:max_warnings]:
        sev = (f["clinical_facets"].get("contraindication_severity") or "").lower()
        why = f["clinical_facets"].get("rationale") or ""
        out.append(f"WARNING (textbook ontology): {f['object_label']} is {'strictly ' if sev == 'strict' else ''}"
                   f"contraindicated in {f['subject_label']}" + (f": {why}" if why else "") + f" ({cite(f)}).")
    return out


# ---------- Where the books differ (shown to students as "books differ, see both", never as an error) ----------

DIFFER_NOTE = "Books differ, see both."


def _contradictions(labels: set[str] | None = None) -> list[dict]:
    """Two kinds, per condition label:
    - treated_and_contraindicated: the same drug is listed as a treatment and as a contraindication (often a
      subgroup or timing nuance; both quotes are returned).
    - first_line_differs: two or more books name first-line drugs and the books share none of them."""
    tb, ci, fl = defaultdict(list), defaultdict(list), defaultdict(lambda: defaultdict(list))
    for f in facts():
        c = f["subject_label"]
        if labels is not None and c not in labels:
            continue
        if f["predicate"] == "TREATED_BY":
            tb[(c, f["object_id"])].append(f)
            if f["clinical_facets"].get("line_of_therapy") == "FIRST_LINE":
                for b in books(f):
                    fl[c][b].append(f)
        elif f["predicate"] == "CONTRAINDICATES":
            ci[(c, f["object_id"])].append(f)
    out = []
    for key in sorted(tb.keys() & ci.keys()):
        out.append({"kind": "treated_and_contraindicated", "condition": key[0],
                    "drug": tb[key][0]["object_label"], "facts": tb[key] + ci[key], "note": DIFFER_NOTE})
    for c, by_book in sorted(fl.items()):
        if len(by_book) < 2:
            continue
        drug_sets = [{f["object_id"] for f in fs} for fs in by_book.values()]
        if not set.intersection(*drug_sets):
            out.append({"kind": "first_line_differs", "condition": c,
                        "by_book": {b: sorted({f["object_label"] for f in fs}) for b, fs in by_book.items()},
                        "facts": [f for fs in by_book.values() for f in fs], "note": DIFFER_NOTE})
    return out


@functools.cache
def all_contradictions() -> tuple[dict, ...]:
    return tuple(_contradictions())


def contradictions_for(name: str) -> list[dict]:
    """Where the books differ about one condition (matched like the other helpers). UI: render each item with
    its note and both sides' citations (cite_all on item["facts"])."""
    labels = set(match_conditions(name))
    return _contradictions(labels) if labels else []
