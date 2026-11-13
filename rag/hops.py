"""Multi-hop answering: BODHI graph plans the hops, the textbook supplies cited evidence for each one.

Two routes (both are the rubric's "query decomposition" enhancement):

  Graph route  -- the question mentions symptoms that link to BODHI nodes
     hop 1  symptoms -> ranked candidate conditions            (graph, cited as [G1], [G2] ...)
     hop 2  condition -> speciality + BODHI drug list           (graph)
     hop 3  "treatment / drug of choice for <condition>"        (textbook retrieval, cited as [1], [2] ...)
     cross-check: drugs named in the textbook evidence vs BODHI's drug list for that condition

  Case route -- a long vignette (35+ words) is decomposed along three clinical axes (etiology & differential,
     emergency stabilization, definitive pharmacology & contraindications); each axis that applies gets its own
     textbook query plus matching certified ontology facts. Falls back to a simpler focus/queries split.

  Decomposition route -- no symptoms linked, but the question has several parts ("compare X and Y")
     the LLM splits it into <= 3 sub-questions; each is retrieved separately so no part crowds out another

Every hop is recorded in a trace that the UI shows, so the reasoning path is visible and checkable.
"""
from __future__ import annotations

import functools
import json
import re
from dataclasses import dataclass, field

from rag import clinical_graph, config, crosswalk, ontology_facts, trace
from rag import mentions as mention_index
from rag.backends import chat
from rag.graph import conditions_for_symptoms, drugs_for, link_entities, specialities_for
from rag.retrieve import Hit, search

PER_SUBQUERY_K = 3
MAX_EVIDENCE = 9

DECOMPOSE_SYSTEM = """Split a medical student's question into the smallest set of independent sub-questions needed
to answer it (at most 3). If it is already a single question, return it unchanged as the only item.
Return JSON: {"sub_questions": ["...", "..."]}"""


@dataclass
class Hop:
    kind: str                 # "graph" | "retrieve" | "decompose"
    query: str
    result: str               # short human-readable outcome for the trace
    hits: list[Hit] = field(default_factory=list)


@dataclass
class Plan:
    route: str                # "graph" | "decompose" | "single"
    hops: list[Hop] = field(default_factory=list)
    graph_facts: list[str] = field(default_factory=list)     # cited as [G1], [G2] ...: BODHI differential/specialist + certified ontology
    nav_hints: list[str] = field(default_factory=list)       # BODHI drug links: navigation hints for the UI, NEVER in the prompt
    evidence: list[Hit] = field(default_factory=list)       # cited as [1], [2] ...
    bodhi_drugs: dict[str, list[str]] = field(default_factory=dict)
    symptoms: list[str] = field(default_factory=list)       # for the clinical-graph view in app.py
    conditions: list[str] = field(default_factory=list)
    axes: list[str] = field(default_factory=list)                # case route: clinical axes searched, in order
    evidence_axis: dict[str, str] = field(default_factory=dict)  # hit id -> axis whose query found it ("case" = whole case)
    candidates: list[dict] = field(default_factory=list)         # graph route: BODHI candidate conditions {"id", "name"}
    walk: dict = field(default_factory=dict)                     # GRAPH_WALK summary: entities, sections, added hit ids


def _add_hits(plan: Plan, hits: list[Hit]) -> None:
    seen = {h.id for h in plan.evidence}
    for h in hits:
        if h.id not in seen and len(plan.evidence) < MAX_EVIDENCE and h.similarity >= config.MIN_SIMILARITY:
            plan.evidence.append(h)
            seen.add(h.id)


GENERIC_TERMS = {"fever", "disease", "disorder", "syndrome", "acute", "chronic", "infection", "viral", "bacterial",
                 "of", "the", "and", "with", "type", "primary", "secondary"}


def mentions(hit: Hit, condition: str) -> bool:
    """True if the passage (or its heading path) names the condition's distinctive word(s)."""
    keys = [w for w in re.findall(r"[a-z]+", condition.lower()) if len(w) >= 4 and w not in GENERIC_TERMS]
    if not keys:
        keys = [condition.lower()]
    hay = (hit.passage + " " + hit.citation()).lower()
    return any(re.search(rf"\b{re.escape(k)}", hay) for k in keys)


NAME_GENERIC = GENERIC_TERMS | {"pulmonary", "cardiac", "renal", "hepatic", "acute", "chronic", "severe", "mild",
                                "primary", "with", "without", "unspecified"}
