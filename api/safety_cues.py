"""Patient-scoped question filter for the NEW answer extras (PRD section 5 "Safety framing"): no diagram, no videos,
no topic for a question about a real person. This is NOT the safety gate (that is rag.answer._guard, which runs
before retrieval); it only decides whether our extra surfaces are offered.

    patient_scoped(question) -> True when rag.answer.PERSONAL matches (same regex _guard uses, without its trace
    side effect) or one of the cues below matches. Biased to over-matching: a false positive only hides an extra. Age-and-sex exam vignettes ("A 45-year-old man
    presents with...") are deliberately NOT a cue by themselves: they are the normal MBBS question shape.
"""
from __future__ import annotations

import re

from rag.answer import PERSONAL

_REL = (r"mother|mom|mum|mummy|father|dad|papa|wife|husband|spouse|son|daughter|child|children|baby|kid|infant|"
        r"newborn|toddler|grandma|grandpa|grandmother|grandfather|brother|sister|uncle|aunt|aunty|cousin|friend|"
        r"neighbou?r|colleague|boyfriend|girlfriend|partner|relative|in-?laws?")

CUES = re.compile(
    r"\b(patient|patients)\b"                                                  # "a patient with...", "my patient"
    r"|\b(my|our|his|her|their)\s+(" + _REL + r")\b"                           # "my mother"
    r"|\b(" + _REL + r")\s+(has|have|had|is|was|was\s+diagnosed|keeps|complains|presented|presents)\b"
    r"|\bi\s+(have|had|got|suffer|feel|am\s+(suffering|diagnosed|pregnant|having|experiencing)|'m\s+(suffering|diagnosed|pregnant|having))\b"
    r"|\bi\s+(think|suspect|believe)\s+i\b"
    r"|\b(should|can|could|may|do)\s+i\s+(take|give|stop|start|increase|decrease|double|skip|use|worry|go|see|be\s+worried)\b"
    r"|\b(am|are)\s+i\b"
    r"|\bwhat\s+(should|can|do)\s+i\s+do\b"
    r"|\b(my|me|myself)\b.*\b(symptom|symptoms|pain|rash|lump|fever|report|result|results|scan|prescription|tablet|tablets)\b"
    r"|\b(dose|dosage|dosing|how\s+many\s+(mg|tablets|pills|ml|units))\b.*\b(for|should|give|take|per\s+day|daily|twice|kg)\b"
    r"|\b(what|which)\s+(dose|dosage|medicine|medication|drug|tablet)\s+(should|do|can|to)\b"
    r"|\b\d+(\.\d+)?\s*(mg|mcg|µg|ug|ml|iu|units?)\b.*\b(should|safe|ok|okay|can|give|take)\b"
    r"|\b(should|can|could)\b.*\b\d+(\.\d+)?\s*(mg|mcg|µg|ug|ml|iu|units?)\b",
    re.I,
)


def patient_scoped(question: str | None) -> bool:
    q = (question or "").strip()
    if not q:
        return False
    return bool(PERSONAL.search(q) or CUES.search(q))
