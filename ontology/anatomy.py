"""Normal-anatomy relations from Gray's Anatomy for Students (Rule 9 / Stage C of docs/headings_to_ontology_plan.md).

Seven relations between two named structures: INNERVATED_BY, SUPPLIED_BY, DRAINED_BY, BOUNDED_BY, CONTAINS,
BRANCH_OF, PART_OF. This module holds
  * the guard rules G1-G9 (docs/headings_m3_cost_review.md section 3.3), used by ontology/reconciler.py;
  * the anatomy extraction prompt;
  * the runner: heading-scoped passages -> one LLM call each (cached) -> the normal gates -> verifier -> merge.

  python -m ontology.anatomy --pilot 40 --dry-run   # passages + cost estimate
  python -m ontology.anatomy --pilot 40             # extract, reconcile, verify, re-save the ontology
  python -m ontology.anatomy                        # every targeted passage

Calls are cached in data/ontology/cache_anatomy/ (never committed; same format as ontology/gapfill.py); failed
calls are not cached, so a rerun resumes. builder --rebuild re-adds the cached facts without LLM calls.
These facts stay OUT of answers: rag/ontology_facts.py hides ANATOMY_PREDICATES from facts().
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ontology.gapfill import PRICE_IN, PRICE_OUT
from ontology.schema import ClinicalRelation as R, ExtractionItem

CACHE = Path("data/ontology/cache_anatomy")
logger = logging.getLogger("ontology.anatomy")
_lock = threading.Lock()

ANATOMY_PREDICATES = {R.INNERVATED_BY, R.SUPPLIED_BY, R.DRAINED_BY, R.BOUNDED_BY, R.CONTAINS, R.BRANCH_OF, R.PART_OF}

# ---------- kinds and guard rules ----------
KINDS = {"muscle", "nerve", "artery", "vein", "lymphatic", "bone", "ligament", "fascia", "space", "organ", "system",
         "region", "joint", "gland", "skin", "sheath"}
VESSEL_NERVE = {"artery", "vein", "nerve", "lymphatic"}
# predicate -> (allowed subject kinds, allowed object kinds); G5 and G6
KIND_RULES = {
    "INNERVATED_BY": ({"muscle", "organ", "region", "bone", "skin", "joint", "gland", "ligament"}, {"nerve"}),
    "SUPPLIED_BY": ({"muscle", "organ", "region", "bone", "joint", "gland", "nerve", "skin", "ligament"}, {"artery"}),
    "DRAINED_BY": ({"muscle", "organ", "region", "bone", "joint", "gland", "skin", "ligament"}, {"vein", "lymphatic"}),
    # organ subjects dropped after the audit: "the kidney is bounded by the diaphragm" was adjacency every time
    "BOUNDED_BY": ({"space", "region"},
                   {"muscle", "bone", "ligament", "fascia", "organ", "space", "region", "artery", "nerve", "joint"}),
    "CONTAINS": ({"space", "region", "organ", "sheath"},
                 {"muscle", "nerve", "artery", "vein", "lymphatic", "organ", "ligament", "space", "bone", "gland"}),
}
KIND_RX = [
    ("nerve", re.compile(r"\bnerves?\b|\bplexus\b|\bganglion\b|\bganglia\b|\broots?\b|\bcords?\b|\bdivisions?\b|\bramus\b|\bramis?\b", re.I)),
    ("lymphatic", re.compile(r"\blymph|thoracic duct\b", re.I)),
    ("vein", re.compile(r"\bveins?\b|\bvenous\b|\bvena cava\b|\bsinus(es)? of the dura|\bdural venous sinus", re.I)),
    ("artery", re.compile(r"\barter(y|ies|ial)\b|\baorta\b|\baortic\b|\bcoronary\b|\bcarotid\b|\btrunk\b|\barch\b", re.I)),
    ("muscle", re.compile(r"\bmuscles?\b|\bmusculus\b|\bdiaphragm\b|\bcrus\b", re.I)),
    ("bone", re.compile(r"\bbones?\b|\bvertebra|\bfemur\b|\bhumerus\b|\bsternum\b|\bribs?\b|\bsacrum\b|\bskull\b", re.I)),
    ("ligament", re.compile(r"\bligaments?\b|\bretinaculum\b|\bmembrane\b", re.I)),
    ("system", re.compile(r"\bsystem\b", re.I)),
    ("sheath", re.compile(r"\bsheath\b", re.I)),
    ("space", re.compile(r"\bcanal\b|\bspace\b|\bfossa\b|\bforamen\b|\bfissure\b|\btriangle\b|\bcavity\b|\bhiatus\b|\bring\b", re.I)),
    ("region", re.compile(r"\bregion\b|\bwall\b|\bpelvis\b|\bperineum\b|\babdomen\b|\bthorax\b|\bneck\b", re.I)),
]
_GENERIC = {"the", "of", "and", "a", "an", "left", "right", "anterior", "posterior", "superior", "inferior", "medial", "lateral"}


_KIND_WORDS = {"artery", "arteries", "vein", "veins", "nerve", "nerves", "muscle", "muscles", "bone", "ligament", "trunk",
               "branch", "branches", "plexus", "system", "canal", "space", "region", "sheath"}


def infer_kind(label: str) -> str:
    """G9 fallback only (the extractor supplies structure_kind): a fact that needed this is never certified."""
    for kind, rx in KIND_RX:
        if rx.search(label):
            return kind
    return "organ"


def _words(label: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", label.lower()) if w not in _GENERIC and len(w) > 2}


def is_segment_of(sub_label: str, obj_label: str) -> bool:
    """'Ascending aorta' is a segment of 'Aorta': every content word of the parent appears in the child's name, and the
    child adds a qualifier. 'Coronary artery' is not a segment of 'Ascending aorta'."""
    o, s = _words(obj_label), _words(sub_label)
    o_core = {re.sub(r"(ies|ery|s)$", "", w) for w in o}
    s_core = {re.sub(r"(ies|ery|s)$", "", w) for w in s}
    return bool(o_core) and o_core <= s_core and len(s_core) > len(o_core)


def check_anatomy_kinds(pred: str, s_kind: str, o_kind: str, s_label: str = "", o_label: str = "") -> tuple[str, str]:
    """('ok' | 'drop' | 'review', reason). Guard rules G1-G6.

    PART_OF   constitutive: the subject is a component or segment of the object (left ventricle of the heart, ascending
              aorta of the aorta, heart of the cardiovascular system).
    BRANCH_OF derivational: the subject vessel/nerve arises from the object (coronary arteries from the aorta). A branch
              is a different named structure that leaves the parent; it is NOT part of it.
    'review' is not certified (the fact is kept as a hidden CANDIDATE).
    """
    if not pred or not (s_kind or o_kind):
        return "drop", "missing kind"
    if pred == "BRANCH_OF":                                                   # G1
        if s_kind not in VESSEL_NERVE or o_kind not in VESSEL_NERVE:
            return "drop", "only vessels and nerves have branches (organs, muscles and systems do not branch)"
        if s_kind != o_kind:
            return "drop", f"{s_kind} cannot be a branch of {o_kind}: branches stay within one family"
        return "ok", "same-family branch"
    if pred == "PART_OF":
        if s_kind in VESSEL_NERVE and s_kind == o_kind:                       # G2
            if is_segment_of(s_label, o_label):
                return "ok", "named segment of the same vessel or nerve"
            return "drop", "same-family vessel/nerve that is not a named segment is a branch, not a part"
        if s_kind in VESSEL_NERVE and o_kind == "organ":                      # G4
            return "review", "a vessel or nerve is not part of an organ it supplies; use SUPPLIED_BY / INNERVATED_BY / CONTAINS"
        if s_kind == "system":                                                # G3
            return "drop", "a system is not part of a structure (use the reverse)"
        if o_kind == "system":
            return ("ok", "organ or vessel in its system") if s_kind in {"organ", "artery", "vein", "nerve", "lymphatic", "muscle", "bone", "ligament"} \
                else ("review", "unusual member of a system")
        return "ok", "component or segment"
    rule = KIND_RULES.get(pred)
    if rule is None:
        return "drop", "unknown predicate"
    if s_kind not in rule[0]:
        return "drop", f"{pred} subject must be one of {sorted(rule[0])}, got {s_kind}"
    if o_kind not in rule[1]:
        return "drop", f"{pred} object must be one of {sorted(rule[1])}, got {o_kind}"
    return "ok", "kind rule satisfied"


def guard_triple(pred: str, s_label: str, o_label: str, s_kind: str | None = None, o_kind: str | None = None) -> tuple[str, str]:
    """check_anatomy_kinds with kinds inferred from names when the extractor did not give them."""
    return check_anatomy_kinds(pred, s_kind or infer_kind(s_label), o_kind or infer_kind(o_label), s_label, o_label)


# G7: the verified quote must carry a cue word for its predicate
QUOTE_CUES = {
    "BRANCH_OF": r"branch|arise|arising|given off|gives? off|originat|derived|divides|divided|bifurcat|terminal|continu|"
                 r"emerg|tributar|springs|leaves|passes? from",
    "PART_OF": r"\bpart\b|segment|component|portion|section|division|subdivision|consist|compris|composed|includ|"
               r"\blobes?\b|\bchambers?\b|formed (of|by)|\bforms\b|made up",
    "INNERVATED_BY": r"innervat|nerve|supplied|supply|supplies|motor|sensory|\bsupplied",
    "SUPPLIED_BY": r"suppl|blood|arter|vascular|perfus|nourish",
    "DRAINED_BY": r"drain|vein|venous|lymph|tributar|return",
    # boundary vocabulary only: "lies behind / is covered by / is cradled between" is adjacency, not a boundary (audit, full run)
    "BOUNDED_BY": r"bound|border|roof|floor|wall|margin|limit|\bform|edge|(anterior|posterior|superior|inferior|medial|lateral)ly,? (by|is|are)",
    "CONTAINS": r"contain|pass|transmit|enclos|\blie|\blies\b|content|house|hold|within|through|carr|enter|exit|leave|"
                r"traverse|occup",
}


def quote_cue_ok(pred: str, quote: str) -> bool:
    rx = QUOTE_CUES.get(pred)
    return True if rx is None else bool(re.search(rx, quote or "", re.I))


def names_in_quote(label: str, quote: str) -> bool:
    """Some distinctive word of the label (5-letter stem) appears in the quote: a quote that never names the
    object cannot prove the relation."""
    q = (quote or "").lower()
    words = [w for w in re.findall(r"[a-z]{4,}", (label or "").lower()) if w not in _GENERIC]
    stems = [w[:5] for w in words if w not in _KIND_WORDS] or [w[:5] for w in words]
    return not stems or any(s in q for s in stems)


def gate_anatomy_item(item: ExtractionItem) -> tuple[str, str]:
    """('ok' | 'candidate' | 'drop', reason) for one extracted anatomy triple. Applied by the reconciler."""
    pred = item.predicate.value.upper()                                       # enum value is 'part_of'
    s_kind, o_kind = (item.structure_kind or "").lower(), (item.object_structure_kind or "").lower()
    from ontology.merge import merge_key
    if merge_key(item.subject_name) == merge_key(item.object_name):          # G8
        return "drop", "self-relation"
    if not quote_cue_ok(pred, item.verbatim_quote):                           # G7
        return "drop", "quote has no cue word for the predicate"
    if not names_in_quote(item.object_name, item.verbatim_quote):
        return "drop", "quote does not name the object"
    inferred = False
    if s_kind not in KINDS:                                                   # G9
        s_kind, inferred = infer_kind(item.subject_name), True
    if o_kind not in KINDS:
        o_kind, inferred = infer_kind(item.object_name), True
    verdict, why = check_anatomy_kinds(pred, s_kind, o_kind, item.subject_name, item.object_name)
    if verdict == "drop":
        return "drop", why
    if verdict == "review" or inferred:
        return "candidate", why if verdict == "review" else "kind inferred from the name (G9)"
    return "ok", why


def drop_cycles(facts):
    """G8, after the merge: PART_OF and BRANCH_OF must stay acyclic. Self-loops and every fact in a cycle are removed."""
    import networkx as nx
    out = list(facts)
    for pred in (R.PART_OF, R.BRANCH_OF):
        g = nx.DiGraph()
        g.add_edges_from((f.subject_id, f.object_id) for f in out if f.predicate == pred)
        bad = set()
        for comp in nx.strongly_connected_components(g):
            if len(comp) > 1:
                bad |= comp
        bad_edges = {(a, b) for a, b in g.edges if a == b or (a in bad and b in bad)}
        if bad_edges:
            logger.warning("%s: dropping %d fact(s) in cycles / self-loops", pred.value, len(bad_edges))
            out = [f for f in out if not (f.predicate == pred and (f.subject_id, f.object_id) in bad_edges)]
    return out


# ---------- prompt ----------
SYSTEM = """\
You extract NORMAL ANATOMY relations from a passage of an anatomy textbook (Gray's Anatomy for Students).
Each relation links two named structures that the passage states, in a sentence that names the structure.

Predicates (subject -> object):
- INNERVATED_BY: muscle/organ/region/bone/skin/joint -> the nerve that supplies it. ("The diaphragm is supplied by the phrenic nerve.")
- SUPPLIED_BY: structure -> the ARTERY that supplies it. ("The head of the femur is supplied by the obturator artery.")
- DRAINED_BY: structure -> the VEIN or LYMPHATIC vessel/node group that drains it.
- BOUNDED_BY: space/region/organ -> a structure forming its wall, roof, floor, anterior/posterior/lateral/medial boundary.
- CONTAINS: space/region/canal/sheath/organ -> a structure inside it or passing through it. ("The inguinal canal contains the spermatic cord.")
- BRANCH_OF: vessel or nerve -> the parent vessel or nerve (same family: artery of artery, vein of vein, nerve of nerve) that it arises from / is given off by / is a terminal branch of. Coronary arteries are BRANCH_OF the ascending aorta.
- PART_OF: subject is a component or SEGMENT of the object only ("Ascending aorta PART_OF Aorta", "Left ventricle PART_OF Heart", "Heart PART_OF Cardiovascular system"). Never use PART_OF for a branch (that is BRANCH_OF), never because a heading nests under another heading, and never for a vessel or nerve that supplies an organ.

Rules:
1. Only what the passage states about normal structure. Skip clinical conditions, surgical steps, imaging, embryology and function.
2. verbatim_quote: ONE sentence copied exactly from the passage (max 40 words) that names the object and states the relation. Never paraphrase.
3. Names: singular, canonical, with the side or level when the passage gives it ("Right coronary artery", "Superior mesenteric vein"). No abbreviations.
4. structure_kind for the subject and object, exactly one of: muscle, nerve, artery, vein, lymphatic, bone, ligament, fascia, space, organ, system, region, joint, gland, skin, sheath. (A plexus, cord, trunk or root of nerves is "nerve"; a canal, fossa, foramen, triangle or compartment is "space".)
5. entity types: AnatomicalStructure for everything, OrganSystem only for a whole body system (structure_kind "system").
6. Direction matters: the subject is the structure BEING supplied/drained/bounded/contained-in/branching. "The femoral artery gives off the deep femoral artery" -> Deep femoral artery BRANCH_OF Femoral artery.
7. At most 20 triples. If the passage states none, return {"triples": []}.

Reply as JSON only:
{"triples": [{"subject_name": "...", "subject_type": "AnatomicalStructure", "structure_kind": "muscle",
 "predicate": "INNERVATED_BY", "object_name": "...", "object_type": "AnatomicalStructure", "object_structure_kind": "nerve",
 "spinal_levels": null, "verbatim_quote": "...", "confidence": 0.95, "nl_fact": "The diaphragm is innervated by the phrenic nerve."}]}
"""
PART_ONLY = """

THIS CALL: extract ONLY PART_OF relations (component or segment of a structure; organ of a body system), at most 10.
Use the predicate value "part_of" exactly. Skip branches, supply, drainage, boundaries and contents."""
PART_CUE = re.compile(r"\bpart\b|segment|component|portion|\bforms?\b|consist|compris|composed|divided into|"
                      r"subdivi|\blobes?\b|chambers?", re.I)
PROMPT_VERSION = "v1"   # extraction prompt version (cache key); the G7 cue table below is applied at reconcile time
PILOT_PRIORITY = ("diaphragm", "inguinal canal", "femoral sheath", "carotid sheath", "head of femur", "femur",
                  "rectal", "superior orbital fissure", "ureter", "coronary", "heart")


# ---------- passages ----------
def _plan():
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import plan_anatomy_relations as plan
    return plan


def targets() -> list[dict]:
    """The Stage C target passages of scripts/plan_anatomy_relations.py (heading-scoped, a relation cue present), with text."""
    return [p for p in _plan().passages(keep_text=True) if p["cues"]]


def pilot_subset(ts: list[dict], n: int) -> list[dict]:
    """n passages: the cost review's named structures first (diaphragm, inguinal canal, ...), then an even stride."""
    chosen: list[dict] = []
    seen: set[int] = set()
    for kw in PILOT_PRIORITY:
        for i, p in enumerate(ts):
            if i not in seen and kw in " ".join(p["heading_path"]).lower() and len(chosen) < n // 2:
                chosen.append(p)
                seen.add(i)
                break
    step = max(1, len(ts) // n)
    for i in range(0, len(ts), step):
        if len(chosen) >= n:
            break
        if i not in seen:
            chosen.append(ts[i])
            seen.add(i)
    return chosen


def _key(path: str, passage: str, part: bool = False) -> Path:
    return CACHE / (hashlib.md5(f"{PROMPT_VERSION}{'-part' if part else ''}|{path}|{passage}".encode()).hexdigest() + ".json")


def _user(p: dict) -> str:
    return (f"Textbook: Gray's Anatomy for Students\nRegion: {p['region']}\nSection: {' > '.join(p['heading_path'])}\n\n"
            f'Passage:\n"""\n{p["text"]}\n"""\n\nExtract the anatomy relations. Reply in valid JSON.')


def _extract(p: dict, spend: dict, part: bool = False) -> None:
    from rag.backends import chat
    cache = _key(p["path"], p["text"], part)
    if cache.exists():
        return
    user = _user(p)
    system = SYSTEM + PART_ONLY if part else SYSTEM
    try:
        raw = chat(system, user, temperature=0.0, max_tokens=4000, json_mode=True, purpose="anatomy relations")
        triples = []
        for item in json.loads(raw).get("triples", []):
            try:
                triples.append(ExtractionItem(**item).model_dump(mode="json"))
            except Exception:
                pass
    except Exception as e:                         # not cached: a rerun retries it
        logger.warning("anatomy failed for %s: %s", Path(p["path"]).name, e)
        with _lock:
            spend["failed"] += 1
        return
    with _lock:
        spend["in"] += (len(system) + len(user)) // 4
        spend["out"] += len(raw) // 4
        spend["calls"] += 1
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"condition": None, "section": p["path"], "passage": p["text"], "triples": triples}),
                     encoding="utf-8")


