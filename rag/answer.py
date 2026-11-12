"""Grounded answering: retrieve → guard rails → LLM with numbered evidence → answer with citations.

Three ways the bot declines instead of guessing (the rubric's "unsupported question" handling):
  1. personal clinical advice ("what dose should my mother take") → study-aid refusal, no retrieval needed
  2. weak retrieval (best similarity < MIN_SIMILARITY) → "not in my sources", the LLM is never called
  3. the LLM itself is told to answer only from the evidence and to say INSUFFICIENT_CONTEXT otherwise
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag import config
from rag.backends import chat
from rag.retrieve import Hit, search

PERSONAL = re.compile(
    r"\b(my|our)\s+(mother|mom|mum|father|dad|wife|husband|son|daughter|child|baby|kid|friend|grandma|grandpa|"
    r"grandmother|grandfather|brother|sister)\b"
    r"|\b(should|can|could)\s+i\s+(take|give|stop|start|increase|double)\b"
    r"|\bi\s+(am|'m)\s+(taking|on)\b"
    r"|\bhow\s+much\s+should\s+(i|he|she|they)\s+(take|give)\b",
    re.I,
)

SYSTEM = """You are a study companion for medical students (pharmacology, medicine, pathology, physiology, microbiology), built on Eka Care's knowledge sources.
Rules:
- Answer ONLY from the numbered evidence passages. Do not use outside knowledge.
- Cite every claim with the passage number in square brackets, e.g. [2]. Use only numbers that exist.
- If the evidence does not contain the answer, reply exactly: INSUFFICIENT_CONTEXT
- If only part of the question is covered, answer that part and state plainly which part the sources do not cover.
- Be concise and exam-oriented: short paragraphs or bullet points. Start directly with the answer; do not repeat
  the passage headers or source lines.
- Never give dosing or treatment advice for a specific real person."""

NOT_IN_SOURCES = ("I couldn't find this in my textbook sources, so I won't guess. "
                  "Try rephrasing, or ask about a topic covered in the indexed textbooks.")
PERSONAL_REFUSAL = ("I'm a study aid, so I can't advise on treatment or dosing for a real person — please ask a "
                    "doctor or pharmacist. I can explain what the textbook says about the drug or condition in general.")


@dataclass
class Answer:
    text: str
    hits: list[Hit] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)   # 1-based indices into hits
    status: str = "answered"                          # answered | not_in_sources | personal_refusal | insufficient
    plan: object | None = None                        # rag.hops.Plan for multi-hop answers (trace for the UI)
    graph_cited: list[int] = field(default_factory=list)
    agreed_drugs: list[str] = field(default_factory=list)   # BODHI drug list ∩ textbook-grounded answer


def evidence_block(i: int, h: Hit) -> str:
    return f"[{i}] Source: {h.citation()}\n{h.passage}"


LEADING_JUNK = re.compile(r"^\s*(?:\[G?\d+\]\s*)+(?:(?:Source:|\().*)?$")


def clean(text: str) -> str:
    """Small models sometimes open by echoing a passage header ("[1] (Robbins, ... pp. 52-61)") or a bare "[3] [8]"."""
    lines = text.strip().splitlines()
    while lines and (LEADING_JUNK.match(lines[0]) or not lines[0].strip()):
        lines.pop(0)
    return "\n".join(lines).strip() or text.strip()


def build_prompt(question: str, hits: list[Hit]) -> str:
    blocks = [evidence_block(i, h) for i, h in enumerate(hits, 1)]
    return "Evidence passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def routed_section_ids(question: str, retriever: str) -> list[str] | None:
    """vector = search everything; router = prompt-based ToC routing; stair = fine-tuned ToC retriever."""
    if retriever == "router":
        from rag.router import section_ids
        return section_ids(question)[1]
    if retriever == "stair":
        from rag.router import pick_book, toc
        from stair.serve import retrieve
        book = pick_book(question)
        t = toc(book)
        ranked = retrieve(question, book)          # raises if the STAIR model is not installed yet
        ids = [i for _, label in ranked for i in t["ids"].get(label, [])]
        return list(dict.fromkeys(ids + t["ids"].get(ranked[0][0], [])))
    return None


def answer(question: str, section_ids: list[str] | None = None, retriever: str = "vector") -> Answer:
    if PERSONAL.search(question):
        return Answer(PERSONAL_REFUSAL, status="personal_refusal")

    if section_ids is None and retriever != "vector":
        section_ids = routed_section_ids(question, retriever)
    hits = search(question, section_ids=section_ids)
    if not hits or hits[0].similarity < config.MIN_SIMILARITY:
        return Answer(NOT_IN_SOURCES, hits=hits, status="not_in_sources")

    text = clean(chat(SYSTEM, build_prompt(question, hits)))
    if "INSUFFICIENT_CONTEXT" in text:
        return Answer(NOT_IN_SOURCES, hits=hits, status="insufficient")

    # Accept [2], [1, 3] and [1][3]
    nums = [n for group in re.findall(r"\[([\d,\s]+)\]", text) for n in re.findall(r"\d+", group)]
    cited = sorted({int(n) for n in nums if 1 <= int(n) <= len(hits)})
    return Answer(text, hits=hits, cited=cited)


MULTIHOP_SYSTEM = SYSTEM + """
- Two kinds of evidence: graph facts [G1], [G2] ... from Eka Care's BODHI clinical graph, and textbook passages
  [1], [2] .... Cite each claim with the right kind.
