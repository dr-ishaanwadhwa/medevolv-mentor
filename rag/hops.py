"""Multi-hop answering: BODHI graph plans the hops, the textbook supplies cited evidence for each one.

Two routes (both are the rubric's "query decomposition" enhancement):

  Graph route  -- the question mentions symptoms that link to BODHI nodes
     hop 1  symptoms -> ranked candidate conditions            (graph, cited as [G1], [G2] ...)
     hop 2  condition -> speciality + BODHI drug list           (graph)
     hop 3  "treatment / drug of choice for <condition>"        (textbook retrieval, cited as [1], [2] ...)
     cross-check: drugs named in the textbook evidence vs BODHI's drug list for that condition

  Decomposition route -- no symptoms linked, but the question has several parts ("compare X and Y")
     the LLM splits it into <= 3 sub-questions; each is retrieved separately so no part crowds out another

Every hop is recorded in a trace that the UI shows, so the reasoning path is visible and checkable.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from rag import config, trace
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
    graph_facts: list[str] = field(default_factory=list)     # cited as [G1], [G2] ...
    evidence: list[Hit] = field(default_factory=list)       # cited as [1], [2] ...
    bodhi_drugs: dict[str, list[str]] = field(default_factory=dict)


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
    with trace.timer() as t:
        ents = link_entities(question)
    symptoms = [e for e in ents if e["type"] == "Symptom"]
    others = [e for e in ents if e["type"] != "Symptom"]
    trace.record("link", f"{len(symptoms)} symptom(s) linked to the clinical graph",
                 ("; ".join(f'"{e.get("via", e["name"])}" → {e["name"]}' for e in symptoms) or "No symptoms found.")
                 + (f" Also recognised: {', '.join(e['name'] + ' (' + e['type'].lower() + ')' for e in others[:4])}."
                    if others else ""), ms=t.ms, symptoms=[e["name"] for e in symptoms])

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
        trace.record("graph", "Textbook check of candidates",
                     "; ".join(f"{c['name']}: {c['symptoms_matched']}/{len(symptoms)} symptoms, named in "
                               f"{c['text_support']} of {len(case_hits)} case passages" for c in conds)
                     or "No condition matches these symptoms.", status="ok" if conds else "warn")
        p.hops.append(Hop("graph", f"symptoms → conditions ({names})",
                          "; ".join(f"{c['name']} ({c['symptoms_matched']}/{len(symptoms)} symptoms)" for c in conds)
                          or "no matching conditions"))
        for c in conds:
            p.graph_facts.append(f"BODHI links {c['symptoms_matched']} of the {len(symptoms)} symptoms "
                                 f"({names}) to {c['name']}.")
            spec = specialities_for(c["id"])
            if spec:
                p.graph_facts.append(f"BODHI: {c['name']} is treated by: {', '.join(spec[:3])}.")
            drugs = drugs_for(c["id"])
            if drugs:
                p.bodhi_drugs[c["name"]] = drugs
                p.graph_facts.append(f"BODHI drug links for {c['name']}: {', '.join(drugs[:8])}.")
        if conds:
            trace.record("graph", "Conditions → specialist and drug links",
                         "; ".join(f"{c['name']}: {', '.join(specialities_for(c['id'])[:2]) or 'no specialist listed'}, "
                                   f"{len(p.bodhi_drugs.get(c['name'], []))} linked drugs" for c in conds))
            p.hops.append(Hop("graph", "conditions → speciality, drugs",
                              "; ".join(f"{c['name']}: {', '.join(specialities_for(c['id'])[:2]) or '—'}"
                                        for c in conds)))
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
