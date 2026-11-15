"""The `topic` of an answer and its related topics (PRD 4.2 "Topic" and "Related topics").

topic is a structured label (never question or answer prose). Source order: (1) diagrams.pick_subject (a condition or
drug in the ontology), (2) the label of the first spatial highlight action, (3) the first concept recognised in the
question or answer that resolves exactly to an ontology concept. `related` = up to 6 certified links_out of the topic's
concept (our own data). Declined and patient-scoped questions always get topic None and no related list.
"""
from __future__ import annotations

from api import spatial
from api.safety_cues import patient_scoped
from api.schemas import RelatedTopic, SpatialAction, TopicEvent
from rag import concepts, diagrams

MAX_RELATED = 6


def _safe(fn, default=None):
    try:                                           # optional layers (ontology, graph): a missing file just means no topic
        return fn()
    except Exception:                              # noqa: BLE001
        return default


def related_for(topic: str) -> list[RelatedTopic]:
    c = _safe(lambda: concepts.concept(topic), {}) or {}
    best: dict[str, tuple[int, RelatedTopic]] = {}
    for pred, links in (c.get("outgoing") or {}).items():
        for lk in links:
            if lk.get("tier") != "certified" or lk["other_id"] == c.get("id") or not lk.get("other_label"):
                continue
            n_books = len(lk.get("books") or [])
            if lk["other_id"] not in best or n_books > best[lk["other_id"]][0]:
                best[lk["other_id"]] = (n_books, RelatedTopic(id=lk["other_id"], label=lk["other_label"], predicate=pred))
    ranked = sorted(best.values(), key=lambda t: (-t[0], t[1].label.lower()))
    return [r for _, r in ranked[:MAX_RELATED]]


def pick(question: str, answer, actions: list[SpatialAction]) -> str | None:
    conds = getattr(getattr(answer, "plan", None), "conditions", None) or []
    subject = _safe(lambda: diagrams.pick_subject(question, condition=conds[0] if conds else None))
    if subject:
        return subject[1]
    if actions:
        return actions[0].label
    for c in _safe(lambda: spatial.recognised_concepts(question, answer.text), []) or []:
        if _safe(lambda: concepts.concept(c["label"])):
            return c["label"]
    return None


def topic_event(question: str, answer, actions: list[SpatialAction]) -> TopicEvent:
    if getattr(answer, "status", "") != "answered" or patient_scoped(question):
        return TopicEvent(topic=None, related=[])
    topic = pick(question, answer, actions)
    return TopicEvent(topic=topic, related=related_for(topic) if topic else [])
