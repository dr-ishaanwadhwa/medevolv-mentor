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

from rag import config
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


def decompose(question: str) -> list[str]:
    try:
        raw = chat(DECOMPOSE_SYSTEM, question, temperature=0.0, max_tokens=300, json_mode=True)
        subs = json.loads(raw[raw.find("{"): raw.rfind("}") + 1]).get("sub_questions", [])
        subs = [" ".join(str(s).split()) for s in subs if str(s).strip()][:3]
        return subs or [question]
    except (json.JSONDecodeError, ValueError):
        return [question]


def looks_compound(question: str) -> bool:
    q = question.lower()
    return bool(re.search(r"\b(compare|contrast|difference|differences|versus|vs\.?)\b", q)) or q.count("?") > 1 \
        or bool(re.search(r"\band\b.*\b(why|how|what|which|when)\b", q))


def plan(question: str) -> Plan:
    ents = link_entities(question)
    symptoms = [e for e in ents if e["type"] == "Symptom"]

    if symptoms:
        p = Plan(route="graph")
        names = ", ".join(e["name"] for e in symptoms)
        conds = conditions_for_symptoms([e["ids"] for e in symptoms], top=3)
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
            p.hops.append(Hop("graph", "conditions → speciality, drugs",
                              "; ".join(f"{c['name']}: {', '.join(specialities_for(c['id'])[:2]) or '—'}"
                                        for c in conds)))
        for c in conds[:2]:                      # textbook evidence for the top two conditions
            q = f"treatment and drug of choice for {c['name']}"
            hits = [h for h in search(q, k=PER_SUBQUERY_K * 2) if mentions(h, c["name"])][:PER_SUBQUERY_K]
            if hits:
                _add_hits(p, hits)
                p.hops.append(Hop("retrieve", q, hits[0].citation(), hits))
            else:
                # Say so explicitly: the honest answer is "this book does not cover it", not a nearby passage.
                p.graph_facts.append(f"The indexed textbook(s) contain no passage on the treatment of {c['name']}.")
                p.hops.append(Hop("retrieve", q, "no textbook passage mentions this condition"))
        # Also retrieve for the original question so non-treatment parts are covered
        hits = search(question, k=PER_SUBQUERY_K)
        _add_hits(p, hits)
        p.hops.append(Hop("retrieve", question, hits[0].citation() if hits else "no textbook evidence", hits))
        return p

    if looks_compound(question):
        p = Plan(route="decompose")
        subs = decompose(question)
        p.hops.append(Hop("decompose", question, " | ".join(subs)))
        for s in subs:
            hits = search(s, k=PER_SUBQUERY_K)
            _add_hits(p, hits)
            p.hops.append(Hop("retrieve", s, hits[0].citation() if hits else "no evidence", hits))
        return p

    p = Plan(route="single")
    hits = search(question)
    _add_hits(p, hits)
    p.hops.append(Hop("retrieve", question, hits[0].citation() if hits else "no evidence", hits))
    return p


def cross_check(answer_text: str, plan: Plan) -> list[str]:
    """Drugs that BODHI links to a candidate condition AND that appear in the textbook-grounded answer."""
    text = answer_text.lower()
    agreed = []
    for cond, drugs in plan.bodhi_drugs.items():
        for d in drugs:
            if len(d) > 3 and re.search(rf"\b{re.escape(d.lower())}\b", text):
                agreed.append(f"{d} ({cond})")
    return agreed
