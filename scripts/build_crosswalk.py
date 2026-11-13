"""Build data/graph/crosswalk.jsonl: ontology conditions/phenotypes <-> BODHI conditions/symptoms.

    .venv/bin/python scripts/build_crosswalk.py --dry            # candidates + cost estimate, no LLM
    .venv/bin/python scripts/build_crosswalk.py [--budget 0.9]   # adjudicate with DeepSeek (cached) and write

Order: id / name-key / synset / bge-small top-5 candidates -> deterministic exact (normalised-name equality, compatible
types) -> DeepSeek (batched, temperature 0, JSON) judges only the remaining candidate pairs -> typing rules -> write.
Stops (and writes what it has) if the estimated DeepSeek spend would pass --budget dollars.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.request
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag import config  # noqa: E402
from rag.crosswalk import BODHI_KIND, ONT_KIND, PATH, kinds_compatible, norm_name, qualifier_set, tier_of, token_key  # noqa: E402
from rag.graph import SYNONYMS, load_graph  # noqa: E402
from rag.ontology_facts import facts  # noqa: E402
from ontology.registry import MEDICAL_SYNSETS  # noqa: E402

OUT = PATH.parent
EMB_CACHE = OUT / "crosswalk_emb.npz"
LLM_CACHE = OUT / "crosswalk_llm_cache.jsonl"
META = OUT / "crosswalk_meta.json"
PROMPT_V = "v1"
VERIFY_V = "verify1"
T2_MIN_COS = 0.88        # an LLM-exact link needs the embedding to agree this closely to be called checked
TOP_K = 5
TOP_OTHER = 2            # extra neighbours of the other kind, only to record typing mismatches
MIN_COS = 0.77           # bge-small cosine below which a candidate is not worth a paid judgement
MIN_COS_OTHER = 0.86
BATCH = 30
PRICE_IN, PRICE_OUT = 0.28 / 1e6, 1.10 / 1e6     # DeepSeek $/token, output priced at the top of the plan's range


# ---------- data ----------
def ontology_entities() -> dict[str, dict]:
    ents: dict[str, dict] = {}
    for f in facts():
        for p in ("subject", "object"):
            if f[p + "_type"] in ONT_KIND:
                ents.setdefault(f[p + "_id"], {"id": f[p + "_id"], "label": f[p + "_label"], "type": f[p + "_type"]})
    return ents


def bodhi_groups() -> dict[str, dict]:
    """One group per (kind, normalised name): symptom variants and Condition/Concept twins collapse into one node."""
    g = load_graph()
    groups: dict[tuple, dict] = {}
    for nid, d in g.nodes(data=True):
        kind = BODHI_KIND.get(d["type"])
        if not kind:
            continue
        key = (kind, norm_name(d["name"]))
        if not key[1]:
            continue
        grp = groups.setdefault(key, {"ids": [], "name": d["name"], "type": d["type"], "kind": kind, "deg": -1, "rep": nid})
        grp["ids"].append(nid)
        if d["type"] == "Condition":
            grp["type"] = "Condition"
        if g.degree(nid) > grp["deg"]:
            grp["deg"], grp["rep"], grp["name"] = g.degree(nid), nid, d["name"]
    return {v["rep"]: v for v in groups.values()}


# ---------- candidates ----------
def deterministic(ents, groups):
    """Return (records, candidates). candidates: (ont_id, rep) -> set of signals for the LLM to judge."""
    by_norm, by_tok, by_id = defaultdict(list), defaultdict(list), {}
    for rep, grp in groups.items():
        by_norm[norm_name(grp["name"])].append(rep)
        by_tok[token_key(grp["name"])].append(rep)
        for i in grp["ids"]:
            by_id[i] = rep
    synonyms = {k.lower(): v for k, v in {**MEDICAL_SYNSETS, **SYNONYMS}.items()}
    recs, cands = {}, defaultdict(set)

    def add(oid, rep, relation, method, score, note="", checked=True):
        recs.setdefault((oid, rep), []).append((relation, method, score, note, checked))

    for oid, e in ents.items():
        n, t = norm_name(e["label"]), token_key(e["label"])
        hit = set(by_norm.get(n, [])) | set(by_tok.get(t, []))
        for rep in hit:
            grp = groups[rep]
            exact_ok = kinds_compatible(e["type"], grp["type"])
            method = "name_key" if rep in by_norm.get(n, []) else "name_tokens"
            if exact_ok:
                add(oid, rep, "exact", method, 1.0)
            else:
                add(oid, rep, "related", method, 0.9, f"typing mismatch: ontology {e['type']} vs BODHI {grp['type']} with the same name")
        if oid in by_id and by_id[oid] not in hit:
            cands[(oid, by_id[oid])].add("id")
        syn = synonyms.get(e["label"].lower())
        if syn:
            for rep in by_norm.get(norm_name(syn), []):
                if rep not in hit:
                    cands[(oid, rep)].add("synset")
    return recs, cands


def embeddings(ents, groups):
    ont_ids = sorted(ents)
    reps = sorted(groups)
    sig = hashlib.md5(json.dumps([[ents[i]["label"] for i in ont_ids], [groups[r]["name"] for r in reps]]).encode()).hexdigest()
    if EMB_CACHE.exists():
        z = np.load(EMB_CACHE, allow_pickle=False)
        if str(z["sig"]) == sig:
            return ont_ids, reps, z["ont"], z["bodhi"]
    from rag.backends import _local_model
    m = _local_model()
    enc = lambda xs: m.encode(xs, normalize_embeddings=True, batch_size=128, show_progress_bar=False).astype("float32")
    ov, bv = enc([ents[i]["label"] for i in ont_ids]), enc([groups[r]["name"] for r in reps])
    OUT.mkdir(parents=True, exist_ok=True)
    np.savez(EMB_CACHE, sig=sig, ont=ov, bodhi=bv)
    return ont_ids, reps, ov, bv


def embedding_candidates(ents, groups, recs, cands):
    ont_ids, reps, ov, bv = embeddings(ents, groups)
    kinds = np.array([groups[r]["kind"] for r in reps])
    sims = ov @ bv.T
    done = {o for (o, _), rs in recs.items() if any(r[0] == "exact" for r in rs)}
    scores = {}
    for i, oid in enumerate(ont_ids):
        if oid in done:
            continue
        kind = ONT_KIND[ents[oid]["type"]]
        for same, k, floor in ((True, TOP_K, MIN_COS), (False, TOP_OTHER, MIN_COS_OTHER)):
            mask = (kinds == kind) == same
            idx = np.where(mask)[0]
            top = idx[np.argsort(-sims[i, idx])[:k]]
            for j in top:
                if sims[i, j] >= floor:
                    cands[(oid, reps[j])].add("embedding")
                    scores[(oid, reps[j])] = float(sims[i, j])
    for (oid, rep) in cands:
        if (oid, rep) not in scores:
            scores[(oid, rep)] = float(ov[ont_ids.index(oid)] @ bv[reps.index(rep)])
    return scores


# ---------- DeepSeek ----------
SYSTEM = """You map medical concepts between two vocabularies. For each numbered pair, the ONTOLOGY entity comes from
medical textbooks and the BODHI node from a clinical knowledge graph. Say how the BODHI node relates to the ONTOLOGY entity:
 exact    - the same clinical concept at the same specificity (synonym, spelling, acronym, eponym, word order).
            Qualifiers must match: acute/chronic, type 1/2, severity, site, laterality, organism, age group, cause.
 broader  - the BODHI node is a more general concept (ontology 'Acute asthma' -> BODHI 'Asthma').
 narrower - the BODHI node is a more specific concept (ontology 'Asthma' -> BODHI 'Asthma in pregnancy').
 related  - clearly connected but a different concept (a disease and one of its symptoms, a cause and its effect, siblings).
 none     - unrelated, or you are unsure.