def estimate(ps: list[dict], part: bool = False) -> dict:
    tin = sum((len(SYSTEM) + (len(PART_ONLY) if part else 0) + len(_user(p))) // 4 for p in ps)
    tout = 700 * len(ps)
    return {"calls": len(ps), "tokens_in": tin, "tokens_out_guess": tout,
            "usd": round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 3)}


def build(stats: dict | None = None):
    """Facts from the cache (no LLM): every cached anatomy call through the normal gates."""
    from ontology.gapfill import reconcile_cached
    return reconcile_cached(stats if stats is not None else {}, CACHE)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", type=int, help="only this many passages (the named structures + an even stride)")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, default=2.0, help="refuse to start when the estimate for uncached calls exceeds this")
    ap.add_argument("--part-of", action="store_true", help="second pass: PART_OF only, on passages with a part/segment cue")
    ap.add_argument("--no-verify", action="store_true")
    a = ap.parse_args()
    ts = targets()
    js = pilot_subset(ts, a.pilot) if a.pilot else ts
    if a.part_of:
        js = [p for p in js if PART_CUE.search(p["text"])]
    est = estimate([p for p in js if not _key(p["path"], p["text"], a.part_of).exists()], a.part_of)
    print(json.dumps({"targets": len(ts), "passages": len(js), "to_run": est}))
    if a.dry_run:
        return
    if est["usd"] > a.max_usd:
        raise SystemExit(f"estimated ${est['usd']} exceeds --max-usd {a.max_usd}; not running")
    spend = {"in": 0, "out": 0, "calls": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(lambda p: _extract(p, spend, a.part_of), js))
    spend["usd"] = round(spend["in"] / 1e6 * PRICE_IN + spend["out"] / 1e6 * PRICE_OUT, 3)
    from ontology.compiler import load_compiled_facts, save_compiled_facts
    stats: dict = {}
    new = build(stats)
    base = [f for f in load_compiled_facts() if f.predicate not in ANATOMY_PREDICATES]
    save_compiled_facts(base + new)
    print(json.dumps({"spend": spend, "reconcile": stats, "anatomy_facts_before_verifier": len(new)}))
    if not a.no_verify:
        from ontology import verifier
        print(json.dumps({"verifier": verifier.run()}))


if __name__ == "__main__":
    main()
