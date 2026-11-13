"""Dry-run plan for Stage C (Gray's anatomy relations) and Stage B (LLM typing of entity headings). Spends $0.

    .venv/bin/python scripts/plan_anatomy_relations.py [--out reports/anatomy_relations_plan.json]

What it does (no LLM call, no network, nothing under ontology/ or data/ is written):
  1. selects the target passages: heading-scoped blocks of Gray's sections (never crossing a section, so never a region),
     figure-label paragraphs and "In the clinic" boxes removed, merged/split to at most MAX_WORDS words;
     a passage is a target only when it contains at least one relation cue (supply, drainage, branch, boundary, ...);
  2. estimates tokens and DeepSeek cost with the repo's own conventions (chars // 4, prices from ontology/gapfill.py);
  3. lists the schema additions and guard rules PROPOSED for ontology/schema.py / reconciler.py (data here, not applied);
  4. estimates Stage B (batched LLM typing of the entity-class headings in data/graph/headings.jsonl).

Counts only: no textbook body text is printed or written. The guard functions at the bottom are the proposed rules;
tests/test_plan_anatomy_relations.py pins them.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SECTIONS = ROOT / "data/okf/grays/sections"
HEADINGS = ROOT / "data/graph/headings.jsonl"

MAX_WORDS = 700            # plan: "about 500 to 700 words"
MIN_WORDS = 450            # a passage keeps absorbing the next heading block of its section until it has this many words
RETRY_FACTOR = 1.15        # failed calls are retried (the repo's cache only stores successes)
FACTS_PER_KWORD = (15, 20)  # headings_to_ontology_plan.md, Rule 9 planning figure
TOK_PER_TRIPLE = 70        # one JSON triple with quote, rationale, facets (measured order of magnitude, see doc)
OUT_OVERHEAD = 30
USER_OVERHEAD_TOK = 80     # ontology/grays.py estimate(): title/book/chapter lines of the user message
CERTIFIED_RATE = 0.90      # share of raw facts that pass the gates (plan: "the file's 90% certified rate")
MAX_TRIPLES_PER_CALL = 20  # plan: output cap raised from 12 to 20

# Price assumptions, USD per million tokens (input, output).
PRICES = {
    "repo_assumed (ontology/gapfill.py, verifier.py)": (0.28, 0.42),
    "pessimistic (scripts/build_hubs.py cap)": (0.56, 1.68),
}
# rag/backends.py carries no prices (it only routes calls); the plan text allows up to $1.10/M output.
PLAN_UPPER_OUT = 1.10

CUES = {
    "INNERVATED_BY": re.compile(r"\binnervat|\bnerve supply|\bmotor (supply|innervation)|\bsensory (supply|innervation)|"
                                r"\bsupplied by the [\w\s,-]{0,40}nerve", re.I),
    "SUPPLIED_BY": re.compile(r"\bblood supply|\barterial supply|\bsupplied by\b|\bsupplies\b|\bvascular supply", re.I),
    "DRAINED_BY": re.compile(r"\bdrain(s|ed|age)?\b|\bvenous\b|\blymph(atic)?\b|\btributar", re.I),
    "BOUNDED_BY": re.compile(r"\bbound(s|ed|ary|aries)\b|\bborder(s|ed)?\b|\broof\b|\bfloor\b|\banterior wall\b|"
                             r"\bposterior wall\b|\bmedial wall\b|\blateral wall\b", re.I),
    "CONTAINS": re.compile(r"\bcontains?\b|\bpass(es)? through\b|\blies? (in|within)\b|\btransmit|\bcontents\b|\benclos", re.I),
    "BRANCH_OF": re.compile(r"\bbranch(es)? of\b|\bbranches\b|\barises? from\b|\bgives? (off|rise)\b|\boriginat|"
                            r"\bterminal branch|\bdivides? into\b", re.I),
}
FIGURE_LABEL_MAX_WORDS = 6


# ---------- passage selection ----------
def parse_section(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    head, _, body = text.removeprefix("---\n").partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        k, _, v = line.partition(": ")
        meta[k] = v
    meta["section_path"] = json.loads(meta.get("section_path", "[]"))
    return meta, body


def is_figure_label(par: str) -> bool:
    """Short unpunctuated paragraph: a label lifted from a figure ("Iliacus", "Right crus"), not a sentence."""
    p = par.strip()
    return len(p.split()) <= FIGURE_LABEL_MAX_WORDS and not re.search(r"[.;:]$", p)


def blocks(body: str) -> list[tuple[str, list[str]]]:
    """[(in-body heading, [paragraphs])] split at ###/#### lines; clinic boxes are dropped (ontology/grays.py has them)."""
    out, cur_h, cur = [], "", []
    for chunk in re.split(r"(?m)^(#{1,4} .*)$", body):
        if re.match(r"#{1,4} ", chunk):
            out.append((cur_h, cur))
            cur_h, cur = chunk.lstrip("# ").strip(), []
        else:
            cur += [p for p in chunk.split("\n\n") if p.strip()]
    out.append((cur_h, cur))
    return [(h, ps) for h, ps in out if not h.lower().startswith("in the clinic")]