CANDIDATE_POOL = 25        # graph proposes this many conditions; the textbook check picks the top 3
CASE_SEARCH_K = 12         # passages retrieved for the whole case text


def names_condition(hit: Hit, condition: str) -> bool:
    """Stricter than mentions(): every distinctive word of the condition must appear in the passage."""
    keys = [w for w in re.findall(r"[a-z]+", condition.lower()) if len(w) >= 4 and w not in NAME_GENERIC]
    if not keys:
        return False
    hay = (hit.passage + " " + hit.citation()).lower()
    return all(re.search(rf"\b{re.escape(k)}", hay) for k in keys)


def textbook_rerank(question: str, pool: list[dict], top: int = 3) -> tuple[list[dict], list[Hit]]:
    """Re-rank graph candidates by textbook support: search the whole case once and count how many of the
    top passages name each candidate. The graph still proposes; the books decide between proposals."""
    case_hits = search(question, k=CASE_SEARCH_K)
    for c in pool:
        c["text_support"] = sum(names_condition(h, c["name"]) for h in case_hits)
    ranked = sorted(pool, key=lambda c: (c["symptoms_matched"] + 0.25 * min(c["text_support"], 4),
                                         c["text_support"], c.get("spec", 0.0)), reverse=True)
    return ranked[:top], case_hits


CASE_MIN_WORDS = 35        # a question this long is a clinical vignette, not a look-up
CASE_SYSTEM = """You turn a clinical case vignette into focused textbook look-up queries for a medical student.
Identify (1) the most likely diagnosis or the specific drug/organism/process the question is really about, and
(2) what is being asked, as a subset of: diagnosis, presentation, etiology, mechanism, pathology, diagnostics,
treatment, contraindications.
Write 1-3 short search queries (each under 15 words) naming the condition/drug/organism explicitly, the way a
textbook heading or index entry would phrase it. Do not answer the question.
Return JSON: {"focus": "<diagnosis or topic>", "asks": ["treatment", ...], "queries": ["...", "..."]}"""
# what the student asks -> which certified ontology facts are worth adding
ASK_TO_ONTOLOGY = {"treatment": ("first-line", "WARNING"), "contraindications": ("WARNING",),
                   "diagnostics": ("confirmed by",), "diagnosis": ("confirmed by",)}


def decompose_case(question: str) -> tuple[str, list[str], list[str]]:
    """(focus, asks, queries) for a long vignette; falls back to the question itself."""
    try:
        raw = chat(CASE_SYSTEM, question, temperature=0.0, max_tokens=300, json_mode=True,
                   purpose="Find the case's focus and what it asks")
        d = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        queries = [" ".join(str(q).split()) for q in d.get("queries", []) if str(q).strip()][:3]
        return str(d.get("focus", "")).strip(), [str(a).lower() for a in d.get("asks", [])], queries or [question]
    except (json.JSONDecodeError, ValueError, RuntimeError):     # RuntimeError: backend down / out of credit
        return "", [], [question]


# ---- Three-axis case decomposition -------------------------------------------------------------------------
# A long case is split along the clinical-ontology axes a clinician reasons in. Each axis that applies gets its own
# textbook query; axes that do not apply (no emergency in a chronic-disease question) are left out, not invented.
AXES = {
    "etiology": "Etiology & differential diagnosis",
    "stabilization": "Emergency stabilization & acute triage",
    "pharmacology": "Definitive pharmacology & contraindications",
}
# which certified ontology fact lines each axis pulls in for the named condition (prefixes of graph_facts_for lines)
AXIS_TO_ONTOLOGY = {"etiology": ("confirmed by",), "stabilization": (), "pharmacology": ("first-line", "WARNING")}
AXIS_QUERY_MAX_WORDS = 12
MAX_QUERIES_PER_AXIS = 2
MAX_AXIS_QUERIES = 5