- For symptom questions answer in this order: likely condition(s) from the graph, which specialist, then treatment /
  drug of choice from the textbook. Present conditions as a differential to consider, never as a diagnosis.
- If the textbook evidence does not cover a condition's treatment, say so instead of filling it in."""


def _cited(text: str, pattern: str, n: int) -> list[int]:
    nums = [x for grp in re.findall(pattern, text) for x in re.findall(r"\d+", grp)]
    return sorted({int(x) for x in nums if 1 <= int(x) <= n})


def answer_multihop(question: str) -> Answer:
    from rag.hops import cross_check, plan as make_plan

    if PERSONAL.search(question):
        return Answer(PERSONAL_REFUSAL, status="personal_refusal")
    p = make_plan(question)
    if p.route == "single":                       # nothing to hop over: identical to the baseline
        a = answer(question)
        a.plan = p
        return a
    if not p.evidence and not p.graph_facts:
        return Answer(NOT_IN_SOURCES, status="not_in_sources", plan=p)

    graph_block = "\n".join(f"[G{i}] {f}" for i, f in enumerate(p.graph_facts, 1))
    text_block = "\n\n".join(evidence_block(i, h) for i, h in enumerate(p.evidence, 1))
    prompt = (f"Graph facts:\n{graph_block or '(none)'}\n\nTextbook passages:\n\n{text_block or '(none)'}"
              f"\n\nQuestion: {question}\nAnswer:")
    text = clean(chat(MULTIHOP_SYSTEM, prompt, max_tokens=1100))
    if "INSUFFICIENT_CONTEXT" in text:
        return Answer(NOT_IN_SOURCES, hits=p.evidence, status="insufficient", plan=p)
    return Answer(text, hits=p.evidence, plan=p,
                  cited=_cited(text, r"\[([\d,\s]+)\]", len(p.evidence)),
                  graph_cited=_cited(text, r"\[(G\d+(?:\s*,\s*G?\d+)*)\]", len(p.graph_facts)),
                  agreed_drugs=cross_check(text, p))


if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    multi = bool(args) and args[0] == "--hops"
    q = " ".join(args[1:] if multi else args) or "What is the mechanism of action of penicillin?"
    a = answer_multihop(q) if multi else answer(q)
    print(f"[{a.status}]\n{a.text}\n")
    if a.plan:
        print(f"route: {a.plan.route}")
        for h in a.plan.hops:
            print(f"  {h.kind:9} {h.query[:70]}\n            -> {h.result[:110]}")
        for i, f in enumerate(a.plan.graph_facts, 1):
            print(f"{'*' if i in a.graph_cited else ' '}[G{i}] {f[:110]}")
    for i, h in enumerate(a.hits, 1):
        print(f"{'*' if i in a.cited else ' '}[{i}] {h.similarity:.3f}  {h.citation()}")
    if a.agreed_drugs:
        print("BODHI cross-check agrees on:", ", ".join(a.agreed_drugs))
