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


# The extractor over-promotes drugs to FIRST_LINE when the source hedges ("a well tolerated alternative",
# "can also be effective", "if X fails"). Measured on 704 cached FIRST_LINE items: 108 state it explicitly,
# 43 hedge, 553 are neutral (a 12-item sample of neutral ones was ~10/12 sound). So: explicit -> keep,
# hedged -> downgrade, neutral -> keep. A strict "must say first-line" rule removed 87% and emptied MI.
FIRST_LINE_CUE = re.compile(
    r"first[- ](line|tier|choice)|(drugs?|agents?|treatment|therapy) of (first )?choice|preferred|mainstay|"
    r"cornerstone|standard (therapy|treatment|of care|regimen|practice)|initial (therapy|treatment|drug)|"
    r"recommended (as|for|first)|primary (therapy|treatment)", re.I)
HEDGE_CUE = re.compile(
    r"\balternative|\b(may|can) (also )?be (used|tried|considered|added|given|useful|effective)|\boptions?\b|"
    r"\bin (some|selected|certain)\b|\bsecond[- ]line|\bif\b.{0,40}\b(fail|not toleran|intoleran|contraindicat|resistan)|"
    r"\brefractory|\breserved\b|\boccasional|\bhas been (used|tried)|\badjunct|\badd[- ]on|"
    r"\bless (commonly|often)|\binstead\b|\bexperimental|\bunder (study|investigation)|\bmay benefit|"
    r"\bsome patients", re.I)


def gate_line_of_therapy(pred, line, quote: str):
    """('keep'|'downgrade'|'clear'|'drop', new_line). Line of therapy only means something for TREATED_BY;
    FIRST_LINE is removed when the quote hedges (and doesn't also say first-line); 'TREATED_BY ... CONTRAINDICATED'
    contradicts itself."""
    value = getattr(line, "value", line)
    if pred != R.TREATED_BY:
        return ("clear", None) if value else ("keep", line)
    if value == "CONTRAINDICATED":
        return "drop", None
    if value == "FIRST_LINE" and HEDGE_CUE.search(quote or "") and not FIRST_LINE_CUE.search(quote or ""):
        return "downgrade", None
    return "keep", line


# A treatment/diagnostic fact whose own quote rejects it ("Cephalosporins are not effective", "lidocaine infusion
# is not recommended") is the opposite of the fact. Tier A run: 213 of 9,144 TREATED_BY/CONFIRMED_BY quotes had a
# negation cue, about half real reversals; the rest were conditionals ("If ineffective, topiramate is next"),
# hence the sentence + object + not-after-if/when rule below.
NEGATION_CUE = re.compile(
    r"\b(should (be )?avoided|avoid(ed)?|should not|must not|not (be )?(recommended|indicated|effective|useful|"
    r"helpful|beneficial)|contraindicated|ineffective|no (role|benefit|proven)|impractical|of no value|not proved|"
    r"has not been shown)\b", re.I)
CONDITIONAL = re.compile(r"\b(if|when|unless|whom|where|or)\b[^.;]{0,40}$", re.I)


def negated_in_quote(pred, obj_name: str, quote: str) -> bool:
    """True when a sentence of the quote that names the object (or the drug's first word) also rejects it,
    and the rejection is not a condition ('if ... ineffective', 'when contraindicated')."""
    if pred not in (R.TREATED_BY, R.CONFIRMED_BY) or not quote:
        return False
    tokens = [w for w in re.findall(r"[a-z]{4,}", (obj_name or "").lower())][:2]
    for sent in re.split(r"(?<=[.;!?])\s+", quote):
        low = sent.lower()
        if tokens and not any(t[:6] in low for t in tokens):
            continue
        for m in NEGATION_CUE.finditer(sent):
            before = sent[:m.start()]
            if re.search(r"\b(to|and|so as to)\s+$", before, re.I):   # purpose: 'titrated to avoid symptoms'
                continue
            if not CONDITIONAL.search(before):
                return True
    return False


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
        gate, line = gate_line_of_therapy(item.predicate, item.line_of_therapy, item.verbatim_quote)
        if gate == "drop":
            stats["self_contradictory"] = stats.get("self_contradictory", 0) + 1
            continue
        if negated_in_quote(item.predicate, item.object_name, item.verbatim_quote):
            stats["negated_dropped"] = stats.get("negated_dropped", 0) + 1
            continue
        if gate != "keep":
            stats[f"line_{gate}d" if gate == "clear" else "first_line_downgraded"] = \
                stats.get(f"line_{gate}d" if gate == "clear" else "first_line_downgraded", 0) + 1
        verified = quote_in_source(item.verbatim_quote, source_norm) if source_norm is not None else False
        stats["verified" if verified else "unverified"] = stats.get("verified" if verified else "unverified", 0) + 1
        sub_id, sub_label, sub_type = registry.resolve(item.subject_name, item.subject_type, book_id)
        obj_id, obj_label, obj_type = registry.resolve(item.object_name, item.object_type, book_id)

        # Generate unique fact ID
        hash_suffix = hashlib.md5(f"{section_id}:{sub_id}:{item.predicate.value}:{obj_id}".encode()).hexdigest()[:8]
        fact_id = f"ont-{book_id}-{hash_suffix}"

        facets = ClinicalFacet(
            line_of_therapy=line,
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
