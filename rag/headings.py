"""Textbook headings as ontology concepts and navigation hierarchy (Milestone 1, Stage A).

Stage A is deterministic and $0 LLM spend. Implements the Section 3.0 decision list from
docs/headings_to_ontology_plan.md across all 3,135 ToC nodes (2,675 section leaves) in the 7 textbooks.
Built by `build_headings()` into `data/graph/headings.jsonl`.

Tiers:
- T1 certified: LLM-extracted fact with verified verbatim quote (ontology_facts only).
- T2 derived: Deterministic rule over ToC or certified facts (primary topic, case link, cross-book bridge).
- T3 candidate: Heuristic / candidate heading concept (part_of candidate, new concept candidate).
- navigation: Book structure, facet, position, procedure, hub.

HARD GATE:
No record from this module may reach an answer prompt (graph_block). All records in headings.jsonl
have tier in ("T2", "T3", "navigation") and NEVER "T1". Generic facet headings (FACET_EXACT) are
strictly filtered before entity matching so structural terms like "Joints", "Nerves", "Arteries",
and "Toxicity" are never promoted to entities.
"""
from __future__ import annotations

import collections
import functools
import json
from pathlib import Path
import re
from typing import Any

from ontology.merge import merge_key
from rag import atlas, ontology_facts as o

PATH = Path("data/graph/headings.jsonl")
BOOKS = ("davidson", "grays", "guyton", "harrison", "micro", "robbins", "tripathi")

BOOK_EXPECTED_TYPES: dict[str, tuple[str, ...]] = {
    "grays": ("AnatomicalStructure",),
    "tripathi": ("TherapeuticAgent",),
    "guyton": ("PhysiologicalProcess",),
    "harrison": ("PathologicalCondition", "ClinicalPhenotype"),
    "robbins": ("PathologicalCondition",),
    "davidson": ("PathologicalCondition",),
    "micro": ("PathologicalCondition", "EtiologicalAgent"),
}

# Types a heading may plausibly link to, per book. A candidate of any other type is dropped, even when it is the
# only one ("Pulmonary valve" must not link to the TherapeuticAgent "Pulmonary valve replacement").
BOOK_PLAUSIBLE_TYPES: dict[str, tuple[str, ...]] = {
    "grays": ("AnatomicalStructure", "OrganSystem", "PathologicalCondition", "ClinicalPhenotype"),
    "tripathi": ("TherapeuticAgent", "PathologicalCondition", "ClinicalPhenotype", "PhysiologicalProcess",
                 "EtiologicalAgent"),
}
# Gray's headings that FACET_EXACT would swallow but that name real structures in Gray's (singular "Bone" in the
# skeletal system chapter, "Fascia" of a region). Gray's facet headings use the plural "Bones".
GRAYS_STRUCTURE_HEADINGS = {"bone", "fascia"}

FRONT = re.compile(
    r"^(bibliography|acknowledg\w*|appendi\w*|telephone numbers|index|notes on individual \w+|references|further reading|[a-z])$",
    re.I,
)
CASE = re.compile(r"^case\s+\d+\s*(?::\s*(.+))?$", re.I)

