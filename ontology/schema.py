"""Formal Pydantic Schema and Metamodel for Clinical Ontology Engineering.

Defines T-Box ontological classes, clinical relation types, taxonomic subsumptions,
multi-axial clinical facets, and complete textbook provenance records.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class EntityType(str, Enum):
    """Ontological Classes (T-Box)."""
    OrganSystem = "OrganSystem"
    PathologicalCondition = "PathologicalCondition"
    ClinicalPhenotype = "ClinicalPhenotype"
    EtiologicalAgent = "EtiologicalAgent"
    PhysiologicalProcess = "PhysiologicalProcess"
    DiagnosticModality = "DiagnosticModality"
    TherapeuticAgent = "TherapeuticAgent"
    MolecularTarget = "MolecularTarget"
    ClinicalStage = "ClinicalStage"


class ClinicalRelation(str, Enum):
    """Standardized Clinical & Ontological Predicates."""
    IS_A = "is_a"
    SUB_CONCEPT_OF = "sub_concept_of"
    PART_OF = "part_of"
    CAUSED_BY = "CAUSED_BY"
    DISRUPTS_PATHWAY = "DISRUPTS_PATHWAY"
    MANIFESTS_AS = "MANIFESTS_AS"
    CONFIRMED_BY = "CONFIRMED_BY"
    HAS_CLINICAL_STAGE = "HAS_CLINICAL_STAGE"
    TREATED_BY = "TREATED_BY"
    CONTRAINDICATES = "CONTRAINDICATES"
    TARGETS_MECHANISM = "TARGETS_MECHANISM"
    CAUSES_ADVERSE_EFFECT = "CAUSES_ADVERSE_EFFECT"
    DIFFERENTIAL_OF = "DIFFERENTIAL_OF"


class LineOfTherapy(str, Enum):
    FIRST_LINE = "FIRST_LINE"
    SECOND_LINE = "SECOND_LINE"
    ADJUNCT = "ADJUNCT"
    REFRACTORY = "REFRACTORY"
    CONTRAINDICATED = "CONTRAINDICATED"
    SUPPORTIVE = "SUPPORTIVE"


class ContraindicationSeverity(str, Enum):
    STRICT = "STRICT"
    CAUTIONARY = "CAUTIONARY"


class ClinicalFacet(BaseModel):
    """Multi-axial clinical facet metadata qualified on an ontological fact."""
    model_config = ConfigDict(extra="ignore")

    line_of_therapy: LineOfTherapy | None = None
    contraindication_severity: ContraindicationSeverity | None = None
    timing_phase: str | None = Field(default=None, description="e.g. 'Week 1', 'Day 3-7', 'Critical leakage phase'")
    organ_system: str | None = Field(default=None, description="e.g. 'Central Nervous System', 'Cardiovascular'")
    diagnostic_yield: str | None = Field(default=None, description="e.g. 'Gold standard', 'Initial screening', 'High specificity'")
    rationale: str | None = Field(default=None, description="Clinical mechanism or pharmacological rationale")


class ClinicalProvenance(BaseModel):
    """Complete academic provenance anchoring a fact to an OKF textbook section."""
    model_config = ConfigDict(extra="ignore")

    book_id: str = Field(..., description="e.g. 'tripathi', 'harrison', 'guyton', 'robbins', 'davidson', 'micro'")
    book_title: str
    chapter: str
    section_id: str
    pages: list[int] = Field(default_factory=list)
    verbatim_quote: str = Field(..., description="Verbatim sentence from the textbook proving this fact")


class ExtractionItem(BaseModel):
    """Raw structured item extracted from an OKF section by LLM."""
    model_config = ConfigDict(extra="ignore")

    subject_name: str = Field(..., description="Canonical clinical entity name")
    subject_type: EntityType = Field(..., description="T-Box class of subject")
    predicate: ClinicalRelation = Field(..., description="Clinical predicate")
    object_name: str = Field(..., description="Canonical clinical entity name")
    object_type: EntityType = Field(..., description="T-Box class of object")
    line_of_therapy: LineOfTherapy | None = Field(default=None, description="If TREATED_BY, specify priority")
    contraindication_severity: ContraindicationSeverity | None = Field(default=None, description="If CONTRAINDICATES, specify severity")
    timing_phase: str | None = Field(default=None, description="Timing, phase, or clinical duration if applicable")
    rationale: str | None = Field(default=None, description="Clinical rationale or mechanism of action")
    verbatim_quote: str = Field(..., description="Exact verbatim sentence supporting this extraction")
    confidence: float = Field(ge=0.0, le=1.0, default=0.95)
    nl_fact: str = Field(..., description="Clear, concise natural language fact statement")


class SectionExtractionResult(BaseModel):
    """Collection of extracted facts for an individual OKF section."""
    section_id: str
    book_id: str
    chapter: str
    triples: list[ExtractionItem] = Field(default_factory=list)


class ProvenancedOntologyFact(BaseModel):
    """Reconciled, certified ontological fact ready for graph loading & reasoning."""
    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="Unique fact ID, e.g. ont-harrison-222-001")
    subject_id: str = Field(..., description="SNOMED-CT, INN, LOINC, or minted MED:OKF URI")
    subject_label: str
    subject_type: EntityType
    predicate: ClinicalRelation
    object_id: str = Field(..., description="SNOMED-CT, INN, LOINC, or minted MED:OKF URI")
    object_label: str
    object_type: EntityType
    confidence: float = 0.95
    status: Literal["CERTIFIED", "CANDIDATE"] = "CERTIFIED"
    clinical_facets: ClinicalFacet = Field(default_factory=ClinicalFacet)
    provenance: ClinicalProvenance
    nl_fact: str
    # Every section that supports this triple (the compiler merges duplicates); provenance is the primary one.
    sources: list[ClinicalProvenance] = Field(default_factory=list)
    # Second-pass check that each quote states the triple (ontology/verifier.py): "yes" | "partial" | None
    llm_check: str | None = None