AXES_SYSTEM = """You plan textbook look-ups for a medical student's clinical case. Decompose the case along up to three
clinical axes, and include an axis ONLY if the case or its question genuinely needs it:
- "etiology": etiology, pathophysiology and differential diagnosis of the presentation
- "stabilization": emergency stabilization and acute triage (airway, breathing, circulation, immediate life-saving
  steps). Omit it when nothing in the case is acute or life-threatening (e.g. a stable chronic-disease question).
- "pharmacology": definitive drug treatment, drug of choice, and contraindications for THIS patient
For each included axis write 1 or 2 search queries (at most 5 in total). Each query covers ONE specific thing the case
asks -- never pack several points into one query -- and is phrased like a textbook heading or index entry, under 10
words, naming the condition, drug or organism. Good: "Management of thyroid storm", "Aspirin in thyrotoxicosis",
"Nitrates contraindicated in right ventricular infarction". Bad: "thyroid storm propylthiouracil iodine aspirin
cooling management". Do not answer the question.
"likely_condition" is the single most likely diagnosis if the case points to one, else "".
Return JSON exactly in this shape:
{"likely_condition": "<diagnosis or empty>", "axes": [{"axis": "etiology|stabilization|pharmacology", "query": "..."}]}
(repeat an axis entry for its second query)"""

AXES_SCHEMA = {
    "type": "object",
    "properties": {
        "likely_condition": {"type": "string"},
        "axes": {"type": "array", "maxItems": MAX_AXIS_QUERIES, "items": {
            "type": "object",
            "properties": {"axis": {"type": "string", "enum": list(AXES)}, "query": {"type": "string"}},
            "required": ["axis", "query"]}},
    },
    "required": ["likely_condition", "axes"],
}


@dataclass
class AxisQuery:
    axis: str                 # a key of AXES
    query: str


@dataclass
class CaseAxes:
    condition: str            # "" when the case does not point to one diagnosis
    axes: list[AxisQuery]


def parse_axes(raw: str) -> CaseAxes | None:
    """Validate the LLM's JSON against AXES_SCHEMA by hand (DeepSeek's JSON mode guarantees JSON, not the shape).
    Returns None for anything unusable, so the caller falls back to the older decomposition."""
    try:
        d = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(d, dict) or not isinstance(d.get("axes"), list):
        return None
    cond = d.get("likely_condition", "")
    cond = " ".join(cond.split())[:80] if isinstance(cond, str) else ""
    out, seen = [], set()
    for item in d["axes"]:
        if not isinstance(item, dict):
            continue
        axis, query = item.get("axis"), item.get("query")
        if axis not in AXES or not isinstance(query, str):
            continue
        query = " ".join(query.split())
        if not query or len(query.split()) > AXIS_QUERY_MAX_WORDS or (axis, query.lower()) in seen:
            continue
        if sum(a.axis == axis for a in out) >= MAX_QUERIES_PER_AXIS or len(out) >= MAX_AXIS_QUERIES:
            continue
        seen.add((axis, query.lower()))
        out.append(AxisQuery(axis, query))
    if not out:
        return None
    out.sort(key=lambda a: list(AXES).index(a.axis))          # stable, clinical order in the trace
    return CaseAxes(cond, out)


def decompose_axes(question: str) -> tuple[CaseAxes | None, str]:
    """(axes, why) -- axes is None when the call failed or returned junk; why says which, for the trace."""
    try:
        raw = chat(AXES_SYSTEM, question, temperature=0.0, max_tokens=350, json_mode=True, schema=AXES_SCHEMA,
                   purpose="Decompose the case along clinical axes")
    except RuntimeError as e:
        return None, f"backend error: {e}"
    axes = parse_axes(raw)
    return axes, ("ok" if axes else "invalid JSON or schema")


def axis_ontology_lines(axes: CaseAxes) -> dict[str, list[str]]:
    """Certified ontology facts for the case's likely condition, routed to the axes that asked for them."""
    if not axes.condition or not ontology_facts.available():
        return {}
    lines = ontology_facts.graph_facts_for(axes.condition)
    out = {}
    for a in axes.axes:
        keys = AXIS_TO_ONTOLOGY.get(a.axis, ())
        picked = [l for l in lines if any(k.lower() in l.lower() for k in keys)]
        if picked:
            out[a.axis] = picked
    return out


def interleave(*lists: list[Hit], limit: int) -> list[Hit]:
    """Round-robin merge (first list first), dropping duplicates: each query's best passages get in."""
    out, seen = [], set()
    for i in range(max((len(l) for l in lists), default=0)):
        for l in lists:
            if i < len(l) and l[i].id not in seen:
                seen.add(l[i].id)
                out.append(l[i])
    return out[:limit]


