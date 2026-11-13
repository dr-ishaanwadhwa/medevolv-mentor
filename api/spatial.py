"""Deterministic spatial hints and resolution. Everything here is derived from rag.atlas / rag.concepts lookups:
no LLM, no clinical claim. An FMA id is only ever emitted if the atlas crosswalk links it."""
from __future__ import annotations

import re

from rag import atlas, concepts, config, mentions, ontology_facts as onto
from api.schemas import (EXCERPT_MAX, AnswerCitation, AtlasLink, Citation, ConceptRef, RelatedConcept,
                         SpatialAction)

MAX_ACTIONS = 8
MAX_CITATIONS = 10
MAX_SECTION_CONCEPTS = 40
BOOK_NAMES = {"tripathi": "KD Tripathi Pharmacology", "guyton": "Guyton & Hall Physiology", "robbins": "Robbins Pathology",
              "davidson": "Davidson Medicine", "micro": "Microbiology", "harrison": "Harrison Internal Medicine",
              "grays": "Gray's Anatomy"}


def excerpt(text: str) -> str:
    return text[:EXCERPT_MAX] + ("…" if len(text) > EXCERPT_MAX else "")


def pointer_from_hit(i: int, hit, cited: bool) -> AnswerCitation:
    m = hit.meta
    return AnswerCitation(index=i, cited=cited, book=m.get("book") or m.get("book_id", ""), edition=str(m.get("edition", "")),
                          chapter=m.get("chapter", ""), pages=str(m.get("pages", "")), section_id=m.get("section_id", ""),
                          excerpt=excerpt(hit.passage))


def _ids(record: dict) -> list[str]:
    return list(record.get("atlas_ids") or [record["atlas_id"]])


def _action(label: str, record: dict) -> SpatialAction:
    return SpatialAction(fma_ids=_ids(record), label=label)


def section_concept_labels(section_id: str) -> list[str]:
    """Labels of anatomical-structure concepts the certified ontology ties to a section (best connected first)."""
    nodes = [n for n in concepts._index()["nodes"].values()
             if section_id in n["sections"] and n["type"] == "AnatomicalStructure"]
    nodes.sort(key=lambda n: -n["degree"])
    return [n["label"] for n in nodes[:MAX_SECTION_CONCEPTS]]


def spatial_actions(answer) -> list[SpatialAction]:
    """Highlight hints for an Answer: (1) the plan's conditions -> INVOLVES_STRUCTURE structures, (2) a cited Gray's
    section's own topic, (3) anatomical concepts of the cited sections. Deduplicated by FMA ids, capped."""
    out: list[SpatialAction] = []
    seen: set[tuple[str, ...]] = set()

    def add(label: str, record: dict | None) -> None:
        if not record or len(out) >= MAX_ACTIONS:
            return
        key = tuple(sorted(_ids(record)))
        if key not in seen:
            seen.add(key)
            out.append(_action(label, record))

    plan = getattr(answer, "plan", None)
    for cond in getattr(plan, "conditions", None) or []:
        for s in atlas.structures_for(cond):
            add(s["label"], atlas.atlas_record(s["label"]))
    cited_hits = [answer.hits[i - 1] for i in answer.cited if 1 <= i <= len(answer.hits)]
    for h in cited_hits:
        t = atlas.for_section(h.meta)
        if t:
            add(t["label"], atlas.atlas_record(t["label"]))
    for sid in dict.fromkeys(h.meta.get("section_id", "") for h in cited_hits):
        for label in section_concept_labels(sid) if sid else []:
            add(label, atlas.atlas_record(label))
    return out


def _records_for_fma(fma: str) -> list[dict]:
    seen, out = set(), []
    for r in atlas.links().values():
        if fma in _ids(r) and r["key"] not in seen:
            seen.add(r["key"])
            out.append(r)
    return out


def _pointer(book_id: str, section_id: str, chapter: str = "", pages: str = "", book: str = "", edition: str = "") -> Citation:
    return Citation(book=book or BOOK_NAMES.get(book_id, book_id), edition=edition, chapter=chapter, pages=pages,
                    section_id=section_id)


def concept_citations(label: str, concept_id: str) -> list[Citation]:
    """Pointer-only citations: certified-fact sources for the concept, then mention-index sections (Gray's first)."""
    out: list[Citation] = []
    seen: set[str] = set()
    for f in onto.facts():
        if concept_id not in (f.get("subject_id"), f.get("object_id")):
            continue
        for p in onto.sources(f):
            sid = p.get("section_id", "")
            if sid and sid not in seen:
                seen.add(sid)
                pages = p.get("pages") or []
                out.append(_pointer(p.get("book_id", ""), sid, re_chapter(p.get("chapter", "")),
                                    f"{pages[0]}-{pages[-1]}" if pages else "", p.get("book_title", ""), str(p.get("edition", ""))))
    try:
        rows = sorted(mentions.sections_for(label, k=MAX_CITATIONS), key=lambda r: r["book_id"] != "grays")
    except Exception:           # optional layer: a missing or differently-versioned data/graph must not break the endpoint
        rows = []
    for r in rows:
        if r["section_id"] not in seen:
            seen.add(r["section_id"])
            parts = [x for x in (r.get("path") or "").split(" › ") if x]
            out.append(_pointer(r["book_id"], r["section_id"], parts[1] if len(parts) > 1 else r.get("title", "")))
    return out[:MAX_CITATIONS]


def re_chapter(c: str) -> str:
    return re.sub(r"^\d+\.?\s*", "", c or "")


def resolve(fma: str | None, label: str | None) -> dict | None:
    """Everything known about one structure; None when neither the atlas nor the ontology knows it."""
    records: list[dict] = []
    if fma:
        records = _records_for_fma(fma)
    elif label:
        r = atlas.atlas_record(label)
        records = [r] if r else []
    names = [r["label"] for r in records] + ([label] if label else [])
    concept = {}
    for n in names:
        concept = concepts.concept(n)
        if concept:
            break
    if not records and not concept:
        return None
    ids = list(dict.fromkeys(i for r in records for i in _ids(r)))
    shown = (concept or {}).get("label") or (records[0]["label"] if records else label or "")
    return {
        "fma_ids": ids, "label": shown,
        "atlas": [AtlasLink(label=r["label"], atlas_name=r["atlas_name"], fma_ids=_ids(r),
                            url=atlas.record_url(r) if config.ATLAS_URL else None) for r in records],
        "concept": ConceptRef(id=concept["id"], label=concept["label"], type=concept["type"], aliases=concept["aliases"],
                              degree=concept["degree"], books=concept["books"]) if concept else None,
        "citations": concept_citations(concept["label"], concept["id"]) if concept else [],
        "related": [RelatedConcept(**{k: r[k] for k in ("id", "label", "type", "shared_facts", "tier")})
                    for r in concepts.related(concept["id"], k=10)] if concept else [],
    }
