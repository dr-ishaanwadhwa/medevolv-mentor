"""Deterministic Normalization and Canonical URI Minting.

Adapts deterministic naming patterns from NVIDIA Auto-Ontology to standardize
medical terms, strip clinical qualifiers, and mint stable ontological URIs.
"""
from __future__ import annotations

import re
from ontology.schema import EntityType

# SNOMED / clinical qualifiers in parentheses
_QUALIFIERS = re.compile(
    r"\s*\((?:condition|symptom|finding|disorder|qualifier value|procedure|substance|organism|regime/therapy|observable entity)\)",
    re.IGNORECASE,
)

# Common pharmaceutical salt suffixes to normalize to active moiety
_SALT_SUFFIXES = re.compile(
    r"\b(hydrochloride|hcl|sodium|potassium|maleate|sulfate|sulphate|succinate|tartrate|fumarate|acetate|phosphate|gluconate|citrate|hydrate|monohydrate|dihydrate)\b",
    re.IGNORECASE,
)


def clean_medical_text(text: str) -> str:
    """Strip brackets, qualifiers, extra spaces, and trailing punctuation."""
    if not text:
        return ""
    cleaned = _QUALIFIERS.sub("", text)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"[:;,]+$", "", cleaned)
    return " ".join(cleaned.split()).strip()


def normalize_drug_name(drug: str) -> str:
    """Normalize drug name to active INN moiety (e.g. 'Metformin Hydrochloride' -> 'Metformin')."""
    base = clean_medical_text(drug)
    # Remove salt suffixes if length > 1 word
    words = base.split()
    if len(words) > 1:
        no_salt = _SALT_SUFFIXES.sub("", base)
        cleaned_no_salt = " ".join(no_salt.split()).strip()
        if len(cleaned_no_salt) >= 3:
            return cleaned_no_salt.capitalize()
    return base.capitalize() if base else ""


def slugify(text: str) -> str:
    """Generate a deterministic lowercase hyphenated slug."""
    clean = clean_medical_text(text).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean)
    return slug.strip("-")


def mint_uri(book_id: str, label: str, entity_type: EntityType | str) -> str:
    """Mint a deterministic URI under the MED:OKF namespace for concepts lacking external codes."""
    type_str = entity_type.value.lower() if isinstance(entity_type, EntityType) else str(entity_type).lower()
    slug = slugify(label)
    # The book is deliberately NOT part of the ID: the same concept from two books must be one node.
    # (book_id is kept in the signature for compatibility; provenance records the book.)
    return f"MED:OKF/{type_str}/{slug}"