# 91 curated generic facet headings: facets of parent, never entities
FACET_EXACT = {
    "overview", "introduction", "summary", "conceptual overview", "general description",
    "key features", "component parts", "relationship to other regions", "functions", "function",
    "surface anatomy", "regional anatomy", "in the clinic", "clinical cases", "general",
    "definition", "epidemiology", "investigations", "investigation", "nerves", "muscles",
    "innervation", "vessels", "arteries", "veins", "lymphatics", "lymphatic drainage",
    "venous drainage", "arterial supply", "arterial supply and venous drainage",
    "arteries and veins", "blood supply", "vasculature", "bones", "bone", "joints", "ligaments",
    "branches", "contents", "boundaries", "skeletal framework", "bony framework", "fascia",
    "blood vessels", "vascular supply and innervation", "innervation and blood supply",
    "other vasculature", "organs", "viscera", "regions", "external features", "internal features",
    "uses", "use", "adverse effects", "side effects", "interactions", "drug interactions",
    "pharmacokinetics", "actions", "mechanism of action", "action and mechanism",
    "pharmacological actions", "therapeutic uses", "precautions and contraindications",
    "adverse effects and precautions", "administration and preparations",
    "preparations, dose, administration", "toxicity", "toxic effects", "treatment", "absorption",
    "distribution", "pathogenesis", "clinical features", "management",
    "functional anatomy and physiology", "functional subdivisions of the cns",
    "anterior view", "posterior view", "lateral view", "superior view", "inferior view",
    "vessels and nerves", "other muscles or muscle groups", "pulse points", "gateways",
    "function of the larynx", "cardiac uses", "central uses", "vascular uses",
    "by prolonging absorption from site of administration", "practical considerations",
    "choice of treatment", "topical therapy", "pharmacodynamic interactions",
    "pharmacokinetic interactions", "drug factors", "patient factors",
    "organism-related considerations", "complications", "prognosis",
}

POSITIONAL_ONLY = re.compile(
    r"^((anterior|posterior|medial|lateral|superior|inferior|superficial|deep)\s+)?"
    r"(wall|compartment|layer|floor|roof|group|border|surface|aspect|part|region)s?$|"
    r"^(first|second|third|fourth|fifth) layer$|^(roof|floor|borders and ceiling|walls.*|roof.*)$",
    re.I,
)
STATEMENT = re.compile(r"\b(is|are|was|were|passes|pass|supplied|innervate[sd]?|drains?)\b", re.I)
PROCEDURAL = re.compile(
    r"^(how to|identifying|visualizing|estimating|locating|position of|normal appearance|motor function)\b",
    re.I,
)
CLASSWORDS = re.compile(
    r"(drugs?|agents?|antibiotics?|inhibitors?|blockers?|antagonists?|agonists?|hormones?|vaccines?|"
    r"analogues?|derivatives|penicillins|cephalosporins|carbapenems|quinolones|sulfonamides|tetracyclines|"
    r"macrolides?|aminoglycosides?|steroids|androgens|estrogens|progestins|benzodiazepines|barbiturates|"
    r"opioids?|nsaids|anaesthetics|anesthetics|diuretics|laxatives|antihistamin\w+|anticoagulants|"
    r"antidepressants|antiemetics|antiseptics|vitamins|corticosteroids|glycosides|alkaloids|taxanes|"
    r"nitrates|thiazides|bisphosphonates|anticholinesterases|sedative\w*|monobactams|oxazolidinone|"
    r"fibrinolytics|enzymes|coagulants|chelating agents|mydriatics|cholinomimetics|sympathomimetics|insulins?)\b",
    re.I,
)
CONDWORDS = re.compile(
    r"(disease|syndrome|disorders?|itis|osis|emia|aemia|oma\b|omas\b|cancer|carcinoma|infection|failure|"
    r"deficiency|fever|injury|hypertension|hypotension|shock|stroke|diabetes|asthma|arthritis|anemia|"
    r"anaemia|leukemia|lymphoma|dementia|epilepsy|ulcer|hernia|thrombosis|embolism|infarction|aneurysm|"
    r"stenosis|regurgitation|fibrillation|tachycardia|palsy|fracture|paralysis|abscess|tumou?r|neoplasm|"
    r"sepsis|poisoning|overdose|allergy|ischemi\w+|ischaemi\w+|pneumonia|tuberculosis|hepatitis|malaria|"
    r"measles|influenza|leprosy|tetanus|cholera|fibrosis|cirrhosis|edema|oedema|atrophy|hyperplasia|"
    r"dysplasia|dystrophy|neuropathy|myopathy|retinopathy|nephropathy|cardiomyopathy|sclerosis|amyloidosis|"
    r"gout|colic|ascites|jaundice|pain|dyspnea|cough|headache|vertigo|syncope|coma|rash|bleeding|hemorrhage|"
    r"haemorrhage|rupture|torsion|tamponade|obstruction|occlusion|stone|calculi|polyps?)(?:s|es)?\b",
    re.I,
)
PROCESSWORDS = re.compile(
    r"\b(regulation|control|secretion|metabolism|transport|transmission|potential|excitation|contraction|"
    r"reflex\w*|homeostasis|filtration|reabsorption|synthesis|signaling|signalling|response|mechanism\w*|"
    r"circulation|flow|exchange|absorption|digestion|conduction|pathway\w*|cycle|rhythm|balance|formation|"
    r"function of|physiology|coagulation|hemostasis|haemostasis|respiration|ventilation|diffusion|osmosis|"
    r"action potential|sleep|motility|reproduction|lactation|growth|aging|ageing|differentiation|apoptosis|"
    r"inflammation|repair|healing|activation|release|uptake|clearance|binding|pathogenesis|biosynthesis|"
    r"oxidation|phosphorylation)\b",
    re.I,
)

