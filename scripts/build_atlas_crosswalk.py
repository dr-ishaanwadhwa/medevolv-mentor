"""Build data/graph/atlas_crosswalk.jsonl: labels -> 3D atlas concepts. Deterministic first, LLM only for leftovers.

    .venv/bin/python scripts/build_atlas_crosswalk.py [--atlas-json PATH] [--budget 0.20] [--dry] [--audit N]

Source labels: every ontology entity label (any type), and Gray's Anatomy section titles and heading-path components
(data/okf/grays/toc.json, titles only). The crosswalk gets
  1. every atlas name (key = rag.atlas.name_key), plus a combined left+right record for a structure the atlas only
     draws as a pair ('lung' -> right lung + left lung); whole-organ concepts win over sub-pieces because only the
     exact name is an alias, never a substring;
  2. curated synonyms (SYNONYMS below), kept only when the target exists in the atlas;
  3. for ontology AnatomicalStructure/OrganSystem labels still unmatched after rag.atlas.variants (plural, 'the',
     'X of Y' order, trailing muscle/bone, hyphens, left/right): bge-small top-3 candidates (cosine >= MIN_COS, never
     across left/right) and one batched DeepSeek yes/no per label, cached in atlas_crosswalk_llm_cache.jsonl.
Only 'same structure' answers are written, so a link is exact or absent. --audit N prints a random sample of the
labels that link, with the method, for hand checking. Needs the atlas catalogue (public/models/atlas.json of the
built human-atlas clone).
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag import atlas as A  # noqa: E402
from rag import backends  # noqa: E402
from rag.atlas import PATH, SIDES, name_key, resolve  # noqa: E402
from rag.ontology_facts import facts  # noqa: E402

DEFAULT_ATLAS = Path.home() / "Projects/third_party/human-atlas/public/models/atlas.json"
TOC = Path("data/okf/grays/toc.json")
CACHE = PATH.parent / "atlas_crosswalk_llm_cache.jsonl"
MIN_COS = 0.78
TOP_K = 3
BATCH = 25
PRICE_IN, PRICE_OUT = 0.28 / 1e6, 1.10 / 1e6
STRUCTURE_TYPES = {"AnatomicalStructure", "OrganSystem"}
# Whole-category atlas concepts: isolating "nerve" or "artery" highlights every one, which is no link to a structure.
GENERIC = {"artery", "vein", "nerve", "muscle", "bone", "ligament", "tendon", "cartilage", "gland", "organ", "ganglion",
           "anatomical entity", "membrane organ", "cranial nerve", "nerve trunk", "skeleton", "trunk"}
NOT_ALIAS = ("set of ", "branch of ", "tributary of ", "anatomical ", "segment of ")   # pieces / categories

# Other names for the same structure (textbook or lay term -> atlas name). Applied only if the target is in the atlas.
SYNONYMS: dict[str, str | list[str]] = {
    "bladder": "urinary bladder", "windpipe": "trachea", "gullet": "esophagus", "gall bladder": "gallbladder",
    "small bowel": "small intestine", "large bowel": "large intestine", "suprarenal gland": "adrenal gland",
    "thighbone": "femur", "thigh bone": "femur", "shinbone": "tibia", "shin bone": "tibia", "collarbone": "clavicle",
    "collar bone": "clavicle", "shoulder blade": "scapula", "breastbone": "sternum", "aortic arch": "arch of aorta",
    "ivc": "inferior vena cava", "svc": "superior vena cava", "common carotid": "common carotid artery",
    "internal carotid": "internal carotid artery", "kneecap": "patella", "knee cap": "patella",
    "heel bone": "calcaneus", "jawbone": "mandible", "lower jaw": "mandible", "upper jaw": "maxilla",
    "cheekbone": "zygomatic bone", "pelvic bone": "hip bone", "diaphragm muscle": "diaphragm",
    "long saphenous vein": "great saphenous vein", "short saphenous vein": "small saphenous vein",
    "achilles tendon": "calcaneal tendon", "gluteus maximus muscle": "gluteus maximus",
    "hepatic portal vein": "portal vein", "coeliac trunk": "celiac trunk", "coeliac artery": "celiac trunk",
    "mitral valve": "left atrioventricular valve", "tricuspid valve": "right atrioventricular valve",
    "intervertebral disc": "intervertebral disk", "spine": "vertebral column", "backbone": "vertebral column",
    "spinal column": "vertebral column", "rib cage": "thoracic cage", "pituitary": "pituitary gland",
    "hypophysis": "pituitary gland", "psoas": "psoas major", "psoas muscle": "psoas major",
    "retina": "optic part of retina", "right and left brachiocephalic veins": "brachiocephalic vein",
    # a muscle or pair the atlas draws only as its parts: select all the parts together
    "trapezius": ["ascending part of trapezius", "transverse part of trapezius", "descending part of trapezius"],
    "biceps brachii": ["long head of biceps brachii", "short head of biceps brachii"],
    "biceps": ["long head of biceps brachii", "short head of biceps brachii"],
    "triceps brachii": ["long head of triceps brachii", "medial head of triceps brachii",
                        "lateral head of triceps brachii"],
    "triceps": ["long head of triceps brachii", "medial head of triceps brachii", "lateral head of triceps brachii"],
    "rhomboids": ["rhomboid major", "rhomboid minor"], "rhomboid muscles": ["rhomboid major", "rhomboid minor"],
    "tibial veins": ["anterior tibial vein", "posterior tibial vein"],
}


def load_atlas(path: Path) -> list[dict]:
    return json.loads(path.read_text())["concepts"]


def alias_table(atlas: list[dict]) -> dict[str, dict]:
    """key -> record for every atlas name, plus a left+right record for pairs drawn only as two sided concepts."""
    real: dict[str, dict] = {}
    for c in atlas:
        k = name_key(c["name"])
        if c["name"].lower() in GENERIC or k in GENERIC or c["name"].lower().startswith(NOT_ALIAS):
            continue
        if k not in real or len(c["elements"]) > len(real[k]["_el"]):     # same name twice: the bigger drawing
            real[k] = {"label": c["name"], "key": k, "atlas_id": c["id"], "atlas_name": c["name"],
                       "method": "atlas-name", "score": 1.0, "_el": c["elements"]}
    pairs: dict[str, dict[str, dict]] = defaultdict(dict)
    for k, r in real.items():
        ws = k.split()
        sides = [w for w in ws if w in SIDES]
        if len(sides) == 1:
            pairs[" ".join(w for w in ws if w not in SIDES)][sides[0]] = r
    table = {k: {x: v for x, v in r.items() if x != "_el"} for k, r in real.items()}
    for u, pr in pairs.items():
        if u and u not in table and len(pr) == 2:
            l, r = pr["left"], pr["right"]
            table[u] = {"label": u, "key": u, "atlas_id": r["atlas_id"], "atlas_ids": [r["atlas_id"], l["atlas_id"]],
                        "by_side": {"right": r["atlas_id"], "left": l["atlas_id"]},
                        "atlas_name": u + " (left and right)", "method": "atlas-pair", "score": 1.0}
    return table


def add_synonyms(table: dict[str, dict]) -> list[str]:
    missing = []
    for syn, target in SYNONYMS.items():
        sk = name_key(syn)
        if sk in table:
            continue                      # the atlas already has that name
        if isinstance(target, list):                   # several atlas concepts together
            parts = [table.get(name_key(x)) for x in target]
            if all(parts):
                ids = [i for p in parts for i in (p.get("atlas_ids") or [p["atlas_id"]])]
                table[sk] = {"label": syn, "key": sk, "atlas_id": ids[0], "atlas_ids": ids,
                             "atlas_name": " + ".join(p["atlas_name"] for p in parts), "method": "synonym-parts",
                             "score": 1.0}
            else:
                missing.append(f"{syn} -> {target}")
            continue
        t = table.get(name_key(target))
        if t:
            table[sk] = {**t, "label": syn, "key": sk, "method": "synonym"}
        else:
            missing.append(f"{syn} -> {target}")
    return missing


def ontology_labels() -> dict[str, tuple[str, set]]:
    """name_key -> (label, set of entity types) over all certified facts."""
    out: dict[str, tuple[str, set]] = {}
    for f in facts():
        for p in ("subject", "object"):
            k = name_key(f[p + "_label"])
            lab, types = out.setdefault(k, (f[p + "_label"], set()))
            types.add(f[p + "_type"])
    return out


_SKIP = re.compile(r"^(case \d+|part [ivx]+|\d+ |table |chapter )", re.I)


def gray_labels() -> dict[str, str]:
    """name_key -> title, for the Gray's Anatomy section titles and every heading-path component (titles only)."""
    out: dict[str, str] = {}
    if not TOC.exists():
        return out
    for s in json.loads(TOC.read_text()):
        for comp in s["path"].split(" › ")[1:]:
            comp = re.sub(r"\s*\[[^\]]*\]$", "", comp.split(":")[-1].strip() if comp.lower().startswith("case") else comp)
            comp = comp.strip()
            if comp and not _SKIP.match(comp) and len(comp.split()) <= 6:
                out.setdefault(name_key(comp), comp)
    return out


