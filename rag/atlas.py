"""Links from ontology anatomy to the 3D atlas (data/graph/atlas_crosswalk.jsonl), plus the atlas deep-link URL.

    atlas_link("Middle meningeal artery")      -> "https://atlas.medevolv.in/?select=FMA...", or None
    structures_for("Aortic dissection")        -> [{"label", "atlas_name", "url"}, ...]   (via INVOLVES_STRUCTURE)

The atlas is human-atlas (MIT) showing BodyParts3D (CC BY 4.0). A link only says "this ontology structure is drawn
there as this named structure"; structures_for goes condition -> certified INVOLVES_STRUCTURE fact -> link. The
INVOLVES_STRUCTURE fact is the only claim; the link is navigation and never adds a clinical statement.

Everything returns None / [] when ATLAS_URL is unset or the crosswalk file is missing, so the app hides the feature.
The file is built offline by scripts/build_atlas_crosswalk.py; one JSON per line:
    {"label", "key", "atlas_id", "atlas_name", "method": "exact" | "embedding+llm", "score"}
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from urllib.parse import quote

from ontology.merge import merge_key
from rag import config, ontology_facts as onto

PATH = Path("data/graph/atlas_crosswalk.jsonl")


def name_key(label: str) -> str:
    """merge_key plus dropping 'the': 'Surgical neck of the humerus' == 'surgical neck of humerus'."""
    return " ".join(w for w in merge_key(label).split() if w != "the")


@functools.cache
def links() -> dict[str, dict]:
    """name_key of the ontology label -> crosswalk record."""
    if not PATH.exists():
        return {}
    out = {}
    for line in PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["key"]] = r
    return out


def enabled() -> bool:
    return bool(config.ATLAS_URL) and bool(links())


def url_for(atlas_id: str) -> str:
    return f"{config.ATLAS_URL.rstrip('/')}/?select={quote(atlas_id)}"


def atlas_record(label: str) -> dict | None:
    return links().get(name_key(label))


def atlas_link(label: str) -> str | None:
    """Deep link into the atlas for an ontology structure label, or None (unlinked, or ATLAS_URL unset)."""
    if not config.ATLAS_URL:
        return None
    r = atlas_record(label)
    return url_for(r["atlas_id"]) if r else None


@functools.cache
def _involves() -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for f in onto.facts():                        # certified facts only
        if f["predicate"] == "INVOLVES_STRUCTURE":
            out.setdefault(f["subject_label"], [])
            if f["object_label"] not in out[f["subject_label"]]:
                out[f["subject_label"]].append(f["object_label"])
    return {k: tuple(v) for k, v in out.items()}


def structures_for(condition_label: str) -> list[dict]:
    """Atlas-linked structures a condition INVOLVES (certified facts), in fact order. [] when none or unconfigured."""
    if not config.ATLAS_URL:
        return []
    out = []
    for s in _involves().get(condition_label, ()):
        r = atlas_record(s)
        if r:
            out.append({"label": s, "atlas_name": r["atlas_name"], "url": url_for(r["atlas_id"])})
    return out