PRE = re.compile(
    r"^(the|overview of|approach to the patient with|approach to|diseases of the|diseases of|"
    r"disorders of the|disorders of|infections of the|infections of|tumou?rs of the|tumou?rs of|"
    r"physiology of|anatomy of|principles of|management of|treatment of|clinical examination of the|"
    r"investigation of|presenting problems in)\s+",
    re.I,
)
SUF = re.compile(r"\s*(\[[ivx0-9]+\]|:\s*(management|diagnosis.*|clinical.*|pathophysiology.*|overview))$", re.I)


def clean_heading(h: str) -> str:
    """Strip section/part prefixes, numbering, Roman numerals, and standardize casing."""
    h = h.strip()
    h = re.sub(r"^(SECTION|Section|PART|Part|Unit|UNIT)\s+[0-9IVXivx]+\s*[:.\-–]?\s*", "", h)
    h = re.sub(r"^\d+\s*[.]?\s+", "", h)
    h = re.sub(r"^\d+[a-z]\.\s+", "", h)  # Tripathi "17a. Introduction", "41b. Diuretics"
    h = re.sub(r"^[IVX]+\.\s+", "", h)
    h = h.rstrip(".").strip()
    if h.isupper() and len(h) > 3:
        h = h.capitalize()
    return h


def strip_possessive(h: str) -> str:
    """"Hodgkin's Lymphoma" -> "Hodgkin Lymphoma", so eponyms match nodes labelled without the possessive."""
    return re.sub(r"(?<=\w)['\u2019]s\b", "", h)


def _key(text: str) -> str:
    """Matching key for headings and ontology labels: merge_key with possessives removed."""
    return merge_key(strip_possessive(text))


def paren_split(h: str) -> tuple[str, list[str]]:
    """Extract parenthetical contents and main string."""
    m = re.findall(r"\(([^)]*)\)", h)
    main = re.sub(r"\([^)]*\)", "", h).strip(" ,:-–—")
    return main, m