def passages(min_words: int = MIN_WORDS) -> list[dict]:
    """Heading-scoped passages: {section_id, region, heading_path, words, paragraphs_removed, cues}. No text is kept."""
    out = []
    for path in sorted(SECTIONS.glob("*.md")):
        meta, body = parse_section(path)
        sp = meta["section_path"]
        if "Clinical cases" in sp:
            continue                                   # already extracted whole by ontology/grays.py
        sid = json.loads(meta["id"])
        region = sp[1] if len(sp) > 1 else ""
        cur: list[tuple[str, str]] = []                 # (heading, paragraph) accumulating toward MAX_WORDS
        removed = 0

        def flush():
            nonlocal cur
            if not cur:
                return
            text = "\n\n".join(p for _, p in cur)
            hits = {name: bool(rx.search(text)) for name, rx in CUES.items()}
            out.append({"section_id": sid, "region": region, "heading_path": sp[1:] + [cur[0][0]] if cur[0][0] else sp[1:],
                        "words": len(text.split()), "chars": len(text), "cues": [k for k, v in hits.items() if v],
                        "removed_label_paragraphs": removed})
            cur = []

        for h, paras in blocks(body):
            if cur and cur[0][0] != h and sum(len(p.split()) for _, p in cur) >= min_words:
                flush()
                removed = 0
            for p in paras:
                if is_figure_label(p):
                    removed += 1
                    continue
                if cur and sum(len(q.split()) for _, q in cur) + len(p.split()) > MAX_WORDS:
                    flush()
                    removed = 0
                cur.append((h, p))
        flush()
    return out


# ---------- cost ----------
def usd(tin: float, tout: float, price: tuple[float, float]) -> float:
    return tin / 1e6 * price[0] + tout / 1e6 * price[1]


ANATOMY_ADDENDUM = """

### Anatomy mode (PROPOSED text, used here only to size the prompt)
This passage is normal anatomy from an anatomy textbook. Extract relations between named structures that the passage
states in one sentence that names both: INNERVATED_BY, SUPPLIED_BY, DRAINED_BY, BOUNDED_BY, CONTAINS, BRANCH_OF, PART_OF.
Give structure_kind for every subject and object (muscle, nerve, artery, vein, lymphatic, bone, ligament, space,
organ, system, region). Use BRANCH_OF only when the passage says the vessel or nerve arises from / is given off by /
is a branch of another; use PART_OF only for a component or segment of the same structure. At most 20 triples.
Quote the sentence verbatim. Skip left/right duplicates by naming the side in the structure name. Skip surgical steps."""


