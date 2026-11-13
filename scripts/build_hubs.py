"""Build hub / map-of-content edges (Stage 3 of docs/graph_networking_plan.md).

    .venv/bin/python scripts/build_hubs.py            # uses the LLM cache; first run costs well under $1
    .venv/bin/python scripts/build_hubs.py --dry-run  # estimate LLM cost only, call nothing

Writes data/graph/hubs.jsonl (+ hubs_llm_cache.json, hubs_cost.json) and prints counts and the graph effect.
Nothing here edits the ontology. T2 = rule over certified facts, T3 = LLM judgement (kept with evidence).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rag import mentions, ontology_facts  # noqa: E402

OUT = ROOT / "data/graph/hubs.jsonl"
CACHE = ROOT / "data/graph/hubs_llm_cache.json"
COST = ROOT / "data/graph/hubs_cost.json"
BUDGET_USD = 1.0
# DeepSeek list prices are lower; these are deliberately pessimistic so the cap holds.
PRICE_IN, PRICE_OUT = 0.56 / 1e6, 1.68 / 1e6
MODIFIERS = {"acute", "chronic", "severe", "mild", "moderate", "primary", "secondary", "early", "late", "advanced",
             "recurrent", "idiopathic", "congenital", "acquired"}
NOT_A_DRUG = re.compile(r"therapy|surgery|resection|transplant|drainage|transfusion|\bdiet\b|exercise|ventilation|repair|"
                        r"excision|restriction|support|stimulation|care\b|withdrawal|discontinuation|reduction|"
                        r"\bplus\b| and |regimen|monitoring|education|counsel|biopsy|ablation|dialysis|"
                        r"oxygen|physiotherapy|rehabilitation|prophylaxis|injection|irrigation|debridement|screening", re.I)
CLASS_WORDS = re.compile(r"\b(inhibitors?|blockers?|antagonists?|agonists?|antibiotics?|statins?|diuretics?|corticosteroids?|"
                         r"glucocorticoids?|benzodiazepines?|agents|drugs|medications|antibacterials?|antifungals?|"
                         r"antivirals?|antimicrobials?|anticoagulants?|antiplatelets?|antihypertensives?|analgesics?|"
                         r"opioids?|antidepressants?|antipsychotics?|anticonvulsants?|antiepileptics?|vasodilators?|"
                         r"antiemetics?|antihistamines?|quinolones?|fluoroquinolones?|macrolides?|cephalosporins?|"
                         r"penicillins?|aminoglycosides?|carbapenems?|tetracyclines?|nsaids?|thiazides?|"
                         r"thiazolidinediones?|bisphosphonates?|antiarrhythmics?|nitrates?|vasopressors?|inotropes?|"
                         r"retinoids?|steroids?|immunosuppress\w+|antiseizure|interferons?)$", re.I)


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- LLM with cache and a hard cost cap
class Llm:
    def __init__(self, dry: bool):
        self.dry = dry
        self.cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
        self.spent = json.loads(COST.read_text()).get("usd", 0.0) if COST.exists() else 0.0
        self.pending_usd = 0.0
        self.calls = 0

    def ask(self, purpose: str, system: str, user: str, max_tokens: int) -> dict | None:
        key = hashlib.sha256((system + "\x00" + user).encode()).hexdigest()
        if key in self.cache:
            return self.cache[key]
        est = (len(system) + len(user)) / 4 * PRICE_IN + max_tokens * PRICE_OUT
        if self.dry:
            self.pending_usd += est
            return None
        if self.spent + est > BUDGET_USD:
            sys.exit(f"STOP: next call would take DeepSeek spend past ${BUDGET_USD:.2f} (spent ${self.spent:.3f}).")
        from rag import backends
        for _ in range(2):
            text = backends.chat(system, user, temperature=0, max_tokens=max_tokens, json_mode=True, purpose=purpose)
            self.spent += (len(system) + len(user)) / 4 * PRICE_IN + len(text) / 4 * PRICE_OUT
            self.calls += 1
            try:
                data = json.loads(text)
                break
            except json.JSONDecodeError:
                data = None
        if data is None:
            return None
        self.cache[key] = data
        CACHE.write_text(json.dumps(self.cache))
        COST.write_text(json.dumps({"usd": round(self.spent, 4), "note": "pessimistic estimate from char counts"}))
        return data


def batches(xs: list, n: int):
    for i in range(0, len(xs), n):
        yield xs[i:i + n]


# ---------------------------------------------------------------- data
def load_nodes() -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for f in ontology_facts.facts():
        for s in ("subject", "object"):
            nodes.setdefault(f[f"{s}_id"], {"id": f[f"{s}_id"], "label": f[f"{s}_label"], "type": f[f"{s}_type"]})
    return nodes


def rec(hub_id, hub_type, hub_label, node, tier, method, evidence=None) -> dict:
    return {"hub_id": hub_id, "hub_type": hub_type, "hub_label": hub_label, "member_id": node["id"],
            "member_label": node["label"], "member_type": node["type"], "tier": tier, "method": method,
            "evidence": evidence}


# (a) organ systems --------------------------------------------------------
def organ_hubs(nodes) -> list[dict]:
    by_label = defaultdict(list)
    for n in nodes.values():
        if n["type"] in ontology_facts.CONDITION_TYPES:
            by_label[n["label"]].append(n)
    out = []
    for system, cats in ontology_facts.catalog().items():
        if system == "Other":
            continue
        for labels in cats.values():
            for lab in labels:
                for n in by_label.get(lab, []):
                    out.append(rec(f"hub:organ:{slug(system)}", "organ_system", system, n, "T2", "catalog.group_of chapter"))
    chapters = defaultdict(Counter)                     # structures join a system through the chapter of their facts
    for f in ontology_facts.facts():
        if f["object_type"] == "AnatomicalStructure":
            p = f["provenance"]
            chapters[f["object_id"]][(p.get("book_id", ""), p.get("chapter", ""))] += 1
    for nid, cnt in chapters.items():
        book, chapter = cnt.most_common(1)[0][0]
        system, _ = ontology_facts.group_of(chapter, book)
        if system != "Other":
            out.append(rec(f"hub:organ:{slug(system)}", "organ_system", system, nodes[nid], "T2", "Gray's chapter -> system"))
    return out


# (b) mechanisms -----------------------------------------------------------
def mechanism_hubs(nodes) -> list[dict]:
    drugs = defaultdict(dict)
    for f in ontology_facts.facts():
        if f["predicate"] == "TARGETS_MECHANISM":
            drugs[f["object_id"]][f["subject_id"]] = f["id"]
    out = []
    for tid, ds in drugs.items():
        if len(ds) >= 2:
            for did in ds:
                out.append(rec(f"hub:mech:{slug(nodes[tid]['label'])}-{slug(tid)[-8:]}", "mechanism", nodes[tid]["label"],
                               nodes[did], "T2", f"TARGETS_MECHANISM fact {ds[did]}"))
    return out


# (c) organisms ------------------------------------------------------------
GENUS = re.compile(r"^([A-Z][a-z]{3,})\s+(spp?\.?|species|[a-z][a-z-]{2,}|[A-Z][a-z]+)\b")


def organism_hubs(nodes, llm: Llm) -> list[dict]:
    agents = sorted((n for n in nodes.values() if n["type"] == "EtiologicalAgent"), key=lambda n: n["label"])
    system = ("You classify infectious agents named in a medical textbook. For each numbered item return its standard "
              "taxonomic FAMILY (bacteria, viruses, fungi, parasites), e.g. 'Enterobacteriaceae', 'Flaviviridae', "
              "'Plasmodiidae'. Use the standard clinical group if no family fits (e.g. 'Dermatophytes'). Use null if the "
              "item is not a specific organism or group of organisms (wounds, toxins, drugs, conditions) or you are "
              "unsure. Reply as JSON: {\"1\": \"Family\", \"2\": null, ...} covering every number.")
    fam = {}
    for b in batches(agents, 60):
        user = "\n".join(f"{i}. {n['label']}" for i, n in enumerate(b, 1))
        res = llm.ask("hubs: organism family", system, user, 60 * 14)
        for i, n in enumerate(b, 1):
            v = (res or {}).get(str(i))
            # a family listed as a member of itself ('Retroviridae' -> Retroviridae) is not a link
            if isinstance(v, str) and 3 <= len(v) <= 40 and v.strip().lower() != n["label"].strip().lower():
                fam[n["id"]] = v.strip()
    out = []
    by_family = defaultdict(list)
    for n in agents:
        if n["id"] in fam:
            by_family[fam[n["id"]].lower()].append(n)
    for key, ns in by_family.items():
        if len(ns) >= 2:
            label = Counter(fam[n["id"]] for n in ns).most_common(1)[0][0]
            out += [rec(f"hub:family:{slug(label)}", "organism_family", label, n, "T3", "LLM family (batched)") for n in ns]
    genus = defaultdict(list)
    for n in agents:
        m = GENUS.match(n["label"])
        if m and n["id"] in fam:                         # the LLM must also agree that this is an organism
            genus[m.group(1)].append(n)
    for g, ns in genus.items():
        if len(ns) >= 2:
            out += [rec(f"hub:genus:{slug(g)}", "organism_genus", g, n, "T2", "genus parsed from label") for n in ns]
    return out


# (d) drug classes ---------------------------------------------------------
LINE_OF_THERAPY = re.compile(r"\b(first|second|third|1st|2nd|3rd)[- ]line\b|\breserve\b", re.I)


def drug_class_hubs(nodes, llm: Llm) -> list[dict]:
    agents = [n for n in nodes.values() if n["type"] == "TherapeuticAgent"]
    cands = sorted((n for n in agents if CLASS_WORDS.search(n["label"]) and not NOT_A_DRUG.search(n["label"])),
                   key=lambda n: n["label"])
    s1 = ("Decide which items are generic pharmacological classes or drug families that several different drugs belong to "
          "(e.g. 'Beta blockers', 'Macrolide antibiotics', 'Statins'). Reject single drugs or single hormones, regimens "
          "or combinations, procedures, withdrawal or dose changes, and variants defined only by route, setting or dose "
          "(oral, topical, intravenous, high-dose, prophylactic). Reply as JSON: {\"classes\": [numbers]}.")
    keep = []
    for b in batches(cands, 80):
        res = llm.ask("hubs: class filter", s1, "\n".join(f"{i}. {n['label']}" for i, n in enumerate(b, 1)), 400)
        keep += [b[i - 1] for i in (res or {}).get("classes", []) if isinstance(i, int) and 1 <= i <= len(b)]
    # one node per class phrase (spelling variants such as 'Sglt2 inhibitors' / 'Sglt-2 inhibitor' collapse)
    classes: dict[str, dict] = {}
    for n in keep:
        classes.setdefault(mentions.phrase_key(n["label"]), n)
    classes_l = sorted(classes.values(), key=lambda n: n["label"])
    cls_text = "\n".join(f"{i}. {n['label']}" for i, n in enumerate(classes_l, 1))
    members = sorted((n for n in agents if not NOT_A_DRUG.search(n["label"])), key=lambda n: n["label"])
    s2 = ("You are a clinical pharmacologist. Below is a numbered list of drug CLASSES, then numbered ITEMS. For each item "
          "that is a specific drug (or a narrower drug class) which belongs to one or more of the listed classes by "
          "standard pharmacology, give the class numbers. Use only the narrowest correct classes (at most 3). Omit items "
          "that are not drugs, belong to none of the classes, or are just another name for a class itself. Reply as "
          "JSON: {\"<item number>\": [class numbers]} for the items that qualify.\n\nCLASSES\n" + cls_text)
    proposed = []
    for b in batches(members, 50):
        res = llm.ask("hubs: drug class", s2, "ITEMS\n" + "\n".join(f"{i}. {n['label']}" for i, n in enumerate(b, 1)), 50 * 12)
        for k, v in (res or {}).items():
            if k.isdigit() and 1 <= int(k) <= len(b) and isinstance(v, list):
                for c in v:
                    if isinstance(c, int) and 1 <= c <= len(classes_l):
                        proposed.append((b[int(k) - 1], classes_l[c - 1]))
    # accept only when class and member share a section of the books
    secs: dict[str, dict] = {}

    def sections(label):
        if label not in secs:
            secs[label] = {r["section_id"]: r["strength"] for r in mentions.sections_for(label, k=600)}
        return secs[label]

    out, seen = [], set()
    for m, c in proposed:
        # line of therapy (first-/second-line, reserve) depends on the guideline and context: not a drug class
        if LINE_OF_THERAPY.search(c["label"]):
            continue
        if m["id"] == c["id"] or mentions.phrase_key(m["label"]) == mentions.phrase_key(c["label"]) or (m["id"], c["id"]) in seen:
            continue
        a, b = sections(m["label"]), sections(c["label"])
        common = set(a) & set(b)
        if common:
            seen.add((m["id"], c["id"]))
            best = max(common, key=lambda s: min(a[s], b[s]))
            out.append(rec(c["id"], "drug_class", c["label"], m, "T3", "LLM class + shared section", best))
    stats = {"class_candidates": len(cands), "classes_kept": len(classes_l), "proposed": len(proposed), "accepted": len(out)}
    print("drug class funnel:", stats)
    return out


# (e) condition hierarchy --------------------------------------------------
def hierarchy_hubs(nodes) -> list[dict]:
    path = ROOT / "reports/merge_proposals.csv"
    if not path.exists():
        return []
    existing = {(f["subject_id"], f["object_id"]) for f in ontology_facts.facts() if f["predicate"] == "is_a"}
    out = []
    for row in csv.DictReader(path.open(encoding="utf-8")):
        if row["kind"] != "modifier_base" or row["id_a"] not in nodes or row["id_b"] not in nodes:
            continue
        ta, tb = set(mentions.tokens(row["label_a"])), set(mentions.tokens(row["label_b"]))
        if not tb < ta or not (ta - tb) <= MODIFIERS or (row["id_a"], row["id_b"]) in existing:
            continue
        base = nodes[row["id_b"]]
        out.append(rec(f"hub:isa:{base['id']}", "condition_hierarchy", base["label"], nodes[row["id_a"]], "T3",
                       "modifier + base label (is_a candidate, not a merge)"))
    return out


# ---------------------------------------------------------------- graph effect
def graph_effect(nodes, records) -> dict:
    import networkx as nx
    facts = ontology_facts.facts()

    def measure(recs):
        g = nx.MultiGraph()
        g.add_edges_from((f["subject_id"], f["object_id"]) for f in facts)
        base_deg = {n: g.degree(n) for n in g}
        g.add_edges_from((r["hub_id"], r["member_id"]) for r in recs)
        comps = sorted((len(c) for c in nx.connected_components(g)), reverse=True)
        orig = [n for n in nodes]
        return {"nodes": g.number_of_nodes(), "components": len(comps), "largest_pct": round(100 * comps[0] / g.number_of_nodes(), 1),
                "size2_components": sum(c == 2 for c in comps),
                "leaves_original_nodes": sum(g.degree(n) == 1 for n in orig),
                "leaves_before": sum(d == 1 for d in base_deg.values())}
    return {"facts_only": measure([]), "plus_T2": measure([r for r in records if r["tier"] == "T2"]),
            "plus_T2_T3": measure(records),
            "plus_T2_T3_no_hierarchy": measure([r for r in records if r["hub_type"] != "condition_hierarchy"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-metrics", action="store_true")
    args = ap.parse_args()
    nodes = load_nodes()
    llm = Llm(args.dry_run)
    recs = organ_hubs(nodes) + mechanism_hubs(nodes) + organism_hubs(nodes, llm) + drug_class_hubs(nodes, llm) + hierarchy_hubs(nodes)
    if args.dry_run:
        print(f"dry run: uncached calls would cost at most ~${llm.pending_usd:.3f} (cap ${BUDGET_USD})")
        return
    drop = set(json.loads((ROOT / "data/graph/hubs_drop.json").read_text())) if (ROOT / "data/graph/hubs_drop.json").exists() else set()
    recs = [r for r in recs if r["hub_type"] not in drop]
    seen, uniq = set(), []
    for r in recs:
        k = (r["hub_id"], r["member_id"])
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in uniq) + "\n", encoding="utf-8")
    per = Counter(r["hub_type"] for r in uniq)
    hubs = defaultdict(set)
    for r in uniq:
        hubs[r["hub_type"]].add(r["hub_id"])
    print(f"LLM calls this run: {llm.calls}; DeepSeek spend (pessimistic estimate, cumulative): ${llm.spent:.3f}")
    for k in per:
        print(f"{k:20s} hubs={len(hubs[k]):4d} edges={per[k]:5d}  tier={uniq[[r['hub_type'] for r in uniq].index(k)]['tier']}")
    if not args.no_metrics:
        print(json.dumps(graph_effect(nodes, uniq), indent=1))


if __name__ == "__main__":
    main()