def slugify(text: str) -> str:
    """Generate a clean slug identifier from heading text."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:50]


@functools.cache
def _entity_index() -> tuple[
    dict[str, dict[str, tuple[str, str]]],
    dict[str, dict[str, tuple[str, str]]],
    collections.Counter[str],
    dict[str, set[str]],
]:
    """Index certified ontology facts: (ent, ent_without_parens, degree, book_facts)."""
    ent: dict[str, dict[str, tuple[str, str]]] = collections.defaultdict(dict)
    ent_p: dict[str, dict[str, tuple[str, str]]] = collections.defaultdict(dict)
    degree: collections.Counter[str] = collections.Counter()
    book_facts: dict[str, set[str]] = collections.defaultdict(set)

    for f in o.facts():
        bks = o.books(f)
        for s in ("subject", "object"):
            nid, lab, t = f[s + "_id"], f[s + "_label"], f[s + "_type"]
            k = _key(lab)
            ent[k][nid] = (lab, t)
            if "(" in lab:
                kp = _key(re.sub(r"\([^)]*\)", "", lab))
                ent_p[kp][nid] = (lab, t)
            degree[nid] += 1
            for b in bks:
                book_facts[b].add(nid)

    return ent, ent_p, degree, book_facts


def match_heading(h: str) -> tuple[str | None, set[str], list[tuple[str, str, str]]]:
    """Strict entity matching against certified ontology: (match_type, types_set, candidates)."""
    ent, ent_p, _, _ = _entity_index()
    h = strip_possessive(h)
    k = merge_key(h)
    if k and k in ent:
        cands = [(nid, lab, t) for nid, (lab, t) in ent[k].items()]
        return "exact", {t for _, _, t in cands}, cands

    main, par = paren_split(h)
    # a drug-class word after the parenthesis: "Dipeptidyl peptidase-4 (DPP-4) inhibitors"
    trailing = bool(re.search(r"\)\s*(inhibitors?|blockers?|antagonists?|agonists?|activators?|modulators?)\s*$", h, re.I))
    alias_cands: list[str] = []
    if trailing:
        # the parenthesis is an abbreviation inside the name, not an alias of the whole heading:
        # try "DPP-4 inhibitors", never the bare "DPP-4" (that is the enzyme, not the drug class)
        for m in re.finditer(r"\(([^)]*)\)\s*([^()]+)", h):
            alias_cands.append(f"{m.group(1)} {m.group(2)}")
    else:
        alias_cands = [p for a in par for p in re.split(r"[;,]", a)]
    for cand in [main] + alias_cands:
        cand = cand.strip()
        if not cand:
            continue
        ck = merge_key(cand)
        if ck in ent:
            cands = [(nid, lab, t) for nid, (lab, t) in ent[ck].items()]
            return "paren", {t for _, _, t in cands}, cands

    if k in ent_p:
        cands = [(nid, lab, t) for nid, (lab, t) in ent_p[k].items()]
        return "paren", {t for _, _, t in cands}, cands

    for v in atlas.variants(main or h):
        if v in ent:
            cands = [(nid, lab, t) for nid, (lab, t) in ent[v].items()]
            return "variant", {t for _, _, t in cands}, cands

    return None, set(), []


def match_heading_for_book(book: str, h: str) -> tuple[str | None, set[str], list[tuple[str, str, str]]]:
    """match_heading, then keep only candidates of a type the book's headings can plausibly name."""
    m, types, cands = match_heading(h)
    plausible = BOOK_PLAUSIBLE_TYPES.get(book)
    if not plausible or not cands:
        return m, types, cands
    cands = [c for c in cands if c[2] in plausible]
    if not cands:
        return None, set(), []
    return m, {t for _, _, t in cands}, cands


def relaxed_match(h: str) -> tuple[str | None, set[str], list[tuple[str, str, str]]]:
    """Rule 1 relaxed matching: prefix/suffix strip, anatomical variations."""
    ent, _, _, _ = _entity_index()
    h0 = strip_possessive(re.sub(r"\([^)]*\)", "", h)).strip()
    cands_str: list[str] = []
    x = SUF.sub("", h0)
    cands_str.append(x)
    y = PRE.sub("", x)
    cands_str.append(y)
    m_an = re.search(r"(muscle|nerve|artery|vein)s?$", y, re.I)
    if m_an:
        cands_str.append(re.sub(r"\s+(muscle|nerve|artery|vein)s?$", "", y, flags=re.I) + " " + m_an.group(1))

    for c in cands_str:
        if not c:
            continue
        k = merge_key(c)
        if k in ent:
            cands = [(nid, lab, t) for nid, (lab, t) in ent[k].items()]
            return "relaxed", {t for _, _, t in cands}, cands
        for v in atlas.variants(c):
            if v in ent:
                cands = [(nid, lab, t) for nid, (lab, t) in ent[v].items()]
                return "relaxed", {t for _, _, t in cands}, cands

    return None, set(), []


