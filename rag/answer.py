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

SYSTEM = """You are a pharmacology study companion for medical students, built on Eka Care's knowledge sources.
Rules:
- Answer ONLY from the numbered evidence passages. Do not use outside knowledge.
- Cite every claim with the passage number in square brackets, e.g. [2]. Use only numbers that exist.
- If the evidence does not contain the answer, reply exactly: INSUFFICIENT_CONTEXT
- If only part of the question is covered, answer that part and state plainly which part the sources do not cover.
- Be concise and exam-oriented: short paragraphs or bullet points.
- Never give dosing or treatment advice for a specific real person."""

NOT_IN_SOURCES = ("I couldn't find this in my textbook sources, so I won't guess. "
                  "Try rephrasing, or ask about a topic covered in the pharmacology textbook.")
PERSONAL_REFUSAL = ("I'm a study aid, so I can't advise on treatment or dosing for a real person — please ask a "
                    "doctor or pharmacist. I can explain what the textbook says about the drug or condition in general.")


@dataclass
class Answer:
    text: str
    hits: list[Hit] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)   # 1-based indices into hits
    status: str = "answered"                          # answered | not_in_sources | personal_refusal | insufficient


def build_prompt(question: str, hits: list[Hit]) -> str:
    blocks = [f"[{i}] ({h.citation()})\n{h.passage}" for i, h in enumerate(hits, 1)]
    return "Evidence passages:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}\nAnswer:"


def answer(question: str, section_ids: list[str] | None = None) -> Answer:
    if PERSONAL.search(question):
        return Answer(PERSONAL_REFUSAL, status="personal_refusal")

    hits = search(question, section_ids=section_ids)
    if not hits or hits[0].similarity < config.MIN_SIMILARITY:
        return Answer(NOT_IN_SOURCES, hits=hits, status="not_in_sources")

    text = chat(SYSTEM, build_prompt(question, hits)).strip()
    if "INSUFFICIENT_CONTEXT" in text:
        return Answer(NOT_IN_SOURCES, hits=hits, status="insufficient")

    # Accept [2], [1, 3] and [1][3]
    nums = [n for group in re.findall(r"\[([\d,\s]+)\]", text) for n in re.findall(r"\d+", group)]
    cited = sorted({int(n) for n in nums if 1 <= int(n) <= len(hits)})
    return Answer(text, hits=hits, cited=cited)


if __name__ == "__main__":
    import sys
    a = answer(" ".join(sys.argv[1:]) or "What is the mechanism of action of penicillin?")
    print(f"[{a.status}]\n{a.text}\n")
    for i, h in enumerate(a.hits, 1):
        mark = "*" if i in a.cited else " "
        print(f"{mark}[{i}] {h.similarity:.3f}  {h.citation()}")