def decompose(question: str) -> list[str]:
    try:
        raw = chat(DECOMPOSE_SYSTEM, question, temperature=0.0, max_tokens=300, json_mode=True,
                   purpose="Split the question into sub-questions")
        subs = json.loads(raw[raw.find("{"): raw.rfind("}") + 1]).get("sub_questions", [])
        subs = [" ".join(str(s).split()) for s in subs if str(s).strip()][:3]
        return subs or [question]
    except (json.JSONDecodeError, ValueError):
        return [question]


def looks_compound(question: str) -> bool:
    q = question.lower()
    return bool(re.search(r"\b(compare|contrast|difference|differences|versus|vs\.?)\b", q)) or q.count("?") > 1 \
        or bool(re.search(r"\band\b.*\b(why|how|what|which|when)\b", q))


CASE_CUE = re.compile(r"\b(patient|presents?|presenting|complain\w*|year[- ]old|y/?o|history of|"
                      r"(likely|probable|differential) diagnosis|diagnos\w*|what could|suffer\w*|"
                      r"(man|woman|boy|girl|child|male|female) (with|has|having))\b", re.I)


def is_case(question: str, symptoms: list[dict]) -> bool:
    """Symptom -> condition hops only make sense for a clinical vignette, not for "drug of choice for seizures"
    or "fall in blood pressure" (a physiology question that merely names a symptom)."""
    return len(symptoms) >= 2 or (len(symptoms) == 1 and bool(CASE_CUE.search(question)))


def plan(question: str) -> Plan:
    p = _plan_routes(question)
    if config.GRAPH_WALK and p.route != "single":
        graph_walk(p, question)
    return p