def disambiguate_candidates(book: str, candidates: list[tuple[str, str, str]]) -> tuple[str, str, str]:
    """Disambiguate matching concept nodes by book-expected type, book fact presence, and degree."""
    if not candidates:
        return ("", "", "")
    unique: dict[str, tuple[str, str, str]] = {}
    for nid, lab, typ in candidates:
        if nid not in unique:
            unique[nid] = (nid, lab, typ)
    cands = list(unique.values())
    if len(cands) == 1:
        return cands[0]

    _, _, degree, book_facts = _entity_index()

    # 1. Book expected type
    expected = BOOK_EXPECTED_TYPES.get(book, ())
    by_type = [c for c in cands if c[2] in expected]
    if by_type:
        cands = by_type
    if len(cands) == 1:
        return cands[0]

    # 2. Book facts presence
    bf = book_facts.get(book, set())
    by_book = [c for c in cands if c[0] in bf]
    if by_book:
        cands = by_book
    if len(cands) == 1:
        return cands[0]

    # 3. Highest degree, tie-break by label
    cands.sort(key=lambda c: (-degree[c[0]], c[1]))
    return cands[0]


def classify_heading(r: dict) -> tuple[str, str | None]:
    """Deterministic classifier implementing the Section 3.0 decision list.

    CRITICAL HARD GATE: FACET_EXACT runs BEFORE entity matching (r.get('match')),
    preventing generic terms like 'Joints', 'Nerves', 'Arteries', 'Toxicity'
    from ever being linked as entities.
    """
    h = r["clean"]
    b = r["book"]
    h2 = re.sub(r"^chapter\s+\d+\s*", "", h, flags=re.I)
    k2 = re.sub(r"\s+", " ", h2.lower()).strip()

    # 1. Front/back matter, bare letters, structural
    if FRONT.match(h) or r["level"] == 0:
        return "structural", None

    # 2. Case
    m = CASE.match(h)
    if m:
        return ("case_cond" if m.group(1) else "case_bare"), None

    # 3. CRITICAL HARD GATE: Facet filter strictly before match
    if k2 in FACET_EXACT and not (b == "grays" and k2 in GRAYS_STRUCTURE_HEADINGS):
        return "facet", None

    # 4. Positional / procedural
    if b == "grays" and POSITIONAL_ONLY.match(h):
        return "positional", None
    if b == "grays" and (PROCEDURAL.match(h) or (len(h.split()) >= 6 and STATEMENT.search(h))):
        return "procedural", None

    # 5. Entity match (strict)
    if r.get("match"):
        mtypes = r.get("mtypes", [])
        return "matched", (mtypes[0] if mtypes else None)

    # 6. Topic headings
    if (
        re.match(
            r"^(clinical examination|approach|principles|presenting problems|investigation|"
            r"general (principles|considerations|pharmacological)|aspects of|evidence|rational|introduction)",
            h2,
            re.I,
        )
        or (
            b == "tripathi"
            and re.match(
                r"^(treatment of|prophylaxis|drugs (for|used)|choice of|uses and|drug therapy|use of|"
                r"complications|combinations|mechanism|mechanisms|disadvantages|urinary|types of|preparations|notes|new )",
                h2,
                re.I,
            )
        )
        or (
            b == "davidson"
            and re.match(
                r"^(clinical|common|specialist|daily|stabilisation|comprehensive|bedside|use and|dealing|death|"
                r"humanitarian|under water|extremes|health|social)",
                h2,
                re.I,
            )
        )
    ):
        return "topic", None

    # 7. Group class (Tripathi)
    if b == "tripathi" and CLASSWORDS.search(h):
        return "group_class", "TherapeuticAgent"

    # 8. Group headings
    if (
        re.match(
            r"^(diseases|disorders|infections|infective syndromes|tumou?rs|neoplasms|miscellaneous|other|"
            r"specific|special|systemic|the \w+ (system|tract)|cardiovascular|respiratory|nervous|endocrine|environmental)\b",
            h2,
            re.I,
        )
        or (r["n_children"] >= 3 and r["level"] <= 2)
        or r["level"] == 1
    ):
        return "group", None

    # 9. Everything else is an entity candidate (T3), except these topic-like headings
    if b == "grays" and re.search(
        r"imaging|interpretation|safety|differences|anatomical position|techniques|arrangement of|estimating|what is", h, re.I
    ) and not re.search(r"\bsystems?$", h, re.I):
        return "topic", None
    if b == "tripathi":
        words = re.sub(r"\([^)]*\)", "", h).split()
        if (PROCESSWORDS.search(h) and r["level"] >= 3) or CONDWORDS.search(h) or (len(words) <= 2 and r["level"] >= 3):
            return "entity", None
        return "topic", None
    return "entity", None