def side(s: str) -> str | None:
    w = set(s.lower().split())
    return next((x for x in SIDES if x in w), None)


def load_cache() -> dict:
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r["q"] + "|" + r["cand"]] = r["same"]
    return cache


SYSTEM = ("You match anatomical structure names from a clinical textbook ontology to concepts of a 3D anatomy atlas "
          "(Foundational Model of Anatomy names). For each item decide whether ONE candidate is the SAME anatomical "
          "structure, i.e. a true synonym that a student would highlight as the very same thing (e.g. 'Bladder' = "
          "'urinary bladder', 'Scaphoid bone' = 'scaphoid', 'Serratus anterior muscle' = 'serratus anterior'). "
          "Answer 0 (no match) when the candidate is: a parent group or category ('muscle of pharynx', 'ganglion', "
          "'compartment'), a part, branch or subdivision, a tendon where the item is a muscle or the reverse, a "
          "layer or space of something, a different side, or merely a neighbour. Prefer 0 when unsure: a wrong link "
          "is worse than no link. "
          "Reply as JSON: {\"results\": [{\"i\": <item number>, \"match\": <candidate number or 0>}]}.")


def judge(pending: list[tuple[str, list[dict]]], cache: dict, budget: float) -> float:
    """Ask DeepSeek about (label, candidates) items; fills cache[label|atlas_id] = bool. Returns dollars spent."""
    spent = 0.0
    todo = [(q, c) for q, c in pending if any(q + "|" + x["id"] not in cache for x in c)]
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        lines = []
        for n, (q, cands) in enumerate(batch, 1):
            lines.append(f"{n}. Ontology: {q}\n" + "\n".join(f"   {k}) {c['name']}" for k, c in enumerate(cands, 1)))
        user = "\n".join(lines)
        est = (len(SYSTEM) + len(user)) / 3.5 * PRICE_IN + 25 * len(batch) * PRICE_OUT
        if spent + est > budget:
            print("budget reached, stopping LLM judging", file=sys.stderr)
            break
        raw = backends._deepseek_chat(SYSTEM, user, 0.0, 1200, True)
        spent += est
        got = {r["i"]: r["match"] for r in json.loads(raw)["results"]}
        with CACHE.open("a") as fh:
            for n, (q, cands) in enumerate(batch, 1):
                m = got.get(n, 0)
                for k, c in enumerate(cands, 1):
                    same = m == k
                    cache[q + "|" + c["id"]] = same
                    fh.write(json.dumps({"q": q, "cand": c["id"], "same": same}) + "\n")
    return spent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas-json", type=Path, default=DEFAULT_ATLAS)
    ap.add_argument("--budget", type=float, default=0.20)
    ap.add_argument("--dry", action="store_true", help="no LLM calls, no file written")
    ap.add_argument("--audit", type=int, default=0)
    ap.add_argument("--show-unmatched", action="store_true")
    a = ap.parse_args()

    atlas = load_atlas(a.atlas_json)
    table = alias_table(atlas)
    n_alias = len(table)
    missing = add_synonyms(table)
    if missing:
        print("synonym targets not in the atlas:", "; ".join(missing))
    ont, grays = ontology_labels(), gray_labels()
    sources = {k: (lab, "ontology", types) for k, (lab, types) in ont.items()}
    for k, lab in grays.items():
        sources.setdefault(k, (lab, "grays", set()))
    print(f"{n_alias} atlas aliases, {len(table) - n_alias} synonyms, {len(ont)} ontology labels, {len(grays)} Gray's labels")

    hit = {k: resolve(lab, table) for k, (lab, _, _) in sources.items()}
    # Non-structure ontology types (drugs, procedures, findings) link only when the label is spelled exactly like the
    # atlas name or synonym: merge_key drops ' replacement', so 'Pulmonary valve replacement' must not become the valve.
    plain = lambda x: re.sub(r"[^a-z0-9]+", "", x.lower())          # noqa: E731
    for k, (lab, src, types) in sources.items():
        r = hit[k]
        if r and src == "ontology" and not types & STRUCTURE_TYPES and plain(lab) != plain(r["label"]):
            hit[k] = None

    unmatched = [(k, sources[k][0]) for k, (lab, src, types) in sources.items()
                 if not hit[k] and src == "ontology" and types & STRUCTURE_TYPES]
    names = [c["name"] for c in atlas]
    by_id = {c["id"]: c for c in atlas}
    llm_rows, spent = [], 0.0
    if unmatched and not a.dry:
        import numpy as np
        A_ = np.array(backends.embed(names))
        Q = np.array(backends.embed([l for _, l in unmatched], is_query=True))
        sims = Q @ A_.T
        pending = []
        for (key, label), s in zip(unmatched, sims):
            cands = []
            for j in np.argsort(-s)[:TOP_K * 3]:
                n = atlas[j]["name"]
                if n.lower() in GENERIC or s[j] < MIN_COS or (side(label) != side(n) and (side(label) or side(n))):
                    continue
                cands.append({"id": atlas[j]["id"], "name": n, "score": float(s[j])})
                if len(cands) == TOP_K:
                    break
            if cands:
                pending.append((label, cands))
        print(f"{len(pending)} with candidates to judge")
        cache = load_cache()
        spent = judge(pending, cache, a.budget)
        keys = {label: key for key, label in unmatched}
        for label, cands in pending:
            for c in cands:
                if cache.get(label + "|" + c["id"]):
                    llm_rows.append({"label": label, "key": keys[label], "atlas_id": c["id"], "atlas_name": c["name"],
                                     "method": "embedding+llm", "score": round(c["score"], 3)})
                    break
    for r in llm_rows:
        table[r["key"]] = r
        hit[r["key"]] = r

    # Output: every atlas alias / synonym / LLM record; source labels resolve at lookup time through rag.atlas.variants.
    rows = list(table.values())
    if not a.dry:
        PATH.parent.mkdir(parents=True, exist_ok=True)
        PATH.write_text("".join(json.dumps(r) + "\n" for r in rows))
        print(f"wrote {len(rows)} records -> {PATH}")

    def n(src, only_struct=False):
        ks = [k for k, (_, s, t) in sources.items() if s == src and (not only_struct or t & STRUCTURE_TYPES)]
        return sum(1 for k in ks if hit[k]), len(ks)
    print("ontology structure labels linked: %d/%d" % n("ontology", True))
    print("ontology labels (any type) linked: %d/%d" % n("ontology"))
    print("Gray's labels linked: %d/%d" % n("grays"))
    print(f"deepseek est. ${spent:.3f}")
    if a.show_unmatched:
        print("UNMATCHED structures:", sorted(l for _, l in unmatched if not hit[_]))
    if a.audit:
        random.seed(0)
        linked = [(k, sources[k]) for k in sources if hit[k]]
        for k, (lab, src, types) in random.sample(linked, min(a.audit, len(linked))):
            r = hit[k]
            print(f"{src:8} {r['method']:14} {lab!r:48} -> {r['atlas_name']!r}")


if __name__ == "__main__":
    main()