def _plan_routes(question: str) -> Plan:
    with trace.timer() as t:
        ents = link_entities(question)
    symptoms = [e for e in ents if e["type"] == "Symptom"]
    others = [e for e in ents if e["type"] != "Symptom"]
    trace.record("link", f"{len(symptoms)} symptom(s) linked to the clinical graph",
                 ("; ".join(f'"{e.get("via", e["name"])}" → {e["name"]}' for e in symptoms) or "No symptoms found.")
                 + (f" Also recognised: {', '.join(e['name'] + ' (' + e['type'].lower() + ')' for e in others[:4])}."
                    if others else ""), ms=t.ms, symptoms=[e["name"] for e in symptoms])

    if len(question.split()) >= CASE_MIN_WORDS:
        return plan_case(question)

    case = is_case(question, symptoms)
    cue = CASE_CUE.search(question)
    if case:
        why = (f"{len(symptoms)} symptoms" if len(symptoms) >= 2 else f'1 symptom plus the case cue "{cue.group()}"')
        trace.record("route", "Clinical vignette → graph route", f"{why}: find likely conditions in the graph, then "
                     "look up their treatment in the textbooks.")
    elif looks_compound(question):
        trace.record("route", "Compound question → split into parts", "It asks about more than one thing, so each part "
                     "is searched separately and no topic crowds out the other.")
    else:
        trace.record("route", "Single question → direct textbook search", "Not a clinical case and only one topic.")

    if case:
        p = Plan(route="graph")
        names = ", ".join(e["name"] for e in symptoms)
        with trace.timer() as t:
            pool = conditions_for_symptoms([e["ids"] for e in symptoms], top=CANDIDATE_POOL)
        trace.record("graph", f"Symptoms → {len(pool)} candidate conditions",
                     "Top by graph: " + ("; ".join(f"{c['name']} ({c['symptoms_matched']}/{len(symptoms)})"
                                                   for c in pool[:5]) or "none"),
                     status="ok" if pool else "warn", ms=t.ms)
        conds, case_hits = textbook_rerank(question, pool)
        p.symptoms = [e["name"] for e in symptoms]
        p.conditions = [c["name"] for c in conds]
        p.candidates = [{"id": c["id"], "name": c["name"]} for c in conds]
        trace.record("graph", "Textbook check of candidates",
                     "; ".join(f"{c['name']}: {c['symptoms_matched']}/{len(symptoms)} symptoms, named in "
                               f"{c['text_support']} of {len(case_hits)} case passages" for c in conds)
                     or "No condition matches these symptoms.", status="ok" if conds else "warn")
        p.hops.append(Hop("graph", f"symptoms → conditions ({names})",
                          "; ".join(f"{c['name']} ({c['symptoms_matched']}/{len(symptoms)} symptoms)" for c in conds)
                          or "no matching conditions"))
        for c in conds:
            # BODHI symptom->condition and specialist links stay citable (attributed to BODHI, used for the
            # differential only). BODHI *drug* links have no textbook support, so they go to nav_hints, never the prompt.
            p.graph_facts.append(f"BODHI links {c['symptoms_matched']} of the {len(symptoms)} symptoms "
                               f"({names}) to {c['name']}.")
            spec = specialities_for(c["id"])
            if spec:
                p.graph_facts.append(f"BODHI: {c['name']} is treated by: {', '.join(spec[:3])}.")
            drugs = drugs_for(c["id"])
            if drugs:
                p.bodhi_drugs[c["name"]] = drugs      # kept for cross_check(), which only compares against the answer
                p.nav_hints.append(f"BODHI drug links for {c['name']}: {', '.join(drugs[:8])}.")
        if conds:
            trace.record("graph", "Conditions → specialist and drug links",
                         "; ".join(f"{c['name']}: {', '.join(specialities_for(c['id'])[:2]) or 'no specialist listed'}, "
                                   f"{len(p.bodhi_drugs.get(c['name'], []))} linked drugs" for c in conds))
            p.hops.append(Hop("graph", "conditions → speciality, drugs",
                              "; ".join(f"{c['name']}: {', '.join(specialities_for(c['id'])[:2]) or '—'}"
                                        for c in conds)))
        if conds and ontology_facts.available():
            with trace.timer() as t:
                found = {c["name"]: ontology_facts.graph_facts_for(c["name"]) for c in conds[:2]}
            for lines in found.values():
                p.graph_facts.extend(lines)
            n_warn = sum(line.startswith("WARNING") for lines in found.values() for line in lines)
            trace.record("graph", "Textbook ontology lookup",
                         "; ".join(f"{name}: " + (", ".join(ontology_facts.match_conditions(name)[:2]) + f" ({len(lines)} facts)"
                                                  if lines else "not covered by the pilot ontology")
                                   for name, lines in found.items())
                         + (f". {n_warn} contraindication warning(s) added." if n_warn else ""),
                         status="ok" if any(found.values()) else "warn", ms=t.ms)
        for c in conds[:2]:                      # textbook evidence for the top two conditions
            q = f"treatment and drug of choice for {c['name']}"
            found = search(q, k=PER_SUBQUERY_K * 2)
            hits = [h for h in found if mentions(h, c["name"])][:PER_SUBQUERY_K]
            trace.record("filter", f"Relevance filter: {c['name']}",
                         f"Kept {len(hits)} of {len(found)} passages that actually name the condition"
                         + ("." if hits else "; none do, so the answer will say the books don't cover its treatment."),
                         status="ok" if hits else "warn")
            if hits:
                _add_hits(p, hits)
                p.hops.append(Hop("retrieve", q, hits[0].citation(), hits))
            else:
                # Say so explicitly: the honest answer is "this book does not cover it", not a nearby passage.
                p.graph_facts.append(f"The indexed textbook(s) contain no passage on the treatment of {c['name']}.")
                p.hops.append(Hop("retrieve", q, "no textbook passage mentions this condition"))
        # The case search above also covers the non-treatment parts of the question (no second search)
        _add_hits(p, case_hits[:PER_SUBQUERY_K])
        p.hops.append(Hop("retrieve", question, case_hits[0].citation() if case_hits else "no textbook evidence",
                          case_hits[:PER_SUBQUERY_K]))
        return p

    if looks_compound(question):
        p = Plan(route="decompose")
        subs = decompose(question)
        trace.record("decompose", f"Split into {len(subs)} sub-question(s)", " | ".join(subs))
        p.hops.append(Hop("decompose", question, " | ".join(subs)))
        for s in subs:
            hits = search(s, k=PER_SUBQUERY_K)
            _add_hits(p, hits)
            p.hops.append(Hop("retrieve", s, hits[0].citation() if hits else "no evidence", hits))
        return p

    # Single route: answer() does the one search itself, so nothing is retrieved twice.
    return Plan(route="single")