def parse_heading_tree() -> list[dict]:
    """Parse all 3,135 ToC nodes across the 7 books from data/okf/{book}/toc.json."""
    raw_recs: list[dict] = []
    for b in BOOKS:
        toc_file = Path(f"data/okf/{b}/toc.json")
        if not toc_file.exists():
            continue
        toc = json.loads(toc_file.read_text(encoding="utf-8"))
        secid: dict[tuple[str, ...], str] = {}
        nodes: dict[tuple[str, ...], None] = {}
        for x in toc:
            parts = tuple(x["path"].split(" › "))
            secid[parts] = x["id"]
            for i in range(2, len(parts) + 1):
                nodes.setdefault(parts[:i], None)
        for n in nodes:
            raw = n[-1]
            raw_recs.append({
                "book": b,
                "level": len(n) - 1,
                "raw": raw,
                "clean": clean_heading(raw),
                "parent": clean_heading(n[-2]) if len(n) > 2 else "",
                "path": list(n),
                "section_id": secid.get(n),
                "is_section": n in secid,
            })

    paths = set(tuple(r["path"]) for r in raw_recs)
    kids: collections.Counter[tuple[str, ...]] = collections.Counter()
    for p in paths:
        if len(p) > 2:
            kids[p[:-1]] += 1
    for r in raw_recs:
        r["n_children"] = kids.get(tuple(r["path"]), 0)

    for r in raw_recs:
        m, t, cands = match_heading_for_book(r["book"], r["clean"])
        r["match"] = m
        r["mtypes"] = sorted(t)
        r["cands"] = cands
        c, ty = classify_heading(r)
        r["cls"] = c
        r["ctype"] = ty

    return raw_recs


def build_headings(output_path: Path | str = PATH) -> list[dict]:
    """Build data/graph/headings.jsonl conforming to the Stage A specification."""
    raw_recs = parse_heading_tree()
    _, _, _, book_facts = _entity_index()

    rows: list[dict] = []
    for r in raw_recs:
        b = r["book"]
        lvl = r["level"]
        subpath = "-".join(slugify(p) for p in r["path"][1:])
        heading_id = f"{b}:{subpath}:{lvl}"

        parent_id = None
        if lvl > 1:
            psubpath = "-".join(slugify(p) for p in r["path"][1:-1])
            parent_id = f"{b}:{psubpath}:{lvl - 1}"

        cls = r["cls"]
        section_id = r["section_id"]
        evidence = section_id if section_id else " › ".join(r["path"])

        concept_ids: list[str] = []
        concept_label: str | None = None
        facet: str | None = None
        tier: str = "navigation"
        method: str = f"rule:{cls}"

        if cls == "matched":
            tier = "T2"
            winner = disambiguate_candidates(b, r.get("cands", []))
            if winner[0]:
                concept_ids = [winner[0]] + [c[0] for c in r.get("cands", []) if c[0] != winner[0]]
                concept_label = winner[1]
                # Rule 1 generic single-word mitigation:
                if len(r["clean"].split()) == 1 and b != "tripathi" and winner[0] not in book_facts[b]:
                    method = "rule1:heading-bridge"
                else:
                    match_type = r.get("match", "exact")
                    method = f"rule1:heading-{match_type}"

        elif cls == "case_cond":
            tier = "T2"
            method = "rule8:case"
            m = CASE.match(r["clean"])
            cond = m.group(1).strip() if m and m.group(1) else None
            if cond:
                _, _, cond_cands = match_heading_for_book("grays", cond)
                if cond_cands:
                    winner = disambiguate_candidates("grays", cond_cands)
                    concept_ids = [winner[0]]
                    concept_label = winner[1]
                else:
                    concept_label = cond

        elif cls == "facet":
            tier = "navigation"
            method = "rule3:facet"
            facet = r["clean"].lower()

        elif cls == "entity":
            tier = "T3"
            method = "rule2:candidate"

        elif cls in ("group", "group_class", "topic", "positional", "procedural", "structural", "case_bare"):
            tier = "navigation"
            method = f"rule:{cls}"

        # Hard invariant: T1 must NEVER occur
        assert tier in ("T2", "T3", "navigation"), f"Forbidden tier {tier} on {heading_id}"

        record = {
            "heading_id": heading_id,
            "book": b,
            "section_id": section_id,
            "level": lvl,
            "raw": r["raw"],
            "clean": r["clean"],
            "class": cls,
            "facet": facet,
            "concept_ids": concept_ids,
            "concept_label": concept_label,
            "parent_id": parent_id,
            "tier": tier,
            "method": method,
            "evidence": evidence,
            "path": r["path"],
            "is_section": r["is_section"],
            "n_children": r["n_children"],
        }
        rows.append(record)

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    _load.cache_clear()
    return rows


