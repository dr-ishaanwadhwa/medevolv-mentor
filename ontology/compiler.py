"""Ontology Compiler & Query Engine.

Compiles certified ProvenancedOntologyFacts into unified JSONL storage and provides
high-performance query helpers for clinical decision support, multi-hop reasoning,
and the interactive sequential drill-down visualizer.
"""
from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any

import networkx as nx
from ontology.schema import (
    ClinicalRelation,
    ContraindicationSeverity,
    EntityType,
    LineOfTherapy,
    ProvenancedOntologyFact,
)

logger = logging.getLogger(__name__)

ONTOLOGY_DATA_DIR = Path("data/ontology")
ONTOLOGY_FILE = ONTOLOGY_DATA_DIR / "clinical_ontology.jsonl"


def save_compiled_facts(facts: list[ProvenancedOntologyFact], path: Path = ONTOLOGY_FILE) -> None:
    """Save reconciled facts to JSONL file, merging duplicates."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Deduplicate by (subject_id, predicate, object_id) while preserving highest confidence
    dedup: dict[tuple[str, str, str], ProvenancedOntologyFact] = {}
    for f in facts:
        key = (f.subject_id, f.predicate.value, f.object_id)
        if key not in dedup or f.confidence > dedup[key].confidence:
            dedup[key] = f

    lines = [f.model_dump_json() for f in dedup.values()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    load_compiled_facts.cache_clear()
    logger.info("Compiled %d unique clinical ontology facts to %s", len(lines), path)


@functools.cache
def load_compiled_facts(path: Path = ONTOLOGY_FILE) -> list[ProvenancedOntologyFact]:
    """Load compiled facts from JSONL file."""
    if not path.exists():
        return []
    facts: list[ProvenancedOntologyFact] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                facts.append(ProvenancedOntologyFact.model_validate_json(line))
            except Exception as e:
                logger.debug("Skipping unparseable fact line: %s", e)
    return facts


def build_ontology_graph(facts: list[ProvenancedOntologyFact] | None = None) -> nx.MultiDiGraph:
    """Build a NetworkX MultiDiGraph from certified ontology facts."""
    if facts is None:
        facts = load_compiled_facts()

    g = nx.MultiDiGraph()
    for f in facts:
        # Add subject node
        if f.subject_id not in g:
            g.add_node(
                f.subject_id,
                label=f.subject_label,
                type=f.subject_type.value,
                sources={f.provenance.book_id},
            )
        else:
            g.nodes[f.subject_id].setdefault("sources", set()).add(f.provenance.book_id)

        # Add object node
        if f.object_id not in g:
            g.add_node(
                f.object_id,
                label=f.object_label,
                type=f.object_type.value,
                sources={f.provenance.book_id},
            )
        else:
            g.nodes[f.object_id].setdefault("sources", set()).add(f.provenance.book_id)

        # Add directed edge with rich clinical attributes
        g.add_edge(
            f.subject_id,
            f.object_id,
            key=f.predicate.value,
            id=f.id,
            predicate=f.predicate.value,
            line_of_therapy=f.clinical_facets.line_of_therapy.value if f.clinical_facets.line_of_therapy else None,
            contraindication_severity=f.clinical_facets.contraindication_severity.value if f.clinical_facets.contraindication_severity else None,
            timing_phase=f.clinical_facets.timing_phase,
            rationale=f.clinical_facets.rationale,
            book_id=f.provenance.book_id,
            book_title=f.provenance.book_title,
            chapter=f.provenance.chapter,
            section_id=f.provenance.section_id,
            pages=f.provenance.pages,
            verbatim_quote=f.provenance.verbatim_quote,
            nl_fact=f.nl_fact,
            confidence=f.confidence,
        )
    return g


# ---------- High-Level Clinical Query Helpers ----------

def get_clinical_treatment_profile(condition_id: str, g: nx.MultiDiGraph | None = None) -> dict[str, list[dict[str, Any]]]:
    """Retrieve structured treatment hierarchy and contraindications for a condition."""
    if g is None:
        g = build_ontology_graph()

    profile: dict[str, list[dict[str, Any]]] = {
        "first_line": [],
        "second_line": [],
        "refractory": [],
        "supportive": [],
        "contraindications": [],
    }

    if condition_id not in g:
        return profile

    for _, target, edge in g.out_edges(condition_id, data=True):
        pred = edge.get("predicate")
        lot = edge.get("line_of_therapy")
        label = g.nodes[target].get("label", target)

        entry = {
            "id": target,
            "name": label,
            "book": edge.get("book_title", ""),
            "chapter": edge.get("chapter", ""),
            "pages": edge.get("pages", []),
            "quote": edge.get("verbatim_quote", ""),
            "rationale": edge.get("rationale", ""),
            "nl_fact": edge.get("nl_fact", ""),
        }

        if pred == ClinicalRelation.TREATED_BY.value:
            if lot == LineOfTherapy.FIRST_LINE.value:
                profile["first_line"].append(entry)
            elif lot == LineOfTherapy.SECOND_LINE.value:
                profile["second_line"].append(entry)
            elif lot == LineOfTherapy.REFRACTORY.value:
                profile["refractory"].append(entry)
            elif lot == LineOfTherapy.SUPPORTIVE.value:
                profile["supportive"].append(entry)
            else:
                profile["first_line"].append(entry)

        elif pred == ClinicalRelation.CONTRAINDICATES.value:
            entry["severity"] = edge.get("contraindication_severity", "STRICT")
            profile["contraindications"].append(entry)

    return profile


def get_clinical_diagnostics(condition_id: str, g: nx.MultiDiGraph | None = None) -> list[dict[str, Any]]:
    """Retrieve confirmatory investigations and diagnostic modalities for a condition."""
    if g is None:
        g = build_ontology_graph()

    results: list[dict[str, Any]] = []
    if condition_id not in g:
        return results

    for _, target, edge in g.out_edges(condition_id, data=True):
        if edge.get("predicate") == ClinicalRelation.CONFIRMED_BY.value:
            results.append({
                "id": target,
                "name": g.nodes[target].get("label", target),
                "timing_phase": edge.get("timing_phase", ""),
                "book": edge.get("book_title", ""),
                "quote": edge.get("verbatim_quote", ""),
                "nl_fact": edge.get("nl_fact", ""),
            })
    return results


def get_clinical_etiology_and_mechanism(condition_id: str, g: nx.MultiDiGraph | None = None) -> dict[str, list[dict[str, Any]]]:
    """Retrieve etiological agents and pathophysiological mechanisms for a condition."""
    if g is None:
        g = build_ontology_graph()

    out: dict[str, list[dict[str, Any]]] = {
        "etiology": [],
        "mechanisms": [],
        "stages": [],
    }
    if condition_id not in g:
        return out

    for _, target, edge in g.out_edges(condition_id, data=True):
        pred = edge.get("predicate")
        label = g.nodes[target].get("label", target)
        entry = {
            "id": target,
            "name": label,
            "quote": edge.get("verbatim_quote", ""),
            "nl_fact": edge.get("nl_fact", ""),
        }
        if pred == ClinicalRelation.CAUSED_BY.value:
            out["etiology"].append(entry)
        elif pred == ClinicalRelation.DISRUPTS_PATHWAY.value:
            out["mechanisms"].append(entry)
        elif pred == ClinicalRelation.HAS_CLINICAL_STAGE.value:
            out["stages"].append(entry)

    return out
