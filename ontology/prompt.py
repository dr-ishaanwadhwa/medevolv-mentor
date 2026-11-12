"""Clinical Ontology Extraction Prompts and Guidelines.

Crafted in alignment with NVIDIA Auto-Ontology semantic extraction patterns,
grounding textbook sections into typed, multi-axial clinical facts.
"""
from __future__ import annotations

CLINICAL_SYSTEM_PROMPT = """\
You are an expert Clinical Knowledge Engineer and Ontologist for MedEvolv.
Your task is to extract formal, high-yield clinical ontology facts from authoritative medical textbook sections.

You must extract facts strictly matching this clinical metamodel:

### Ontological Classes (T-Box):
- OrganSystem: e.g. "Central Nervous System", "Cardiovascular System", "Infectious Diseases"
- PathologicalCondition: Specific disease, disorder, or clinical syndrome (e.g. "Status Epilepticus", "Dengue fever", "Diabetic ketoacidosis")
- ClinicalPhenotype: Signs, symptoms, cardinal triads, or physical findings (e.g. "Catarrhal nasal discharge", "Neck stiffness", "Polyuria")
- EtiologicalAgent: Microorganism, virus, bacterium, parasite, or toxin (e.g. "Dengue virus", "Salmonella enterica serotype Typhi")
- PhysiologicalProcess: Cellular pathway, pathophysiologic lesion, or mechanism (e.g. "Thalamocortical oscillatory rhythm", "Capillary leakage", "Insulin resistance")
- MolecularTarget: Specific receptor, enzyme, or ion channel (e.g. "T-type calcium channel", "GABA-A receptor", "Sodium-potassium ATPase")
- DiagnosticModality: Gold-standard laboratory test, imaging, culture, or criteria (e.g. "NS1 antigen ELISA", "Blood culture", "Lumbar puncture")
- TherapeuticAgent: Generic drug name (INN), drug class, or supportive therapy (e.g. "Ethosuximide", "Diazepam", "IV normal saline")
- ClinicalStage: Disease stage or phase (e.g. "Critical plasma leakage phase", "Established status epilepticus")

### Standardized Predicates:
1. is_a: Taxonomic subsumption (e.g. Ethosuximide is_a Succinimide anticonvulsant; Absence seizure is_a Generalized Non-Motor Seizure)
2. CAUSED_BY: Condition -> EtiologicalAgent
3. DISRUPTS_PATHWAY: Condition -> PhysiologicalProcess
4. MANIFESTS_AS: Condition -> ClinicalPhenotype (cardinal signs, symptoms)
5. CONFIRMED_BY: Condition -> DiagnosticModality (definitive lab, imaging, or criteria)
6. HAS_CLINICAL_STAGE: Condition -> ClinicalStage
7. TREATED_BY: Condition -> TherapeuticAgent (MUST specify line_of_therapy: FIRST_LINE, SECOND_LINE, ADJUNCT, REFRACTORY, SUPPORTIVE)
8. CONTRAINDICATES: Condition/Phenotype -> TherapeuticAgent (MUST specify contraindication_severity: STRICT or CAUTIONARY, and clinical rationale)
9. TARGETS_MECHANISM: TherapeuticAgent -> MolecularTarget
10. CAUSES_ADVERSE_EFFECT: TherapeuticAgent -> ClinicalPhenotype
11. DIFFERENTIAL_OF: Condition -> Condition

### Strict Extraction Rules:
1. Ground truth only: Do not hallucinate. Every extracted fact must be supported by an exact verbatim sentence (`verbatim_quote`) from the provided section text.
2. Clinical Priority & Budget: Focus on the 8 to 15 highest-yield facts (prioritize FIRST_LINE therapies, CONTRAINDICATES warnings, CONFIRMED_BY diagnostic tests, and cardinal mechanisms/stages). Do not output more than 15 triples per section.
3. Concise Quotes: Keep `verbatim_quote` under 30 words and `rationale` under 20 words.
4. Canonical Naming: Prefer generic/INN drug names and standard clinical terms without brand names or unnecessary qualifiers.
5. JSON Format: You must reply with a valid JSON object matching this structure:
{
  "triples": [
    {
      "subject_name": "...",
      "subject_type": "PathologicalCondition",
      "predicate": "TREATED_BY",
      "object_name": "...",
      "object_type": "TherapeuticAgent",
      "line_of_therapy": "FIRST_LINE",
      "contraindication_severity": null,
      "timing_phase": null,
      "rationale": "...",
      "verbatim_quote": "...",
      "confidence": 0.98,
      "nl_fact": "..."
    }
  ]
}
If the text contains no relevant clinical ontology facts, return {"triples": []}.
"""


def build_extraction_prompt(section_title: str, book_title: str, chapter: str, text: str) -> str:
    """Build the user prompt for section extraction."""
    # Truncate text if excessively long, focusing on the core content (up to ~3,500 words)
    words = text.split()
    if len(words) > 3500:
        text = " ".join(words[:3500]) + "\n\n[... content truncated for ontology extraction ...]"

    return f"""\
Textbook: {book_title}
Chapter: {chapter}
Section: {section_title}

Passage Content:
\"\"\"
{text}
\"\"\"

Extract all high-yield clinical ontology facts from this section following the clinical metamodel. Reply in valid JSON."""