@functools.cache
def _load() -> tuple[
    list[dict],
    dict[str, dict],
    dict[str, dict],
    dict[str, list[dict]],
    dict[str, list[dict]],
    dict[str, list[dict]],
]:
    """Cached loader returning (rows, by_heading_id, by_section_id, by_concept_id, by_parent_id, by_book)."""
    if not PATH.exists():
        return [], {}, {}, {}, {}, {}

    rows: list[dict] = []
    by_heading_id: dict[str, dict] = {}
    by_section_id: dict[str, dict] = {}
    by_concept_id: dict[str, list[dict]] = collections.defaultdict(list)
    by_parent_id: dict[str, list[dict]] = collections.defaultdict(list)
    by_book: dict[str, list[dict]] = collections.defaultdict(list)

    for line in PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append(r)
        by_heading_id[r["heading_id"]] = r
        if r.get("section_id"):
            by_section_id[r["section_id"]] = r
        for cid in r.get("concept_ids", []):
            by_concept_id[cid].append(r)
        if r.get("parent_id"):
            by_parent_id[r["parent_id"]].append(r)
        by_book[r["book"]].append(r)

    return rows, by_heading_id, by_section_id, dict(by_concept_id), dict(by_parent_id), dict(by_book)


# --- Query APIs ---

def primary_topic(section_id: str, allow_bridge: bool = False) -> dict | None:
    """Return the primary topic heading record for a section leaf, or None."""
    rec = _load()[2].get(section_id)
    if not rec:
        return None
    if rec.get("class") == "matched":
        if allow_bridge or rec.get("method") != "rule1:heading-bridge":
            return dict(rec)
    return None


def section_heading(section_id: str) -> dict | None:
    """Return the heading record corresponding to a section ID."""
    rec = _load()[2].get(section_id)
    return dict(rec) if rec else None


def headings_for_concept(concept_id: str) -> list[dict]:
    """Return heading records associated with an ontology concept ID."""
    return [dict(r) for r in _load()[3].get(concept_id, [])]


def facets_for(heading_id: str) -> list[dict]:
    """Return child facet headings attached to a parent heading."""
    return [dict(r) for r in _load()[4].get(heading_id, []) if r.get("class") == "facet"]


def subtopics(heading_id: str, include_facets: bool = False) -> list[dict]:
    """Return child headings in the hierarchy attached to a parent heading."""
    children = _load()[4].get(heading_id, [])
    if include_facets:
        return [dict(r) for r in children]
    return [dict(r) for r in children if r.get("class") not in ("facet", "structural", "positional")]


