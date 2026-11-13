"""Build data/graph/atlas_crosswalk.jsonl: ontology AnatomicalStructure entities -> 3D atlas concepts.

    .venv/bin/python scripts/build_atlas_crosswalk.py [--atlas-json PATH] [--budget 0.30] [--dry]

Order: (1) exact normalised-name match (ontology.merge.merge_key, minus 'the')  ->  (2) bge-small top-3 candidates
(cosine >= MIN_COS, never across left/right)  ->  (3) a DeepSeek yes/no ('is this the same anatomical structure?')
for those candidates only. Only 'same' answers are written, so a link is exact or absent. Audit: --audit N prints a
random sample for hand checking. Needs the atlas catalogue (public/models/atlas.json of the built human-atlas clone).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag import backends, config  # noqa: E402
from rag.atlas import PATH, name_key  # noqa: E402
from rag.ontology_facts import facts  # noqa: E402

DEFAULT_ATLAS = Path.home() / "Projects/third_party/human-atlas/public/models/atlas.json"
CACHE = PATH.parent / "atlas_crosswalk_llm_cache.jsonl"
MIN_COS = 0.78
TOP_K = 3
BATCH = 25
PRICE_IN, PRICE_OUT = 0.28 / 1e6, 1.10 / 1e6
SIDES = ("left", "right")
# Whole-category atlas concepts: isolating "nerve" or "artery" highlights every one, which is no link to a structure.
GENERIC = {"artery", "vein", "nerve", "muscle", "bone", "ligament", "tendon", "cartilage", "gland", "organ", "ganglion"}

SYSTEM = ("You match anatomical structure names from a clinical textbook ontology to concepts of a 3D anatomy atlas "
          "(Foundational Model of Anatomy names). For each item decide whether ONE candidate is the SAME anatomical "
          "structure, i.e. a true synonym that a student would highlight as the very same thing (e.g. 'Bladder' = "
          "'urinary bladder', 'Scaphoid bone' = 'scaphoid', 'Serratus anterior muscle' = 'serratus anterior'). "
          "Answer 0 (no match) when the candidate is: a parent group or category ('muscle of pharynx', 'ganglion', "
          "'compartment'), a part, branch or subdivision, a tendon where the item is a muscle or the reverse, a "
          "layer or space of something, a different side, or merely a neighbour. Prefer 0 when unsure: a wrong link "
          "is worse than no link. "
          "Reply as JSON: {\"results\": [{\"i\": <item number>, \"match\": <candidate number or 0>}]}.")


def side(s: str) -> str | None:
    w = set(s.lower().split())
    return next((x for x in SIDES if x in w), None)


def ontology_structures() -> dict[str, str]:
    """name_key -> label, for every AnatomicalStructure in certified facts."""
    out: dict[str, str] = {}
    for f in facts():
        for p in ("subject", "object"):
            if f[p + "_type"] == "AnatomicalStructure":
                out.setdefault(name_key(f[p + "_label"]), f[p + "_label"])
    return out


def load_cache() -> dict:
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                cache[r["q"] + "|" + r["cand"]] = r["same"]
    return cache


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
    ap.add_argument("--budget", type=float, default=0.30)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--audit", type=int, default=0)
    a = ap.parse_args()

    atlas = json.loads(a.atlas_json.read_text())["concepts"]
    by_key: dict[str, list[dict]] = defaultdict(list)
    for c in atlas:
        by_key[name_key(c["name"])].append(c)
    ont = ontology_structures()

    rows, unmatched = [], []
    for key, label in ont.items():
        hits = [c for c in by_key.get(key, []) if c["name"].lower() not in GENERIC]
        if hits:
            c = min(hits, key=lambda c: int(c["id"][3:]) if c["id"][3:].isdigit() else 0)
            rows.append({"label": label, "key": key, "atlas_id": c["id"], "atlas_name": c["name"],
                         "method": "exact", "score": 1.0})
        else:
            unmatched.append((key, label))
    print(f"{len(ont)} structures, {len(rows)} exact, {len(unmatched)} left for embeddings")

    names = [c["name"] for c in atlas]
    A = np.array(backends.embed(names))
    Q = np.array(backends.embed([l for _, l in unmatched], is_query=True))
    sims = Q @ A.T
    pending = []
    for (key, label), s in zip(unmatched, sims):
        cands = []
        for j in np.argsort(-s)[:TOP_K * 3]:
            if atlas[j]["name"].lower() in GENERIC or s[j] < MIN_COS or (side(label) != side(atlas[j]["name"]) and (side(label) or side(atlas[j]["name"]))):
                continue
            cands.append({"id": atlas[j]["id"], "name": atlas[j]["name"], "score": float(s[j])})
            if len(cands) == TOP_K:
                break
        if cands:
            pending.append((label, cands))
    print(f"{len(pending)} with candidates to judge")
    if a.dry:
        return

    cache = load_cache()
    spent = judge(pending, cache, a.budget)
    keys = {label: key for key, label in unmatched}
    for label, cands in pending:
        for c in cands:
            if cache.get(label + "|" + c["id"]):
                rows.append({"label": label, "key": keys[label], "atlas_id": c["id"], "atlas_name": c["name"],
                             "method": "embedding+llm", "score": round(c["score"], 3)})
                break
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"wrote {len(rows)}/{len(ont)} links ({len(rows) / len(ont):.0%}); deepseek est. ${spent:.3f} -> {PATH}")
    if a.audit:
        random.seed(0)
        for r in random.sample(rows, min(a.audit, len(rows))):
            print(f"{r['method']:14} {r['label']!r:50} -> {r['atlas_name']!r}")


if __name__ == "__main__":
    main()