def stage_c(ps: list[dict]) -> dict:
    from ontology.prompt import CLINICAL_SYSTEM_PROMPT       # read-only import: the existing prompt sizes the call
    sys_tok = (len(CLINICAL_SYSTEM_PROMPT) + len(ANATOMY_ADDENDUM)) // 4
    targets = [p for p in ps if p["cues"]]
    n = len(targets)
    words = sum(p["words"] for p in targets)
    tin = sum(sys_tok + p["chars"] // 4 + USER_OVERHEAD_TOK for p in targets)
    scen_out = {                                   # output tokens, three views
        "repo_guess_600_per_call": 600 * n,
        "plan_15_facts_per_kword": sum(min(MAX_TRIPLES_PER_CALL, FACTS_PER_KWORD[0] * p["words"] / 1000) * TOK_PER_TRIPLE + OUT_OVERHEAD for p in targets),
        "plan_20_facts_per_kword": sum(min(MAX_TRIPLES_PER_CALL, FACTS_PER_KWORD[1] * p["words"] / 1000) * TOK_PER_TRIPLE + OUT_OVERHEAD for p in targets),
    }
    raw_facts = {"low": sum(min(MAX_TRIPLES_PER_CALL, FACTS_PER_KWORD[0] * p["words"] / 1000) for p in targets),
                 "high": sum(min(MAX_TRIPLES_PER_CALL, FACTS_PER_KWORD[1] * p["words"] / 1000) for p in targets)}
    # verifier (ontology/verifier.py): batches of 25, system ~330 tokens, ~60 tokens per item in, ~6 out
    def verifier(facts: float) -> tuple[float, float]:
        batches = math.ceil(facts / 25)
        return batches * 330 + facts * 60, batches * 40 + facts * 6
    cost = {}
    for pname, price in PRICES.items():
        row = {}
        for sname, tout in scen_out.items():
            facts = raw_facts["high" if "20" in sname else "low"]
            vin, vout = verifier(facts)
            extract = usd(tin, tout, price)
            row[sname] = {"extract": round(extract, 3), "verify": round(usd(vin, vout, price), 3),
                          "total_with_retries": round((extract + usd(vin, vout, price)) * RETRY_FACTOR, 2)}
        cost[pname] = row
    pilot = targets[:40]
    pin = sum(sys_tok + p["chars"] // 4 + USER_OVERHEAD_TOK for p in pilot)
    pout = sum(min(MAX_TRIPLES_PER_CALL, 20 * p["words"] / 1000) * TOK_PER_TRIPLE + OUT_OVERHEAD for p in pilot)
    by_region = Counter(p["region"] for p in targets)
    cue_counts = Counter(c for p in targets for c in p["cues"])
    return {
        "sections_total": len({p["section_id"] for p in ps}),
        "sections_targeted": len({p["section_id"] for p in targets}),
        "passages_total": len(ps), "passages_targeted": n, "passages_skipped_no_cue": len(ps) - n,
        "words_targeted": words, "avg_words_per_passage": round(words / n) if n else 0,
        "figure_label_paragraphs_removed": sum(p["removed_label_paragraphs"] for p in ps),
        "system_prompt_tokens": sys_tok,
        "input_tokens": tin,
        "output_tokens_scenarios": {k: round(v) for k, v in scen_out.items()},
        "raw_facts_expected": {k: round(v) for k, v in raw_facts.items()},
        "certified_expected": {k: round(v * CERTIFIED_RATE) for k, v in raw_facts.items()},
        "passages_by_cue": dict(cue_counts), "passages_by_region": dict(by_region),
        "cost_usd": cost,
        "cost_usd_plan_upper_output_price_1.10": round((usd(tin, scen_out["plan_20_facts_per_kword"], (0.56, PLAN_UPPER_OUT))
                                                        + usd(*verifier(raw_facts["high"]), (0.56, PLAN_UPPER_OUT))) * RETRY_FACTOR, 2),
        "pilot_40_passages_usd_repo_prices": round(usd(pin, pout, PRICES["repo_assumed (ontology/gapfill.py, verifier.py)"]) * RETRY_FACTOR, 3),
        "wall_clock_minutes_at_6_workers_20s_per_call": round(n * 20 / 6 / 60),
    }


# ---------- Stage B ----------
STAGE_B_SYSTEM_TOKENS = 450      # instruction + the 4 kinds + the type list; sized to match ontology/prompt.py style
STAGE_B_BATCH = 40               # plan: 40 per call
STAGE_B_OUT_PER_HEADING = 45     # {"i":12,"kind":"entity","type":"PathologicalCondition","name":"Heart failure"}


def stage_b() -> dict:
    rows = [json.loads(l) for l in HEADINGS.read_text(encoding="utf-8").splitlines() if l.strip()] if HEADINGS.exists() else []
    ent = [r for r in rows if r.get("class") == "entity"]
    n = len(ent)
    per_item_in = [(len(r["clean"]) + len(" > ".join(r["path"][1:-1])) + len(r["book"]) + 20) // 4 for r in ent]
    calls = math.ceil(n / STAGE_B_BATCH)
    tin = calls * STAGE_B_SYSTEM_TOKENS + sum(per_item_in)
    tout = n * STAGE_B_OUT_PER_HEADING + calls * 20
    cost = {pn: round(usd(tin, tout, pr) * RETRY_FACTOR, 3) for pn, pr in PRICES.items()}
    cost["pessimistic + adjudication pass on 20% of headings"] = round(
        (usd(tin, tout, PRICES["pessimistic (scripts/build_hubs.py cap)"]) + usd(tin * 0.2, tout * 0.2, PRICES["pessimistic (scripts/build_hubs.py cap)"])) * RETRY_FACTOR, 3)
    return {"entity_headings": n, "by_book": dict(Counter(r["book"] for r in ent)), "calls": calls,
            "input_tokens": tin, "output_tokens": tout, "cost_usd": cost}


# ---------- proposed schema additions (data only; nothing here edits ontology/) ----------
PROPOSED_PREDICATES = {
    # predicate: (subject kinds, object kinds, reads as, inverse wording for concepts.INVERSE)
    "INNERVATED_BY": ({"muscle", "organ", "region", "bone", "skin", "joint", "gland"}, {"nerve"}, "is innervated by", "innervates"),
    "SUPPLIED_BY": ({"muscle", "organ", "region", "bone", "joint", "gland", "nerve", "skin"}, {"artery"}, "is supplied by", "supplies"),
    "DRAINED_BY": ({"muscle", "organ", "region", "bone", "joint", "gland", "skin"}, {"vein", "lymphatic"}, "is drained by", "drains"),
    "BOUNDED_BY": ({"space", "region", "organ"}, {"muscle", "bone", "ligament", "fascia", "organ", "space", "region", "artery", "nerve"},
                   "is bounded by", "bounds"),
    "CONTAINS": ({"space", "region", "organ", "sheath"}, {"muscle", "nerve", "artery", "vein", "lymphatic", "organ", "ligament", "space", "bone"},
                  "contains", "contained in"),
    "BRANCH_OF": ({"artery", "vein", "nerve", "lymphatic"}, {"artery", "vein", "nerve", "lymphatic"}, "is a branch of", "has branch"),
    "PART_OF": (None, None, "is a component or segment of", "has part"),     # exists in ClinicalRelation; gets guards only
}
PROPOSED_SCHEMA = {
    "ontology/schema.py: ClinicalRelation": ["INNERVATED_BY", "SUPPLIED_BY", "DRAINED_BY", "BOUNDED_BY", "CONTAINS", "BRANCH_OF"],
    "ontology/schema.py: ClinicalFacet (new optional fields)": ["structure_kind: muscle|nerve|artery|vein|lymphatic|bone|ligament|fascia|space|organ|system|region|joint|gland|skin|sheath",
                                                                "object_structure_kind: same values (kind of the object, so a nerve-object rule needs no new EntityType)",
                                                                "spinal_levels: str, e.g. C3-C5 (optional)"],
    "ontology/reconciler.py: TYPE_RULES": ["each new predicate: (AnatomicalStructure, AnatomicalStructure), one direction",
                                           "PART_OF: (AnatomicalStructure | OrganSystem, AnatomicalStructure | OrganSystem)"],
    "ontology/reconciler.py: new gate": ["check_anatomy_kinds(pred, subject_kind, object_kind, subject_label, object_label) -> ok|drop|review (this file, below)",
                                         "quote cue gate: BRANCH_OF needs an arises/branch/given-off cue, PART_OF a part/segment/component cue"],
    "ontology/verifier.py: SYSTEM": ["one line per new predicate, e.g. BRANCH_OF = SUBJECT vessel/nerve arises from or is a branch of OBJECT"],
    "rag/concepts.py: INVERSE": {p: v[3] for p, v in PROPOSED_PREDICATES.items()},
    "ontology/prompt.py or a new ontology/anatomy.py": ["ANATOMY_ADDENDUM (normal anatomy only; the mirror of ontology/grays.py ADDENDUM)"],
    "eval/": ["gold_triples for the 14-question smoke set (about 40 triples by hand) and gold_sections"],
}

# ---------- guard rules (PROPOSED reconciler gate) ----------
VESSEL_NERVE = {"artery", "vein", "nerve", "lymphatic"}
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


def infer_kind(label: str) -> str:
    """Fallback only; the extractor is asked for structure_kind. Order matters: nerve before artery ('nerve to ...')."""
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
    """('ok' | 'drop' | 'review', reason). review = send to a human/LLM adjudication queue with a suggested predicate.

    PART_OF   constitutive: the subject is a component or segment of the object and is not a distinct vessel/nerve in its
              own right (left ventricle of the heart, ascending aorta of the aorta, heart of the cardiovascular system).
    BRANCH_OF derivational: the subject vessel/nerve arises from the object (coronary arteries from the aorta, ulnar nerve
              from the medial cord). A branch is a different named structure that leaves the parent; it is NOT part of it.
    """
    if s_kind == o_kind == "" or not pred:
        return "drop", "missing kind"
    if pred == "BRANCH_OF":
        if s_kind not in VESSEL_NERVE or o_kind not in VESSEL_NERVE:
            return "drop", "only vessels and nerves have branches (organs, muscles and systems do not branch)"
        if s_kind != o_kind:
            return "drop", f"{s_kind} cannot be a branch of {o_kind}: branches stay within one family (artery-artery, vein-vein, nerve-nerve)"
        return "ok", "same-family branch"
    if pred == "PART_OF":
        if s_kind in VESSEL_NERVE and o_kind in VESSEL_NERVE and s_kind == o_kind:
            if is_segment_of(s_label, o_label):
                return "ok", "named segment of the same vessel or nerve"
            return "drop", "same-family vessel/nerve that is not a named segment is a branch, not a part: BRANCH_OF if the quote says it arises from the parent"
        if s_kind in VESSEL_NERVE and o_kind in {"organ"}:
            return "review", "a vessel or nerve is not part of an organ it supplies; use SUPPLIED_BY / INNERVATED_BY / CONTAINS"
        if o_kind == "system":
            return ("ok", "organ or vessel in its system") if s_kind in {"organ", "artery", "vein", "nerve", "lymphatic", "muscle", "bone", "ligament"} \
                else ("review", "unusual member of a system")
        if s_kind == "system":
            return "drop", "a system is not part of a structure (use the reverse)"
        return "ok", "component or segment"
    rule = PROPOSED_PREDICATES.get(pred)
    if rule is None:
        return "drop", "unknown predicate"
    s_ok, o_ok = rule[0], rule[1]
    if s_kind not in s_ok:
        return "drop", f"{pred} subject must be one of {sorted(s_ok)}, got {s_kind}"
    if o_kind not in o_ok:
        return "drop", f"{pred} object must be one of {sorted(o_ok)}, got {o_kind}"
    return "ok", "kind rule satisfied"


def guard_triple(pred: str, s_label: str, o_label: str, s_kind: str | None = None, o_kind: str | None = None) -> tuple[str, str]:
    """check_anatomy_kinds with kinds inferred from names when the extractor did not give them."""
    return check_anatomy_kinds(pred, s_kind or infer_kind(s_label), o_kind or infer_kind(o_label), s_label, o_label)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "reports/anatomy_relations_plan.json"))
    ap.add_argument("--min-words", type=int, default=MIN_WORDS, help="merge heading blocks of a section up to this size (cap %d)" % MAX_WORDS)
    a = ap.parse_args()
    ps = passages(a.min_words)
    report = {"note": "dry run, $0 spent, nothing applied", "min_words": a.min_words,
              "all_passage_words": sum(p["words"] for p in ps), "prices_usd_per_M_tokens": {k: {"in": v[0], "out": v[1]} for k, v in PRICES.items()},
              "stage_c": stage_c(ps), "stage_b": stage_b(),
              "proposed_schema": {k: v for k, v in PROPOSED_SCHEMA.items()},
              "guard_examples": {f"{p}: {s} -> {o}": list(guard_triple(p, s, o)) for p, s, o in [
                  ("PART_OF", "Coronary artery", "Ascending aorta"), ("BRANCH_OF", "Coronary artery", "Ascending aorta"),
                  ("PART_OF", "Ascending aorta", "Aorta"), ("PART_OF", "Heart", "Cardiovascular system"),
                  ("BRANCH_OF", "Heart", "Aorta"), ("BRANCH_OF", "Ulnar nerve", "Medial cord"),
                  ("BRANCH_OF", "Radial artery", "Median nerve")]}}
    Path(a.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("stage_c", "stage_b")}, indent=1))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
