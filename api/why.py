"""\"Why was I wrong?\" for one MCQ: retrieve textbook passages, ask the model for a strict-JSON verdict, validate it.

Cite-or-decline: a verdict is only returned when the model names the correct option, the explanation cites real
passage numbers, and (for a verdict) there are exactly three viva questions. Anything else becomes
status "insufficient" -- never an invented answer. Runs synchronously; the gateway calls it in a worker thread."""
from __future__ import annotations

import json
import re

from api import spatial
from api.schemas import AnswerCitation, VerdictEvent, WhyRequest
from rag import config, trace
from rag.backends import chat
from rag.retrieve import Hit, search

LETTERS = "ABCDEF"
MAX_PASSAGES = 10
INSUFFICIENT_TEXT = "The textbooks in the library don't settle this."

SYSTEM = """You are MedEvolv Mentor, a study companion for medical students. A student answered a multiple-choice question
and wants to know why. Use ONLY the numbered textbook passages; no outside knowledge.
Reply with ONE JSON object and nothing else:
{"grounded": true|false,
 "correct_option": "A".."F" or null,
 "chosen_wrong_because": "1-3 sentences on why the student's chosen option is wrong (or, if it was correct, say so and why)",
 "explanation": "markdown, concise; why the correct option is right and the others are not",
 "viva_questions": ["three short oral-exam follow-up questions answerable from the same passages"]}
Rules:
- Cite every claim with passage numbers in square brackets, e.g. [2]. Use only numbers that exist, in explanation and chosen_wrong_because.
- If the passages do not let you determine the correct option, set "grounded": false, "correct_option": null and leave the other fields empty.
- Never invent facts, doses or page numbers. Never give advice about a real patient."""

_CITE = re.compile(r"\[([\d,\s]+)\]")


def _cites(text: str) -> set[int]:
    return {int(n) for g in _CITE.findall(text or "") for n in re.findall(r"\d+", g)}


def retrieve(req: WhyRequest) -> list[Hit]:
    """Stem, plus stem + each option: best similarity per passage, above the relevance threshold, strongest first."""
    stem = req.question.strip()
    best: dict[str, Hit] = {}
    for q, k in [(stem, 5)] + [(f"{stem}\n{o}", 3) for o in req.options]:
        for h in search(q, k=k):
            if h.id not in best or h.similarity > best[h.id].similarity:
                best[h.id] = h
    hits = sorted((h for h in best.values() if h.similarity >= config.MIN_SIMILARITY), key=lambda h: -h.similarity)
    return hits[:MAX_PASSAGES]


def build_prompt(req: WhyRequest, hits: list[Hit]) -> str:
    opts = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(req.options))
    blocks = "\n\n".join(f"[{i}] Source: {h.citation()}\n{h.passage}" for i, h in enumerate(hits, 1))
    return (f"Evidence passages:\n\n{blocks}\n\nQuestion: {req.question}\n\nOptions:\n{opts}\n\n"
            f"The student chose {LETTERS[req.chosen]}. JSON:")


def parse(raw: str) -> dict | None:
    """The model's JSON object, tolerating code fences and surrounding prose; None when it is not an object."""
    m = re.search(r"\{.*\}", raw or "", re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def validate(obj: dict, req: WhyRequest, n_hits: int) -> tuple[VerdictEvent | None, str]:
    """(verdict, "") when the model's JSON is a well-grounded verdict, else (None, reason)."""
    if obj.get("grounded") is False:
        return None, "model says the passages do not settle it"
    letter = str(obj.get("correct_option") or "").strip().upper()[:1]
    if letter not in LETTERS[:len(req.options)]:
        return None, "no valid correct option"
    why, expl = obj.get("chosen_wrong_because"), obj.get("explanation")
    viva = obj.get("viva_questions")
    if not (isinstance(why, str) and isinstance(expl, str) and why.strip() and expl.strip()):
        return None, "missing explanation"
    if not isinstance(viva, list) or len([v for v in viva if isinstance(v, str) and v.strip()]) < 3:
        return None, "fewer than three viva questions"
    nums = _cites(expl) | _cites(why)
    if not _cites(expl) or any(not 1 <= n <= n_hits for n in nums):
        return None, "missing or invalid citations"
    correct = LETTERS.index(letter)
    why = why.strip()
    if correct == req.chosen and "correct" not in why.lower():
        why = f"Your choice was correct. {why}"
    return VerdictEvent(status="verdict", correct_option=correct, chosen_wrong_because=why, explanation=expl.strip(),
                        viva_questions=[v.strip() for v in viva if isinstance(v, str) and v.strip()][:3]), ""


def insufficient(hits: list[Hit] | None = None) -> VerdictEvent:
    return VerdictEvent(status="insufficient", explanation=INSUFFICIENT_TEXT,
                        citations=[spatial.pointer_from_hit(i, h, False) for i, h in enumerate(hits or [], 1)])


def run(req: WhyRequest) -> VerdictEvent:
    if req.chosen >= len(req.options):
        raise ValueError("chosen is out of range")
    hits = retrieve(req)
    if not hits:
        trace.record("filter", "Relevance threshold", "No passage reached the relevance threshold: the books do not cover this.",
                     status="stop")
        return insufficient()
    books = sorted({h.meta.get("book_id") for h in hits})
    trace.record("evidence", f"{len(hits)} numbered passages sent to the model", "From: " + ", ".join(books))
    prompt, reason = build_prompt(req, hits), "unparseable model output"
    for attempt in range(2):                        # one retry: small models sometimes break the JSON contract
        obj = parse(chat(SYSTEM, prompt, max_tokens=1200, json_mode=True,
                         purpose="Judge the MCQ from textbook passages" + (" (retry)" if attempt else "")))
        if obj is None:
            reason = "unparseable model output"
            continue
        verdict, reason = validate(obj, req, len(hits))
        if verdict is not None:
            cited = _cites(verdict.explanation) | _cites(verdict.chosen_wrong_because)
            verdict.citations = [spatial.pointer_from_hit(i, h, i in cited) for i, h in enumerate(hits, 1)]
            trace.record("cite", "Citation check", f"{len(cited)} of {len(hits)} passages cited; every [n] checked against the evidence.")
            return verdict
        if obj.get("grounded") is False:
            break
    trace.record("refuse", "Declined: verdict not grounded", reason, status="stop")
    return insufficient(hits)
