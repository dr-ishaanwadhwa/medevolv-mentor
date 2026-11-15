"""Links from ontology anatomy to the 3D atlas (data/graph/atlas_crosswalk.jsonl), plus the atlas deep-link URL.

    atlas_link("Middle meningeal artery")      -> "https://atlas.medevolv.in/?select=FMA...", or None
    structures_for("Aortic dissection")        -> [{"label", "atlas_name", "url"}, ...]   (via INVOLVES_STRUCTURE)

The atlas is human-atlas (MIT) showing BodyParts3D (CC BY 4.0). A link only says "this ontology structure is drawn
there as this named structure"; structures_for goes condition -> certified INVOLVES_STRUCTURE fact -> link. The
INVOLVES_STRUCTURE fact is the only claim; the link is navigation and never adds a clinical statement.

Everything returns None / [] when ATLAS_URL is unset or the crosswalk file is missing, so the app hides the feature.
The file is built offline by scripts/build_atlas_crosswalk.py; one JSON per line:
    {"label", "key", "atlas_id", "atlas_name", "method", "score", ["atlas_ids"], ["by_side"]}
It holds every atlas name (so a label that merely spells an atlas name differently still links), curated synonyms,
and the LLM-checked matches. `variants(label)` (plural, 'the', 'X of Y' order, trailing 'muscle'/'bone', hyphens) is
shared by the build and by the lookup here. A structure drawn only as a left and a right piece (lungs, kidneys'
muscles...) links to both: `atlas_ids` is a list and the atlas selects them together.

Systemic-condition guard (Stage 0 of docs/atlas_coverage_plan.md). A 3D link for a CONDITION is shown only when the
condition is local: one anatomical site, where highlighting the structure teaches where the lesion is. Every condition
that had a linked structure was classified once (scripts/build_atlas_crosswalk.py --guard, DeepSeek at temperature 0,
cached) into data/graph/atlas_condition_guard.jsonl, one JSON per line {"condition", "label", "reason"}:
    local            one site; the link is shown
    systemic         whole-body or whole-system disease (cystic fibrosis, sepsis)
    multi_site       several unrelated sites, or no single site
    misleading_site  the linked structure is not the defining site (tuberculosis -> lumbar vertebra, pneumonia, cirrhosis)
`structures_for(condition)` returns [] unless the label is `local`; a condition missing from an existing guard file is
unclassified and hidden. The curated overrides in CURATED_NON_LOCAL always win over the file, and they are the only
rule when the guard file is missing (fail safe: the known misleading links stay hidden, the rest behave as before).
Structure -> atlas links (`atlas_link`, `for_section`: AnatomicalStructure pages) are not affected by the guard.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path
from urllib.parse import quote

from ontology.merge import merge_key
from rag import config, ontology_facts as onto

PATH = Path("data/graph/atlas_crosswalk.jsonl")
GUARD_PATH = Path("data/graph/atlas_condition_guard.jsonl")
LOCAL = "local"
# Hand-curated from the coverage plan (section 5): conditions whose 3D link misleads. Always override the guard file.
CURATED_NON_LOCAL = {
    "tuberculosis": "misleading_site", "peripheral vascular disease": "misleading_site",
    "osteomyelitis": "misleading_site", "pneumonia": "misleading_site", "stress fracture": "misleading_site",
    "muscle tear": "misleading_site", "ovarian cancer": "misleading_site", "hepatic cirrhosis": "misleading_site",
    "temporal arteritis": "misleading_site", "tumor embolus": "misleading_site",
    "intermittent claudication": "misleading_site", "metastatic lesions in the liver": "misleading_site",
    "cystic fibrosis": "systemic",
    # moved here by the Stage 0 audit (reports/atlas_stage0_audit.md): the model said local, the highlight is not the site
    "accessory nerve injury": "misleading_site", "dorsal scapular nerve injury": "misleading_site",   # shows the
    "high median nerve palsy": "misleading_site",         # denervated muscle; the lesion is the nerve, which has no model
    "pelvic kidney": "misleading_site",                   # highlights the kidney where it normally lies, not where it sits
    # independent re-audit: signs shown on the denervated / weak target muscle, not the lesion (usually a nerve)
    "trendelenburg's sign": "misleading_site", "diaphragmatic paralysis": "misleading_site",
    "complete ptosis": "misleading_site",
}
# Lesion-only restriction: the facts also name neighbours that are complications, landmarks or compressed structures
# (optic chiasm for a pituitary tumour, branch arteries for a dissection). Show only the lesion's own structure.
LESION_ONLY = {
    "pituitary macroadenoma": ("pituitary gland",),
    "aortic dissection": ("aorta",),
    "dissecting thoracic aortic aneurysm": ("aorta",),
}
SIDES = ("left", "right")
_TRAIL = ("muscle", "bone")          # the atlas writes 'scaphoid', 'serratus anterior'; textbooks add the category word
# Same condition written two ways; used only to find INVOLVES_STRUCTURE facts, never to add one.
_COND_WORDS = {"epidural": "extradural"}
_COND_SAME = {"extradural hemorrhage": "extradural hematoma"}


def name_key(label: str) -> str:
    """merge_key plus dropping 'the': 'Surgical neck of the humerus' == 'surgical neck of humerus'."""
    return " ".join(w for w in merge_key(label).split() if w != "the")


def side_of(label: str) -> str | None:
    return next((w for w in merge_key(label).split() if w in SIDES), None)


def _singular(w: str) -> list[str]:
    """Other singular forms merge_key misses ('kidneys', 'vertebrae', 'bronchi')."""
    out = []
    if len(w) > 4 and w.endswith("ae"):
        out.append(w[:-1])
    if len(w) > 4 and w.endswith("i"):
        out.append(w[:-1] + "us")
    if len(w) > 4 and w.endswith("ys"):
        out.append(w[:-1])
    return out


def variants(label: str) -> list[str]:
    """Lookup keys for a label, most literal first: the key, without a trailing 'muscle'/'bone', 'X of Y' <-> 'Y X',
    the key without spaces ('~sacroiliacjoint' for 'Sacro-iliac joint'), and the key without left/right."""
    k = name_key(label)
    ws = k.split()
    out = [k]
    last = ws[-1] if ws else ""
    for sing in _singular(last):
        out.append(" ".join(ws[:-1] + [sing]))
    if len(ws) > 1 and ws[-1] in _TRAIL:
        out.append(" ".join(ws[:-1]))
    for base in list(out):
        bw = base.split()
        if "of" in bw[1:-1]:
            i = bw.index("of")
            out.append(" ".join(bw[i + 1:] + bw[:i]))
        elif 2 <= len(bw) <= 3:
            out.append(bw[-1] + " of " + " ".join(bw[:-1]))
    out.append("~" + k.replace(" ", ""))
    nos = [w for w in ws if w not in SIDES]
    if nos != ws and nos:
        out.append(" ".join(nos))
    return list(dict.fromkeys(out))


def resolve(label: str, table: dict[str, dict]) -> dict | None:
    """Crosswalk record for a label under `table` (key -> record), or None. A label that names a side takes that
    side of a left/right pair, never both."""
    side = side_of(label)
    for k in variants(label):
        r = table.get(k)
        if not r:
            continue
        if side and r.get("by_side"):
            one = r["by_side"].get(side)
            if not one:
                continue
            return {**r, "atlas_id": one, "atlas_ids": [one]}
        return r
    return None


@functools.cache
def links() -> dict[str, dict]:
    """name_key of a label or atlas name -> crosswalk record (plus '~nospace' keys for hyphen/space variants)."""
    if not PATH.exists():
        return {}
    out = {}
    for line in PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["key"]] = r
    for k, r in list(out.items()):
        out.setdefault("~" + k.replace(" ", ""), r)
    return out


def enabled() -> bool:
    return bool(config.ATLAS_URL) and bool(links())


def url_for(atlas_id: str | list[str]) -> str:
    """Deep link; several ids (a left/right pair) are comma separated and selected together."""
    ids = atlas_id if isinstance(atlas_id, list) else [atlas_id]
    return f"{config.ATLAS_URL.rstrip('/')}/?select={quote(','.join(ids), safe=',')}"


def record_url(r: dict) -> str:
    return url_for(r.get("atlas_ids") or r["atlas_id"])


def atlas_record(label: str) -> dict | None:
    return resolve(label, links())


def atlas_link(label: str) -> str | None:
    """Deep link into the atlas for an ontology structure label, or None (unlinked, or ATLAS_URL unset)."""
    if not config.ATLAS_URL:
        return None
    r = atlas_record(label)
    return record_url(r) if r else None


def cond_key(label: str) -> str:
    """name_key with 'epidural' = 'extradural' and 'extradural hemorrhage' = 'extradural hematoma'."""
    k = " ".join(_COND_WORDS.get(w, w) for w in name_key(label).split())
    return _COND_SAME.get(k, k)


def for_section(meta: dict) -> dict | None:
    """Link for a textbook passage's own topic: its heading, section title, then the two headings above it (so a
    Gray's section 'Heart' or 'Liver' links; 'Vessels' alone does not). {"label", "atlas_name", "url"} or None."""
    if not config.ATLAS_URL:
        return None
    path = [p for p in (meta.get("section_path") or "").split(" › ") if p][2:]       # drop book and chapter
    for name in [meta.get("heading"), meta.get("section_title"), *reversed(path[-3:])]:
        r = atlas_record(name) if name else None
        if r:
            return {"label": name, "atlas_name": r["atlas_name"], "url": record_url(r)}
    return None