NON_DRUGS = {
    "iron", "water", "saline", "normal saline", "oxygen", "diet", "exercise",
    "electrolyte", "electrolytes", "adapting electrolyte solutions",
    "oral rehydration salts", "rehydration", "bed rest", "glucose", "dextrose",
    "calcium", "potassium", "sodium", "nutrition", "fluid", "fluids",
    "intravenous fluid", "intravenous fluids", "lifestyle", "rest", "smoking cessation",
}

NEGATION_PATTERN = re.compile(
    r"\b(avoid|avoided|avoiding|do not|don't|should not|must not|never|contraindicated|"
    r"contraindication|contraindications|harmful|not recommended|withheld|withhold|"
    r"refrain|toxic|toxicity|caution with|discontinue|stop|prohibited)\b",
    re.I,
)


def plan_case(question: str) -> Plan:
    """Long vignette: name its focus and what it asks, search the whole case AND focused queries (interleaved),
    and add certified ontology facts for the focus that match what is asked."""
    p = Plan(route="case")
    trace.record("route", "Long clinical case → focused look-ups",
                 f"{len(question.split())} words: one embedding of the whole case blurs what is asked, so the case "
                 "is also searched as short, focused textbook queries.")
    axes, why = decompose_axes(question)
    if axes:
        return _plan_axes(question, p, axes)
    trace.record("decompose", "Clinical-axis split unavailable → simpler split",
                 f"{why[:160]}.", status="warn")
    if why.startswith("backend error"):                 # the backend is down: don't spend a second failing call
        focus, asks, queries = "", [], [question]
    else:
        focus, asks, queries = decompose_case(question)
    trace.record("decompose", f"Focus: {focus or 'unclear'}",
                 ("Asks about: " + ", ".join(asks) + ". " if asks else "") + "Queries: " + " | ".join(queries))
    p.hops.append(Hop("decompose", question, f"{focus} :: " + " | ".join(queries)))
    whole = search(question, k=5)
    focused = [search(q, k=5) for q in queries]
    merged = interleave(whole, *focused, limit=MAX_EVIDENCE + 3)
    _add_hits(p, merged)
    p.hops.append(Hop("retrieve", " + ".join([question[:40] + "…"] + queries),
                      p.evidence[0].citation() if p.evidence else "no evidence", p.evidence))
    if focus and ontology_facts.available():
        wanted = {key for a in asks for key in ASK_TO_ONTOLOGY.get(a, ())}
        lines = [l for l in ontology_facts.graph_facts_for(focus)
                 if any(w.lower() in l.lower() for w in wanted)] if wanted else []
        p.graph_facts.extend(lines)
        trace.record("graph", "Textbook ontology lookup",
                     f"{focus}: " + (", ".join(ontology_facts.match_conditions(focus)[:2]) or "not in the pilot ontology")
                     + (f"; {len(lines)} certified fact(s) added for what the case asks" if lines else
                        "; nothing added (not covered, or the case doesn't ask about therapy/diagnostics)"),
                     status="ok" if lines else "warn")
    return p


def _plan_axes(question: str, p: Plan, axes: CaseAxes) -> Plan:
    """One retrieval sub-query per clinical axis (plus the whole case), and per-axis ontology facts."""
    trace.record("decompose", f"{len({a.axis for a in axes.axes})} clinical axis/axes, {len(axes.axes)} look-ups" + (f" · likely {axes.condition}" if axes.condition else ""),
                 " | ".join(f"{AXES[a.axis]}: {a.query}" for a in axes.axes)
                 + (". Skipped: " + ", ".join(AXES[k] for k in AXES if k not in {a.axis for a in axes.axes})
                    if len(axes.axes) < len(AXES) else ""))
    p.hops.append(Hop("decompose", question, f"{axes.condition} :: "
                      + " | ".join(f"{a.axis}: {a.query}" for a in axes.axes)))
    whole = search(question, k=5)
    per_axis = [search(a.query, k=5) for a in axes.axes]
    for a, hits in zip(axes.axes, per_axis):
        p.hops.append(Hop("retrieve", f"[{a.axis}] {a.query}", hits[0].citation() if hits else "no evidence", hits))
    _add_hits(p, interleave(whole, *per_axis, limit=MAX_EVIDENCE + 3))
    p.axes = list(dict.fromkeys(a.axis for a in axes.axes))
    for h in p.evidence:
        p.evidence_axis[h.id] = next((a.axis for a, hits in zip(axes.axes, per_axis) if any(x.id == h.id for x in hits)),
                                     "case")
    if axes.condition:
        p.conditions = [axes.condition]
        p.symptoms = clinical_graph.symptoms_in_text(question, [axes.condition])
    onto = axis_ontology_lines(axes)
    for a in axes.axes:
        for line in onto.get(a.axis, []):
            if line not in p.graph_facts:
                p.graph_facts.append(line)
    if axes.condition and ontology_facts.available():
        n = sum(len(v) for v in onto.values())
        trace.record("graph", "Textbook ontology lookup",
                     f"{axes.condition}: " + (", ".join(ontology_facts.match_conditions(axes.condition)[:2])
                                              or "not in the pilot ontology")
                     + (f"; {n} certified fact(s) added for " + ", ".join(onto) if n else "; nothing added"),
                     status="ok" if n else "warn")
    return p


