"""Clinical Entity Reconciliation and Canonical Fact Certification.

Adapts reconciliation patterns from NVIDIA Auto-Ontology (semantic_fk, deterministic)
to map raw extracted triples into certified, provenanced facts grounded in BODHI.
"""
from __future__ import annotations

import hashlib
from typing import Any

from ontology.normalizer import clean_medical_text
from ontology.registry import get_registry
from ontology.schema import (
    ClinicalFacet,
    ClinicalProvenance,
    ExtractionItem,
    ProvenancedOntologyFact,
    SectionExtractionResult,
)


def reconcile_section_facts(
    result: SectionExtractionResult,
    meta: dict[str, Any],
    min_confidence: float = 0.85,
) -> list[ProvenancedOntologyFact]:
    """Reconcile and certify extraction items into grounded ProvenancedOntologyFacts."""
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
            continue

        # Reconcile subject and object with canonical registry (BODHI SNOMED/INN or minted URI)
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
            verbatim_quote=clean_medical_text(item.verbatim_quote),
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
            status="CERTIFIED",
            clinical_facets=facets,
            provenance=provenance,
            nl_fact=item.nl_fact.strip(),
        )
        certified_facts.append(fact)

    return certified_facts
