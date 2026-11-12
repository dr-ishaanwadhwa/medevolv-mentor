"""Canonical Medical Entity Registry & Synset Engine.

Reconciles raw clinical entity mentions against the 6,560 BODHI nodes (SNOMED-CT,
LOINC, WHO INN) and provides comprehensive synset mapping for medical terminology,
eponyms, and clinical acronyms.
"""
from __future__ import annotations

import functools
import re
from typing import Any
from ontology.normalizer import clean_medical_text, mint_uri, normalize_drug_name, slugify
from ontology.schema import EntityType

# Comprehensive Medical Synsets & Acronyms
MEDICAL_SYNSETS: dict[str, str] = {
    # Acronyms
    "dka": "Diabetic ketoacidosis",
    "stemi": "ST elevation myocardial infarction",
    "nstemi": "Non-ST elevation myocardial infarction",
    "acs": "Acute coronary syndrome",
    "mi": "Myocardial infarction",
    "tb": "Tuberculosis",
    "mdr-tb": "Multidrug-resistant tuberculosis",
    "xdr-tb": "Extensively drug-resistant tuberculosis",
    "copd": "Chronic obstructive pulmonary disease",
    "sle": "Systemic lupus erythematosus",
    "csf": "Cerebrospinal fluid",
    "lp": "Lumbar puncture",
    "ards": "Acute respiratory distress syndrome",
    "uti": "Urinary tract infection",
    "gerd": "Gastroesophageal reflux disease",
    "ckd": "Chronic kidney disease",
    "aki": "Acute kidney injury",
    "esrd": "End stage renal disease",
    "hhs": "Hyperosmolar hyperglycemic state",
    "dic": "Disseminated intravascular coagulation",
    "afib": "Atrial fibrillation",
    "a-fib": "Atrial fibrillation",

    # Upper Respiratory / Coryza
    "coryza": "Catarrhal nasal discharge",
    "runny nose": "Catarrhal nasal discharge",
    "rhinorrhea": "Catarrhal nasal discharge",
    "nasal congestion": "Catarrhal nasal discharge",
    "nasal discharge": "Catarrhal nasal discharge",

    # Cardinal Symptoms
    "polyuria": "Passing excessive urine",
    "excessive urination": "Passing excessive urine",
    "frequent urination": "Passing excessive urine",
    "polydipsia": "Excessive thirst",
    "polyphagia": "Excessive hunger",
    "radiating chest pain": "Chest pain radiating to left arm",
    "radiating pain": "Chest pain radiating to left arm",
    "diaphoresis": "Excessive sweating",
    "profuse sweating": "Excessive sweating",
    "night sweats": "Night sweats",
    "fever with chills": "Fever with chills",
    "rigors": "Fever with chills",
    "unintentional weight loss": "Weight loss",
    "hemoptysis": "Coughing up blood",
    "blood in sputum": "Coughing up blood",
    "dyspnea": "Breathlessness",
    "shortness of breath": "Breathlessness",
    "headache": "Headache",
    "arthralgia": "Joint pain",
    "polyarthralgia": "Joint pain",
    "polyarthralgias": "Joint pain",
    "retro-orbital pain": "Eye pain",
    "photophobia": "Photophobia",
    "nuchal rigidity": "Neck stiffness",
    "neck stiffness": "Neck stiffness",

    # Clinical Eponyms
    "graves disease": "Toxic diffuse goiter",
    "graves' disease": "Toxic diffuse goiter",
    "hashimoto thyroiditis": "Hashimoto thyroiditis",
    "hashimoto's thyroiditis": "Hashimoto thyroiditis",
    "parkinson disease": "Parkinson's disease",
    "parkinson's disease": "Parkinson's disease",
    "crohn disease": "Crohn's disease",
    "crohn's disease": "Crohn's disease",
    "bell palsy": "Bell's palsy",
    "bell's palsy": "Bell's palsy",

    # Drug Synonyms & Salt Normalizations
    "adrenaline": "Epinephrine",
    "noradrenaline": "Norepinephrine",
    "paracetamol": "Acetaminophen",
    "frusemide": "Furosemide",
    "salbutamol": "Albuterol",
    "ethosuccimide": "Ethosuximide",
    "sodium valproate": "Valproate",
    "valproic acid": "Valproate",
    "fosphenytoin sodium": "Fosphenytoin",
    "phenobarbitone": "Phenobarbital",
}


class EntityRegistry:
    """In-memory index of canonical concepts from BODHI and textbook ontologies."""

    def __init__(self) -> None:
        self._name_to_node: dict[str, dict[str, Any]] = {}
        self._id_to_node: dict[str, dict[str, Any]] = {}
        self._synsets = {k.lower(): v for k, v in MEDICAL_SYNSETS.items()}
        self._load_bodhi()

    def _load_bodhi(self) -> None:
        """Load BODHI nodes into lookup tables."""
        from rag.graph import load_graph
        g = load_graph()
        for nid, d in g.nodes(data=True):
            name = d.get("name", "")
            ntype = d.get("type", "Concept")
            entry = {"id": nid, "name": name, "type": ntype, "full_name": d.get("full_name", name)}
            self._id_to_node[nid] = entry
            clean_name = clean_medical_text(name).lower()
            if clean_name:
                self._name_to_node.setdefault(clean_name, entry)

    def resolve(self, text: str, entity_type: EntityType | str, book_id: str = "okf") -> tuple[str, str, str]:
        """Resolve a raw mention to (canonical_id, canonical_label, resolved_type).

        Returns:
            canonical_id: SNOMED/LOINC ID if in BODHI, or minted 'MED:OKF/...' URI.
            canonical_label: Normalized, user-friendly label.
            resolved_type: Ontological EntityType.
        """
        raw = clean_medical_text(text)
        low = raw.lower()

        # 1. Check synsets / acronyms
        if low in self._synsets:
            raw = self._synsets[low]
            low = raw.lower()

        # 2. Check exact / normalized match in BODHI
        if low in self._name_to_node:
            node = self._name_to_node[low]
            return node["id"], node["name"], node["type"]

        # 3. Check drug name normalization
        if entity_type in (EntityType.TherapeuticAgent, "Drug"):
            clean_drug = normalize_drug_name(raw)
            clean_drug_low = clean_drug.lower()
            if clean_drug_low in self._name_to_node:
                node = self._name_to_node[clean_drug_low]
                return node["id"], node["name"], node["type"]
            # Check synset again for normalized drug
            if clean_drug_low in self._synsets:
                syn_low = self._synsets[clean_drug_low].lower()
                if syn_low in self._name_to_node:
                    node = self._name_to_node[syn_low]
                    return node["id"], node["name"], node["type"]
            raw = clean_drug

        # 4. Mint stable URI for newly discovered concepts
        type_str = entity_type.value if isinstance(entity_type, EntityType) else str(entity_type)
        minted_id = mint_uri(book_id, raw, type_str)
        return minted_id, raw, type_str


@functools.cache
def get_registry() -> EntityRegistry:
    """Singleton accessor for the entity registry."""
    return EntityRegistry()