# ---- Graph walk (GRAPH_WALK=1, Stage 5 of docs/graph_networking_plan.md) --------------------------------------
# NAVIGATION ONLY. What may enter the answer prompt:
#   * textbook passages (normal evidence) found by searching inside sections the mention index points to, and
#   * certified ontology facts (graph_facts_for), whose condition label may come from ontology_facts.match_conditions
#     or from crosswalk.trusted_labels (name-rule exact, T2).
# Mention scores, hubs, co-mentions and non-trusted crosswalk rows are never read here as clinical content: the
# mention index only chooses WHERE to search, the crosswalk only chooses WHICH certified facts to show.
WALK_MAX_ENTITIES = 3        # entities expanded per question
WALK_SECTIONS = 3            # mention sections per entity
WALK_MAX_HITS = 2            # expansion passages allowed in the evidence list
WALK_SEARCH_K = 3


@functools.cache
def _label_keys() -> dict[str, str]:
    """phrase key -> ontology condition label, for spotting condition names inside a question."""
    out: dict[str, str] = {}
    for label in ontology_facts.condition_labels():          # most-described first, so it wins ties
        key = mention_index.phrase_key(label)
        if len(key) >= 6 and key not in out:
            out[key] = label
    return out


def _exact_label(name: str) -> str | None:
    """Best ontology label for a condition name: the exact-name label if there is one, else the best-documented."""
    labels = ontology_facts.match_conditions(name) if ontology_facts.available() else []
    if not labels:
        return None
    key = mention_index.phrase_key(name)
    return next((l for l in labels if mention_index.phrase_key(l) == key), labels[0])


def resolve_entities(question: str, p: Plan) -> list[dict]:
    """[{"label", "via"}]: ontology labels for the plan's candidate conditions, then for condition names that the
    question itself spells out (longest phrase first). Crosswalk use is T2-only (trusted_labels)."""
    out: list[dict] = []
    seen: set[str] = set()

    def add(label: str | None, via: str) -> None:
        if label and mention_index.phrase_key(label) not in seen:
            seen.add(mention_index.phrase_key(label))
            out.append({"label": label, "via": via})

    cands = p.candidates or [{"id": None, "name": n} for n in p.conditions]
    for c in cands:
        add(_exact_label(c["name"]), f"candidate {c['name']}")
        for label in crosswalk.trusted_labels(c["id"] or c["name"]):
            add(label, f"candidate {c['name']} (crosswalk T2)")
    toks = mention_index.tokens(question)
    keys = _label_keys()
    i = 0
    while i < len(toks):
        for n in range(min(5, len(toks) - i), 0, -1):
            gram = " ".join(toks[i:i + n])
            if gram in keys and not (n == 1 and gram in GENERIC_TERMS):
                add(keys[gram], f'question names "{gram}"')
                i += n - 1
                break
        i += 1
    return out


def walk_sections(label: str, evidence: list[Hit]) -> list[dict]:
    """Top mention sections for one entity: sections of books not yet in the evidence first, then the rest."""
    have_books = {h.meta.get("book_id") for h in evidence}
    have_sections = {h.meta.get("section_id") for h in evidence}
    rows = [r for r in mention_index.sections_for(label, k=8) if r["section_id"] not in have_sections]
    rows.sort(key=lambda r: r["book_id"] in have_books)       # stable: strength order kept inside each group
    return rows[:WALK_SECTIONS]