def part_of_candidates(book: str = "grays") -> list[dict]:
    """Return Gray's anatomy part_of candidates (entity-like child under entity-like parent)."""
    rows, by_hid, _, _, by_pid, _ = _load()
    candidates: list[dict] = []
    for r in rows:
        if r["book"] != book or r["level"] < 3:
            continue
        if r.get("class") not in ("entity", "matched"):
            continue
        pid = r.get("parent_id")
        if not pid or pid not in by_hid:
            continue
        parent = by_hid[pid]
        if parent.get("class") in ("entity", "matched"):
            candidates.append({
                "child_id": r["heading_id"],
                "child_label": r["clean"],
                "parent_id": parent["heading_id"],
                "parent_label": parent["clean"],
                "book": book,
                "tier": "T3",
                "method": "rule4:part_of",
                "evidence": r.get("section_id") or r.get("evidence"),
            })
    return candidates


def parenthetical_aliases() -> list[dict]:
    """Extract and categorize abbreviations, synonyms, alias matches, and merge proposals."""
    rows = _load()[0]
    out: list[dict] = []
    for r in rows:
        h = r["clean"]
        if "(" not in h or r.get("class") == "structural":
            continue
        main, par = paren_split(h)
        if not par:
            continue
        aliases = [a.strip() for p in par for a in re.split(r"[;,]| or ", p) if a.strip()]
        abbrevs = [
            a for a in aliases
            if re.match(r"^[A-Z][A-Za-z0-9\-/]{1,7}$|^[A-Z]{1,6}$", a) and not re.search(r"\s", a)
        ]
        syns = [a for a in aliases if a not in abbrevs]

        m_main, _, _ = match_heading(main)
        m_aliases = [match_heading(a)[0] for a in aliases]
        alias_only = (not m_main) and any(m_aliases)

        merge_prop = False
        if m_main and any(m_aliases):
            first_matched_alias = next(a for a, m in zip(aliases, m_aliases) if m)
            if merge_key(main) != merge_key(first_matched_alias):
                merge_prop = True

        out.append({
            "heading_id": r["heading_id"],
            "book": r["book"],
            "raw": r["raw"],
            "clean": r["clean"],
            "main": main,
            "aliases": aliases,
            "abbreviations": abbrevs,
            "synonyms": syns,
            "main_match": m_main,
            "alias_matches": [a for a, m in zip(aliases, m_aliases) if m],
            "alias_only_match": alias_only,
            "merge_proposal": merge_prop,
            "tier": "T2",
        })
    return out


def cross_book_headings() -> list[dict]:
    """Return identical headings appearing in 2+ books (excluding facets and structural)."""
    rows = _load()[0]
    ent, _, _, _ = _entity_index()
    by_key: dict[str, dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in rows:
        if r["level"] < 1 or r.get("class") in ("facet", "structural", "case_bare", "positional", "procedural"):
            continue
        k = _key(re.sub(r"\([^)]*\)", "", r["clean"]))
        if k:
            by_key[k][r["book"]].append(r)

    out: list[dict] = []
    for k, bmap in sorted(by_key.items()):
        if len(bmap) >= 2:
            out.append({
                "key": k,
                "books": sorted(bmap.keys()),
                "heading_ids": [r["heading_id"] for b in sorted(bmap.keys()) for r in bmap[b]],
                "headings": [r["clean"] for b in sorted(bmap.keys()) for r in bmap[b]],
                "in_ontology": k in ent,
                "tier": "T2",
            })
    return out


def all_headings(book: str | None = None, cls: str | None = None) -> list[dict]:
    """Return all headings, optionally filtered by book and/or heading class."""
    rows = _load()[0]
    out = []
    for r in rows:
        if book and r.get("book") != book:
            continue
        if cls and r.get("class") != cls:
            continue
        out.append(dict(r))
    return out


if __name__ == "__main__":
    print(f"Building {PATH}...")
    built = build_headings()
    print(f"Successfully generated {len(built)} headings.")
    leaves = [r for r in built if r.get("is_section")]
    print(f"Total section leaves: {len(leaves)}")
    by_cls = collections.Counter(r["class"] for r in built)
    print("Class breakdown:")
    for c, cnt in sorted(by_cls.items(), key=lambda x: -x[1]):
        print(f"  {c:15s}: {cnt:4d}")
    pts = [r for r in leaves if r["class"] == "matched"]
    print(f"Leaf primary topics matched: {len(pts)} ({len(pts) / len(leaves):.1%})")
