"""Crosswalk between the certified ontology and the BODHI graph (data/graph/crosswalk.jsonl).

    bodhi_for("Pulmonary tuberculosis")        -> [{"bodhi_id", "bodhi_name", "relation", "tier", ...}]
    ontology_for("Migraine")                    -> same records seen from the BODHI side (id, or name)
    bodhi_for(label, relations=("exact", "broader", "narrower", "related"))

Relation is read as "the BODHI node relative to the ontology entity":
    exact    same clinical concept (same specificity)
    broader  the BODHI node is more general  (ontology 'Acute asthma'  -> BODHI 'Asthma')
    narrower the BODHI node is more specific (ontology 'Asthma'        -> BODHI 'Asthma in pregnancy')
    related  navigational neighbour, incl. every typing mismatch (an ontology phenotype <-> a BODHI condition)

Tier of a link: `exact` + `checked` is T2 DERIVED (a deterministic name/id rule, or an LLM 'exact' that an
independent curated signal also supports). Everything else is T3 INFERRED (an LLM or embedding said so).

A CROSSWALK LINK IS NEVER A CLINICAL CLAIM. It says "these two records name the same (or a nearby) thing" and is
used to navigate and to hang BODHI's symptom -> differential on certified ontology facts. Only `exact` + `checked`
links may feed ontology facts into an answer; broader/narrower/related are display-only. BODHI is CC BY-NC 4.0:
keep attribution, and never copy its text into certified facts.

Every function returns [] when data/graph/crosswalk.jsonl does not exist, so the app works without it.
"""
from __future__ import annotations

import functools
import json
import re
from pathlib import Path

from ontology.merge import merge_key

PATH = Path("data/graph/crosswalk.jsonl")
RELATIONS = ("exact", "broader", "narrower", "related")

ONT_KIND = {"PathologicalCondition": "condition", "ClinicalPhenotype": "phenotype"}
BODHI_KIND = {"Condition": "condition", "Concept": "condition", "Symptom": "phenotype"}

_TAG = re.compile(r"\s*\((disorder|finding|disease|situation|morphologic abnormality|procedure|event|"
                  r"observable entity|qualifier value|body structure|symptom|sign)\)\s*$", re.I)
_ABBREV = re.compile(r"\s*\(([A-Za-z0-9\-/]{2,8})\)\s*")          # "(TSH)", "(T2D)": an acronym, not a qualifier
_DROP = {"the", "of", "an", "in", "at"}          # NOT "a": vitamin A, hepatitis A, type A


def norm_name(label: str) -> str:
    """Normalised name: case, punctuation, plural, spelling variants, SNOMED tags and acronym parentheses removed."""
    s = _TAG.sub("", label or "")
    if re.search(r"\([A-Z0-9][A-Za-z0-9\-/]{1,7}\)", s):              # keep lower-case qualifiers like "(acute)"
        s = _ABBREV.sub(" ", s)
    return merge_key(s.replace("aemi", "emi"))


# Words that change WHICH concept is meant. Two names that differ in these are broader/narrower, never exact.
_QUALIFIERS = {"acute", "chronic", "primary", "secondary", "severe", "mild", "moderate", "massive", "benign", "malignant",
               "congenital", "acquired", "recurrent", "subclinical", "early", "late", "left", "right", "bilateral",
               "unilateral", "upper", "lower", "anterior", "posterior", "proximal", "distal", "familial", "idiopathic",
               "infantile", "neonatal", "juvenile", "adult", "pediatric", "pregnancy", "transient", "refractory",
               "complicated", "uncomplicated", "latent", "active", "mixed", "partial", "complete", "major", "minor",
               "peripheral", "central", "viral", "bacterial", "fungal", "drug", "induced", "not", "without", "with",
               "type", "stage", "grade", "history", "family", "risk", "screening", "nonspecific", "atypical"}


def qualifier_set(label: str) -> frozenset:
    """Qualifier words plus numbers/Roman-numeral-free digits in a name ('type 2', 'acute'), for the exact gate."""
    return frozenset(w for w in norm_name(label).split() if w in _QUALIFIERS or w.isdigit())


def token_key(label: str) -> str:
    """Word-order and stopword insensitive form: 'Medullary carcinoma of the thyroid' == 'Medullary thyroid carcinoma'."""
    return " ".join(sorted(w for w in norm_name(label).split() if w not in _DROP))


def kinds_compatible(ont_type: str, bodhi_type: str) -> bool:
    return ONT_KIND.get(ont_type) is not None and ONT_KIND.get(ont_type) == BODHI_KIND.get(bodhi_type)


def tier_of(relation: str, checked: bool) -> str:
    return "T2" if relation == "exact" and checked else "T3"


@functools.cache
def _records() -> tuple[dict, ...]:
    if not PATH.exists():
        return ()
    return tuple(json.loads(l) for l in PATH.read_text(encoding="utf-8").splitlines() if l.strip())


@functools.cache
def _by_label() -> dict[str, list[dict]]:
    idx: dict[str, list[dict]] = {}
    for r in _records():
        idx.setdefault(norm_name(r["ont_label"]), []).append(r)
    return idx


@functools.cache
def _by_bodhi() -> tuple[dict[str, list[dict]], dict[str, list[dict]]]:
    by_id: dict[str, list[dict]] = {}
    by_name: dict[str, list[dict]] = {}
    for r in _records():
        for bid in r.get("bodhi_ids") or [r["bodhi_id"]]:
            by_id.setdefault(bid, []).append(r)
        by_name.setdefault(norm_name(r["bodhi_name"]), []).append(r)
    return by_id, by_name


def _pick(rows: list[dict], relations) -> list[dict]:
    want = {relations} if isinstance(relations, str) else set(relations or RELATIONS)
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: -r["score"]):
        k = (r["ont_id"], r["bodhi_id"], r["relation"])
        if r["relation"] in want and k not in seen:
            seen.add(k)
            out.append(r)
    return out


def bodhi_for(ontology_label: str, relations=("exact",)) -> list[dict]:
    """BODHI nodes linked to an ontology label (all ontology entities that carry that label)."""
    return _pick(_by_label().get(norm_name(ontology_label), []), relations)


def ontology_for(bodhi_id_or_name: str, relations=("exact",)) -> list[dict]:
    """Ontology entities linked to a BODHI node, given its id (any variant id) or its name."""
    by_id, by_name = _by_bodhi()
    rows = by_id.get(bodhi_id_or_name) or by_name.get(norm_name(bodhi_id_or_name), [])
    return _pick(rows, relations)


def trusted_labels(bodhi_id_or_name: str) -> list[str]:
    """Ontology labels reachable through T2 links only: the set that may feed certified facts."""
    return sorted({r["ont_label"] for r in ontology_for(bodhi_id_or_name) if r["tier"] == "T2"})
