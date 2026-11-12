"""Clinical Entity Reconciliation and Canonical Fact Certification.

Adapts reconciliation patterns from NVIDIA Auto-Ontology (semantic_fk, deterministic)
to map raw extracted triples into certified, provenanced facts grounded in BODHI.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from ontology.normalizer import clean_medical_text
from ontology.registry import get_registry
from ontology.schema import (
    ClinicalRelation as R,
    EntityType as T,
    ClinicalFacet,
    ClinicalProvenance,
    ExtractionItem,
    ProvenancedOntologyFact,
    SectionExtractionResult,
)


_COND = {T.PathologicalCondition, T.ClinicalStage}
_COND_P = _COND | {T.ClinicalPhenotype}
# predicate -> (allowed subject types, allowed object types); directions follow ontology/prompt.py
TYPE_RULES: dict[R, tuple[set, set]] = {
    R.TREATED_BY: (_COND_P, {T.TherapeuticAgent}),
    R.CONTRAINDICATES: (_COND_P, {T.TherapeuticAgent}),          # drug-drug interactions are not this
    R.CAUSED_BY: (_COND_P, {T.EtiologicalAgent, T.PhysiologicalProcess, T.PathologicalCondition,
                            T.TherapeuticAgent}),                  # incl. drug-induced / secondary disease
    R.MANIFESTS_AS: (_COND_P, {T.ClinicalPhenotype}),
    R.CONFIRMED_BY: (_COND_P, {T.DiagnosticModality}),
    R.HAS_CLINICAL_STAGE: (_COND, {T.ClinicalStage}),
    R.DISRUPTS_PATHWAY: (_COND | {T.EtiologicalAgent}, {T.PhysiologicalProcess}),
    R.TARGETS_MECHANISM: ({T.TherapeuticAgent}, {T.MolecularTarget, T.PhysiologicalProcess}),
    R.CAUSES_ADVERSE_EFFECT: ({T.TherapeuticAgent}, {T.ClinicalPhenotype, T.PathologicalCondition}),
    R.DIFFERENTIAL_OF: (_COND_P, _COND_P),
}


def check_direction(pred, s_type, o_type) -> str:
    """'ok' | 'swap' (subject and object are reversed) | 'drop' (types don't fit this predicate)."""
    if pred in (R.IS_A, R.SUB_CONCEPT_OF):
        return "ok" if s_type == o_type else "drop"
    rule = TYPE_RULES.get(pred)
    if rule is None:
        return "ok"
    subj, obj = rule
    if s_type in subj and o_type in obj:
        return "ok"
    if o_type in subj and s_type in obj:
        return "swap"
    return "drop"


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def quote_in_source(quote: str, source_norm: str) -> bool:
    """A 'verbatim' quote must really be in the section. Ellipses are allowed: every fragment of 3+ words
    must appear. Compared after lower-casing and dropping punctuation (PDF text has odd hyphens/quotes)."""
    frags = [_norm(f) for f in re.split(r"\.\.\.|…", quote)]
    frags = [f for f in frags if len(f.split()) >= 3]
    return bool(frags) and all(f in source_norm for f in frags)


def reconcile_section_facts(
    result: SectionExtractionResult,
    meta: dict[str, Any],
    min_confidence: float = 0.85,
    source_text: str | None = None,
    stats: dict | None = None,
) -> list[ProvenancedOntologyFact]:
    """Reconcile extraction items into grounded facts. With source_text, a fact is CERTIFIED only if its quote
    is found in the section; otherwise it is kept as CANDIDATE (and excluded from the app)."""
    stats = stats if stats is not None else {}
    source_norm = _norm(source_text) if source_text else None
    registry = get_registry()
    book_id = result.book_id
    book_title = meta.get("book", book_id.capitalize())
    chapter = result.chapter
    section_id = result.section_id
    pages = meta.get("pages", [])
    if isinstance(pages, int):
        pages = [pages]

    certified_facts: list[ProvenancedOntologyFact] = []

    for idx, item in enumerate(result.triples):
        if item.confidence < min_confidence:
            stats["low_confidence"] = stats.get("low_confidence", 0) + 1
            continue
        verdict = check_direction(item.predicate, item.subject_type, item.object_type)
        if verdict == "drop":
            stats["wrong_types"] = stats.get("wrong_types", 0) + 1
            continue
        if verdict == "swap":
            stats["swapped"] = stats.get("swapped", 0) + 1
            item = item.model_copy(update={
                "subject_name": item.object_name, "subject_type": item.object_type,
                "object_name": item.subject_name, "object_type": item.subject_type})

        # Reconcile subject and object with canonical registry (BODHI SNOMED/INN or minted URI)
        verified = quote_in_source(item.verbatim_quote, source_norm) if source_norm is not None else False
        stats["verified" if verified else "unverified"] = stats.get("verified" if verified else "unverified", 0) + 1
        sub_id, sub_label, sub_type = registry.resolve(item.subject_name, item.subject_type, book_id)
        obj_id, obj_label, obj_type = registry.resolve(item.object_name, item.object_type, book_id)

        # Generate unique fact ID
        hash_suffix = hashlib.md5(f"{section_id}:{sub_id}:{item.predicate.value}:{obj_id}".encode()).hexdigest()[:8]
        fact_id = f"ont-{book_id}-{hash_suffix}"

        facets = ClinicalFacet(
            line_of_therapy=item.line_of_therapy,
            contraindication_severity=item.contraindication_severity,
            timing_phase=item.timing_phase,
            rationale=item.rationale,
        )

        provenance = ClinicalProvenance(
            book_id=book_id,
            book_title=book_title,
            chapter=chapter,
            section_id=section_id,
            pages=pages,
            verbatim_quote=item.verbatim_quote.strip(),          # kept exactly as found in the source
        )

        fact = ProvenancedOntologyFact(
            id=fact_id,
            subject_id=sub_id,
            subject_label=sub_label,
            subject_type=item.subject_type,
            predicate=item.predicate,
            object_id=obj_id,
            object_label=obj_label,
            object_type=item.object_type,
            confidence=item.confidence,
            status="CERTIFIED" if verified else "CANDIDATE",
            clinical_facets=facets,
            provenance=provenance,
            nl_fact=item.nl_fact.strip(),
        )
        certified_facts.append(fact)

    return certified_facts