@functools.cache
def _involves() -> dict[str, tuple[str, ...]]:
    out: dict[str, list[str]] = {}
    for f in onto.facts():                        # certified facts only
        if f["predicate"] == "INVOLVES_STRUCTURE":
            lst = out.setdefault(cond_key(f["subject_label"]), [])
            if f["object_label"] not in lst:
                lst.append(f["object_label"])
    return {k: tuple(v) for k, v in out.items()}


@functools.cache
def guard() -> dict[str, str] | None:
    """cond_key -> label from the guard file, or None when the file is missing (curated overrides only then)."""
    if not GUARD_PATH.exists():
        return None
    out = {}
    for line in GUARD_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[cond_key(r["condition"])] = r["label"]
    return out


def guard_label(condition: str) -> str:
    """local / systemic / multi_site / misleading_site / unclassified for a condition (curated overrides first)."""
    k = cond_key(condition)
    curated = {cond_key(c): v for c, v in CURATED_NON_LOCAL.items()}
    if k in curated:
        return curated[k]
    g = guard()
    return LOCAL if g is None else g.get(k, "unclassified")


def structures_for(condition_label: str) -> list[dict]:
    """Atlas-linked structures a condition INVOLVES (certified facts), in fact order, for LOCAL conditions only.
    [] when none, unconfigured, or the guard says the condition is systemic / multi-site / has a misleading site."""
    if not config.ATLAS_URL or guard_label(condition_label) != LOCAL:
        return []
    out, seen = [], set()
    only = {cond_key(x) for x in LESION_ONLY.get(cond_key(condition_label), ())}
    for s in _involves().get(cond_key(condition_label), ()):
        if only and cond_key(s) not in only:
            continue
        r = atlas_record(s)
        if r and record_url(r) not in seen:       # 'Lung' and 'Lungs' are one link
            seen.add(record_url(r))
            out.append({"label": s, "atlas_name": r["atlas_name"], "url": record_url(r)})
    return out