Be strict with "exact": when in doubt choose broader, narrower, related or none. Answer with JSON only:
{"1": "exact", "2": "none", ...} using every pair number."""


VERIFY_SYSTEM = SYSTEM + """

SECOND OPINION. Each pair below was already judged "exact" once; a reviewer found that about 1 in 8 such pairs is wrong.
Answer "exact" ONLY if a clinician would use the two names interchangeably in a differential-diagnosis list with no loss
of meaning. Choose narrower/broader when one name adds or drops a qualifier (primary, massive, severe, acute, site, cause,
subtype). Choose related when one is a symptom/finding and the other a disease, or the two only overlap partly
(e.g. 'Sadness' vs 'Depressed mood', 'Arthralgia/arthritis' vs 'Joint pain', 'Behavioral symptoms' vs 'Change in behaviour')."""


def _ask(pairs: list[str], system: str = SYSTEM) -> tuple[dict, int, int]:
    body = json.dumps({"model": config.DEEPSEEK_MODEL, "temperature": 0, "max_tokens": 40 + 14 * len(pairs), "stream": False,
                       "response_format": {"type": "json_object"},
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": "\n".join(f"{i + 1}. {p}" for i, p in enumerate(pairs))}]}).encode()
    req = urllib.request.Request(f"{config.DEEPSEEK_BASE_URL}/chat/completions", body, {
        "Content-Type": "application/json", "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"})
    last = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            out = json.loads(d["choices"][0]["message"]["content"])
            u = d.get("usage", {})
            return out, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)
        except Exception as e:                       # noqa: BLE001 - retry any transport/parse error
            last = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"DeepSeek failed: {last}")


def pair_text(e, grp) -> str:
    return f"ONTOLOGY: {e['label']} [{ONT_KIND[e['type']]}] | BODHI: {grp['name']} [{BODHI_KIND[grp['type']]}]"


def judge(ents, groups, pending, budget, system=SYSTEM, version=PROMPT_V):
    cache = {}
    if LLM_CACHE.exists():
        for l in LLM_CACHE.read_text().splitlines():
            if l.strip():
                r = json.loads(l)
                cache[(r["ont_id"], r["rep"], r["v"])] = r
    todo = [k for k in pending if (*k, version) not in cache]
    spent = sum(r.get("cost", 0) for r in cache.values())
    est_in = len(system) / 3.2 + 40
    per_pair_in, per_pair_out = 32, 8
    print(f"pairs to judge: {len(todo)} (cached {len(pending) - len(todo)}), spent so far ${spent:.4f}")
    stopped = False
    with LLM_CACHE.open("a") as fh:
        for s in range(0, len(todo), BATCH):
            chunk = todo[s:s + BATCH]
            est = (est_in + per_pair_in * len(chunk)) * PRICE_IN + (per_pair_out * len(chunk) + 10) * PRICE_OUT
            if spent + est > budget:
                print(f"STOP: next batch (~${est:.4f}) would pass the ${budget} budget (spent ${spent:.4f})")
                stopped = True
                break
            out, tin, tout = _ask([pair_text(ents[o], groups[r]) for o, r in chunk], system)
            cost = (tin * PRICE_IN + tout * PRICE_OUT)
            spent += cost
            for i, (o, r) in enumerate(chunk):
                rel = str(out.get(str(i + 1), "none")).strip().lower()
                rel = rel if rel in ("exact", "broader", "narrower", "related", "none") else "none"
                row = {"ont_id": o, "rep": r, "relation": rel, "v": version, "cost": cost / len(chunk)}
                cache[(o, r, version)] = row
                fh.write(json.dumps(row) + "\n")
            fh.flush()
            if (s // BATCH) % 20 == 0:
                print(f"  {s + len(chunk)}/{len(todo)} spent ${spent:.4f}", flush=True)
    return cache, spent, stopped


# ---------- assemble ----------
def assemble(ents, groups, recs, cands, scores, verdicts):
    final = {}
    for (oid, rep), rs in recs.items():
        final[(oid, rep)] = max(rs, key=lambda r: (r[0] == "exact", r[2]))
    for key, signals in cands.items():
        if key in final:
            continue
        rel = verdicts[(*key, PROMPT_V)]["relation"] if (*key, PROMPT_V) in verdicts else "none"
        if rel == "none":
            continue
        oid, rep = key
        e, grp = ents[oid], groups[rep]
        method = "+".join(sorted(signals)) + "+llm"
        note, checked = "", False
        if not kinds_compatible(e["type"], grp["type"]):
            note = f"typing mismatch: ontology {e['type']} vs BODHI {grp['type']}"
            rel = "related"                           # a cross-type link is never exact/broader/narrower
        elif rel == "exact":
            second = verdicts.get((*key, VERIFY_V))
            if second is None:
                continue                                # unverified exact (budget stop): not recorded
            method += "2"
            if second["relation"] != "exact":
                rel = second["relation"] if second["relation"] != "none" else "related"
                note = "second opinion disagreed with exact"
            elif qualifier_set(e["label"]) != qualifier_set(grp["name"]):
                rel, note = "related", "qualifier mismatch (acute/primary/type/site...)"
            else:
                checked = scores.get(key, 0.0) >= T2_MIN_COS or bool(signals & {"id", "synset"})
        final[key] = (rel, method, scores.get(key, 0.0), note, checked)
    rows = []
    g = load_graph()
    for (oid, rep), (rel, method, score, note, checked) in final.items():
        e, grp = ents[oid], groups[rep]
        rows.append({"ont_id": oid, "ont_label": e["label"], "ont_type": e["type"], "bodhi_id": rep, "bodhi_ids": sorted(grp["ids"]),
                     "bodhi_name": g.nodes[rep]["name"], "bodhi_type": grp["type"], "relation": rel, "score": round(score, 4),
                     "method": method, "checked": checked, "tier": tier_of(rel, checked), "note": note,
                     "created_by": "build_crosswalk.py"})
    rows.sort(key=lambda r: (r["ont_label"].lower(), r["relation"], -r["score"]))
    return rows


def coverage(ents, groups, rows):
    g = load_graph()
    cond = [i for i, e in ents.items() if e["type"] == "PathologicalCondition"]
    phen = [i for i, e in ents.items() if e["type"] == "ClinicalPhenotype"]
    pct = lambda n, d: round(100 * n / d, 1)
    base = lambda ids: sum(i in g for i in ids)
    linked = lambda ids, pred: len({r["ont_id"] for r in rows if r["ont_id"] in set(ids) and pred(r)})
    t2 = lambda r: r["tier"] == "T2"
    anyx = lambda r: r["relation"] == "exact"
    anyr = lambda r: True
    from rag.ontology_facts import condition_labels, match_conditions
    fact_labels = set(condition_labels())
    bconds = [n for n, d in g.nodes(data=True) if d["type"] == "Condition"]
    sym = {n for n in bconds if any(d.get("relation") == "PRESENT_IN" for _, _, d in g.in_edges(n, data=True))}
    by_rep = defaultdict(list)
    for r in rows:
        if r["relation"] == "exact" and r["tier"] == "T2" and r["ont_label"] in fact_labels:
            for i in r["bodhi_ids"]:
                by_rep[i].append(r)
    before = {n for n in bconds if match_conditions(g.nodes[n]["name"])}
    after = before | {n for n in bconds if n in by_rep}
    return {
        "ontology_conditions": len(cond), "ontology_phenotypes": len(phen),
        "before_id_link_conditions_pct": pct(base(cond), len(cond)), "before_id_link_phenotypes_pct": pct(base(phen), len(phen)),
        "after_t2_conditions_pct": pct(linked(cond, t2), len(cond)), "after_t2_phenotypes_pct": pct(linked(phen, t2), len(phen)),
        "after_exact_conditions_pct": pct(linked(cond, anyx), len(cond)), "after_exact_phenotypes_pct": pct(linked(phen, anyx), len(phen)),
        "after_any_conditions_pct": pct(linked(cond, anyr), len(cond)), "after_any_phenotypes_pct": pct(linked(phen, anyr), len(phen)),
        "bodhi_conditions": len(bconds), "bodhi_conditions_with_symptom_edges": len(sym),
        "bodhi_cond_reach_facts_before_pct": pct(len(before), len(bconds)),
        "bodhi_cond_reach_facts_after_t2_pct": pct(len(after), len(bconds)),
        "bodhi_symptom_cond_reach_before_pct": pct(len(before & sym), len(sym)),
        "bodhi_symptom_cond_reach_after_t2_pct": pct(len(after & sym), len(sym)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--budget", type=float, default=0.9)
    ap.add_argument("--min-cos", type=float, default=None)
    a = ap.parse_args()
    global MIN_COS
    if a.min_cos:
        MIN_COS = a.min_cos
    ents, groups = ontology_entities(), bodhi_groups()
    print(f"ontology entities {len(ents)}, BODHI groups {len(groups)}")
    recs, cands = deterministic(ents, groups)
    scores = embedding_candidates(ents, groups, recs, cands)
    pending = [k for k in cands if k not in recs]
    print(f"deterministic pairs {len(recs)}, candidate pairs to judge {len(pending)}")
    if a.dry:
        est = len(pending) / BATCH * ((len(SYSTEM) / 3.2 + 40) * PRICE_IN + 10 * PRICE_OUT) + len(pending) * (32 * PRICE_IN + 8 * PRICE_OUT)
        print(f"estimated cost ${est:.3f}")
        return
    cache, spent, stopped = judge(ents, groups, pending, a.budget)
    exact1 = [k for k in pending if cache.get((*k, PROMPT_V), {}).get("relation") == "exact"
              and kinds_compatible(ents[k[0]]["type"], groups[k[1]]["type"])]
    cache, spent, stop2 = judge(ents, groups, exact1, a.budget, VERIFY_SYSTEM, VERIFY_V)
    stopped = stopped or stop2
    rows = assemble(ents, groups, recs, cands, scores, cache)
    OUT.mkdir(parents=True, exist_ok=True)
    PATH.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    cov = coverage(ents, groups, rows)
    from collections import Counter
    cov.update({"rows": len(rows), "by_relation": Counter(r["relation"] for r in rows), "by_tier": Counter(r["tier"] for r in rows),
                "deepseek_spent_usd": round(spent, 4), "budget_stopped": stopped, "unjudged_pairs": sum(1 for k in pending if (*k, PROMPT_V) not in cache)})
    META.write_text(json.dumps(cov, indent=1))
    print(json.dumps(cov, indent=1))


if __name__ == "__main__":
    main()