def _bridge_facts(p: Plan) -> list[str]:
    """Certified ontology lines for BODHI candidates whose own name had no ontology match, reached through
    T2 crosswalk links. Same lines as any other graph fact, so the answer cites them as [G#]."""
    added = []
    for c in p.candidates:
        if ontology_facts.graph_facts_for(c["name"]):
            continue                                          # already covered by the name match
        for label in crosswalk.trusted_labels(c["id"])[:1]:
            for line in ontology_facts.graph_facts_for(label):
                if line not in p.graph_facts:
                    p.graph_facts.append(line)
                    added.append(line)
    return added


def graph_walk(p: Plan, question: str) -> None:
    """Add up to WALK_MAX_HITS textbook passages from entity-linked sections (and certified bridge facts)."""
    with trace.timer() as t:
        ents = resolve_entities(question, p)[:WALK_MAX_ENTITIES]
        bridged = _bridge_facts(p) if ontology_facts.available() else []
        cands: list[tuple[Hit, str]] = []
        used: list[dict] = []
        for e in ents:
            secs = walk_sections(e["label"], p.evidence)
            if not secs:
                continue
            q = f"{e['label']}: {' '.join(question.split()[:40])}"
            hits = search(q, k=WALK_SEARCH_K, section_ids=[s["section_id"] for s in secs])
            used.append({"label": e["label"], "sections": [s["section_id"] for s in secs]})
            cands += [(h, e["label"]) for h in hits]
        have = {h.id for h in p.evidence}
        books = {h.meta.get("book_id") for h in p.evidence}
        cands = [(h, l) for h, l in cands if h.id not in have and h.similarity >= config.MIN_SIMILARITY]
        # best first, books not yet in the evidence ahead of ones that are
        cands.sort(key=lambda x: (x[0].meta.get("book_id") in books, -x[0].similarity))
        picked: list[Hit] = []
        for one_per_entity in (True, False):               # first the best hit of each entity, then fill up
            for h, label in cands:
                if h.id in {x.id for x in picked} or len(picked) >= WALK_MAX_HITS:
                    continue
                if one_per_entity and label in {l for x, l in cands if x in picked}:
                    continue
                picked.append(h)
        # evidence is capped at MAX_EVIDENCE: expansion passages take the lowest-ranked slots, never more than 2
        room = MAX_EVIDENCE - len(p.evidence)
        if len(picked) > room:
            del p.evidence[len(p.evidence) - (len(picked) - room):]
        _add_hits(p, picked)
    added = [h.id for h in picked if h in p.evidence]
    p.walk = {"entities": [e["label"] for e in ents], "sections": used, "added": added, "bridge_facts": len(bridged)}
    if used:
        p.hops.append(Hop("expand", "; ".join(u["label"] for u in used),
                          picked[0].citation() if picked else "no new passage cleared the threshold", picked))
    trace.record("graph", "Graph walk",
                 ("Entities: " + "; ".join(f'{e["label"]} ({e["via"]})' for e in ents) if ents else "No entity resolved")
                 + ". Sections: " + (" | ".join(f'{u["label"]}: ' + ", ".join(u["sections"]) for u in used) or "none")
                 + f". {len(added)} passage(s) added" + (f", {len(bridged)} certified fact(s) via T2 crosswalk" if bridged else "")
                 + ". Navigation only: mention links choose where to search, never what is claimed.",
                 status="ok" if added or bridged else "warn", ms=t.ms, entities=[e["label"] for e in ents], added=added)


def cross_check(answer_text: str, plan: Plan) -> list[str]:
    """Drugs that BODHI links to a candidate condition AND that appear in affirmative recommendations
    in the textbook-grounded answer (skips non-drugs and negated/contraindicated mentions)."""
    sentences = [s.strip() for s in re.split(r"[.\n;!]", answer_text) if s.strip()]
    agreed = []
    seen = set()
    for cond, drugs in plan.bodhi_drugs.items():
        for d in drugs:
            d_clean = d.strip()
            if len(d_clean) < 3 or d_clean.lower() in NON_DRUGS:
                continue
            d_pattern = re.compile(rf"\b{re.escape(d_clean.lower())}\b", re.I)
            affirmed = False
            for sent in sentences:
                if d_pattern.search(sent) and not NEGATION_PATTERN.search(sent):
                    affirmed = True
                    break
            if affirmed:
                item = f"{d_clean.title()} ({cond})"
                if item not in seen:
                    seen.add(item)
                    agreed.append(item)
    return agreed
