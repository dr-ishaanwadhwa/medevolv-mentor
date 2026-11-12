"""MedEvolv Medical Ontology Package.

Implements formal medical T-Box/A-Box ontologies, grounding to SNOMED-CT, LOINC,
and WHO INN / ATC classifications, extending BODHI-S and BODHI-M with textbook knowledge.
"""

from ontology.schema import (
    ClinicalFacet,
    ClinicalProvenance,
    ClinicalRelation,
    EntityType,
    ExtractionItem,
    LineOfTherapy,
    ProvenancedOntologyFact,
    SectionExtractionResult,
)

__all__ = [
    "EntityType",
    "ClinicalRelation",
    "LineOfTherapy",
    "ClinicalFacet",
    "ClinicalProvenance",
    "ExtractionItem",
    "SectionExtractionResult",
    "ProvenancedOntologyFact",
]
