"""Evaluation and measurement suite for textbook headings densification (Milestone 1, Stage A).

Promotes scratchpad analysis scripts (h1.py through h7.py) into an auditable evaluation tool:
- Book ToC distributions and coverage across the 7 textbooks
- Classification distribution matrix (7 books x 11 classes)
- Primary topic yield & provenance (% same-section, % same-book)
- Hard gate: Facet protection (0 generic facets promoted to entities)
- Heading hierarchy (subtopic_of, Gray's part_of candidates)
- Parenthetical aliases (abbreviations, synonyms, alias matches, merge proposals)
- Cross-book identical headings & near-duplicates
- Gray's clinical cases link yield
- Hard gate: Non-T1 leak verification

Writes structured results to `reports/heading_metrics.json`.
"""
from __future__ import annotations

import ast
import collections
import json
from pathlib import Path
import re
import sys
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ontology.merge import merge_key
from rag import headings, ontology_facts as o

REPORT_PATH = Path("reports/heading_metrics.json")
GENERIC_STOP = {
    "disease", "diseases", "disorder", "disorders", "of", "the", "and", "in",
    "syndrome", "syndromes", "infection", "infections", "acute", "chronic",
}


def _token_set(h: str) -> frozenset[str]:
    clean_h = re.sub(r"\([^)]*\)", "", h)
    return frozenset(w for w in merge_key(clean_h).split() if w not in GENERIC_STOP)


def compute_metrics() -> dict[str, Any]:
    """Compute all evaluation metrics across headings, ontology, and books."""
    # Ensure headings are built
    all_recs = headings.all_headings()
    if not all_recs:
        headings.build_headings()
        all_recs = headings.all_headings()

    # 1. Book Distribution
    book_dist: dict[str, dict[str, Any]] = {}
    for b in headings.BOOKS:
        b_recs = [r for r in all_recs if r["book"] == b]
        sections = sum(1 for r in b_recs if r.get("is_section"))
        distinct_clean = len({r["clean"] for r in b_recs})
        distinct_keys = len({merge_key(r["clean"]) for r in b_recs})
        levels = collections.Counter(r["level"] for r in b_recs)
        book_dist[b] = {
            "total_nodes": len(b_recs),
            "sections": sections,
            "distinct_clean_strings": distinct_clean,
            "distinct_clean_keys": distinct_keys,
            "levels": dict(sorted(levels.items())),
        }

    # 2. Classification Matrix (All nodes and Leaf sections)
    class_all: dict[str, dict[str, int]] = collections.defaultdict(lambda: collections.defaultdict(int))
    class_leaf: dict[str, dict[str, int]] = collections.defaultdict(lambda: collections.defaultdict(int))
    for r in all_recs:
        b = r["book"]
        c = r["class"]
        class_all[b][c] += 1
        if r.get("is_section"):
            class_leaf[b][c] += 1

    totals_all = collections.Counter(r["class"] for r in all_recs)
    totals_leaf = collections.Counter(r["class"] for r in all_recs if r.get("is_section"))

    # 3. Primary Topic Provenance Check
    esec: dict[str, set[str]] = collections.defaultdict(set)
    for f in o.facts():
        for s in ("subject", "object"):
            for p in o.sources(f):
                esec[merge_key(f[s + "_label"])].add(p["section_id"])

    secs_with_fact = {p["section_id"] for f in o.facts() for p in o.sources(f)}
    by_book_facts = collections.Counter(s.split("/")[0] for s in secs_with_fact)

    leaf_matched = [r for r in all_recs if r["class"] == "matched" and r.get("is_section")]
    chk_provenance = collections.Counter()
    no_same_book: list[dict[str, str]] = []
    for r in leaf_matched:
        k = merge_key(r["clean"])
        main, par = headings.paren_split(r["clean"])
        keys = [k, merge_key(main)] + [merge_key(x) for a in par for x in re.split(r"[;,]", a)]
        provenance_secs = set().union(*[esec.get(x, set()) for x in keys if x])
        same_sec = r["section_id"] in provenance_secs
        same_book = any(s.split("/")[0] == r["book"] for s in provenance_secs)
        chk_provenance["n"] += 1
        chk_provenance["same_section"] += int(same_sec)
        chk_provenance["same_book"] += int(same_book)
        if not same_book:
            no_same_book.append({"book": r["book"], "clean": r["clean"], "section_id": r["section_id"]})

    # Single-word generic headings check
    single_word_non_tripathi = [
        r["clean"] for r in all_recs
        if r["class"] == "matched" and len(r["clean"].split()) == 1 and r["book"] != "tripathi"
    ]
    bridge_count = sum(1 for r in all_recs if r.get("method") == "rule1:heading-bridge")

    # Relaxed matches check
    relaxed_matches: list[dict[str, Any]] = []
    for r in all_recs:
        if r["class"] in ("entity", "group", "topic", "group_class"):
            m, t, cands = headings.relaxed_match(r["clean"])
            if m:
                relaxed_matches.append({
                    "heading_id": r["heading_id"],
                    "book": r["book"],
                    "clean": r["clean"],
                    "class": r["class"],
                    "types": sorted(t),
                })

    # 4. Facet Protection Gate (Hard Gate)
    facets = [r for r in all_recs if r["class"] == "facet"]
    distinct_facet_strings = {r["clean"].lower() for r in facets}
    generic_promoted_to_entities = [
        r for r in all_recs
        if r["clean"].lower() in headings.FACET_EXACT and r["class"] in ("matched", "entity")
    ]
    gate_probes = {}
    for word in ("Joints", "Nerves", "Arteries", "Toxicity"):
        matches_found = [r for r in all_recs if r["clean"].lower() == word.lower()]
        gate_probes[word] = {
            "count": len(matches_found),
            "classes": sorted({r["class"] for r in matches_found}),
            "all_facet": all(r["class"] == "facet" for r in matches_found),
            "has_concept_ids": any(bool(r.get("concept_ids")) for r in matches_found),
        }

    # 5. Hierarchy Edges
    tree_edges = collections.Counter()
    tree_edges_non_facet = collections.Counter()
    for r in all_recs:
        if r["level"] >= 2:
            tree_edges[r["book"]] += 1
            if r["class"] not in ("facet", "structural", "positional"):
                tree_edges_non_facet[r["book"]] += 1

    part_of_candidates = headings.part_of_candidates("grays")

    # 6. Parenthetical Aliases
    aliases = headings.parenthetical_aliases()
    abbrevs = [a for a in aliases if a["abbreviations"]]
    syns = [a for a in aliases if a["synonyms"]]
    alias_only_matches = [a for a in aliases if a["alias_only_match"]]
    merge_proposals = [a for a in aliases if a["merge_proposal"]]

    # 7. Cross-Book Headings
    cross_books = headings.cross_book_headings()
    cross_books_matched = [c for c in cross_books if c["in_ontology"]]

    # Near duplicates (token-set equality)
    by_token_set: dict[frozenset[str], dict[str, list[dict]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in all_recs:
        if r["level"] < 1 or r["class"] in ("facet", "structural", "case_bare", "positional", "procedural", "group"):
            continue
        tset = _token_set(r["clean"])
        if tset:
            by_token_set[tset][r["book"]].append(r)
    near_duplicates = [
        {"tokens": sorted(tset), "books": sorted(bmap.keys()), "headings": [x["clean"] for b in bmap for x in bmap[b]]}
        for tset, bmap in by_token_set.items() if len(bmap) >= 2
    ]

    # 8. Gray's Clinical Cases
    grays_cases = [r for r in all_recs if r["book"] == "grays" and headings.CASE.match(r["clean"])]
    grays_case_conds = [r for r in all_recs if r["class"] == "case_cond"]
    grays_case_matched = [r for r in grays_case_conds if r.get("concept_ids")]

    # 9. Non-T1 Leak Verification Gate
    tiers = collections.Counter(r["tier"] for r in all_recs)
    t1_records_in_headings = tiers.get("T1", 0)

    # Check clinical_ontology.jsonl for contamination
    ont_file = Path("data/ontology/clinical_ontology.jsonl")
    ont_heading_records = 0
    if ont_file.exists():
        for line in ont_file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                f = json.loads(line)
                if f.get("source") == "heading" or "heading" in str(f.get("rule", "")):
                    ont_heading_records += 1

    # Check AST isolation of hops.py and answer.py
    ast_hops_clean = True
    ast_answer_clean = True
    hops_file = Path("rag/hops.py")
    if hops_file.exists():
        tree = ast.parse(hops_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "headings" in alias.name:
                        ast_hops_clean = False
            elif isinstance(node, ast.ImportFrom):
                if node.module and "headings" in node.module:
                    ast_hops_clean = False

    ans_file = Path("rag/answer.py")
    if ans_file.exists():
        tree = ast.parse(ans_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "headings" in alias.name:
                        ast_answer_clean = False
            elif isinstance(node, ast.ImportFrom):
                if node.module and "headings" in node.module:
                    ast_answer_clean = False

    report = {
        "summary": {
            "total_tree_nodes": len(all_recs),
            "total_section_leaves": sum(1 for r in all_recs if r.get("is_section")),
            "distinct_clean_keys": len({merge_key(r["clean"]) for r in all_recs if r["level"] >= 1}),
        },
        "book_distribution": book_dist,
        "classification_totals": {
            "all_nodes": dict(totals_all),
            "leaf_sections": dict(totals_leaf),
        },
        "classification_by_book": {
            "all_nodes": {b: dict(class_all[b]) for b in headings.BOOKS},
            "leaf_sections": {b: dict(class_leaf[b]) for b in headings.BOOKS},
        },
        "primary_topic": {
            "strict_matched_total": totals_all.get("matched", 0),
            "strict_matched_leaves": totals_leaf.get("matched", 0),
            "strict_matched_leaf_share": round(totals_leaf.get("matched", 0) / 2675, 4),
            "relaxed_matches_count": len(relaxed_matches),
            "provenance_checked": dict(chk_provenance),
            "same_section_pct": round(chk_provenance["same_section"] / max(chk_provenance["n"], 1), 4),
            "same_book_pct": round(chk_provenance["same_book"] / max(chk_provenance["n"], 1), 4),
            "single_word_non_tripathi_matched": len(single_word_non_tripathi),
            "single_word_bridges": bridge_count,
            "sections_with_certified_fact": len(secs_with_fact),
            "sections_with_fact_by_book": dict(by_book_facts),
        },
        "facet_protection_gate": {
            "total_facet_headings": len(facets),
            "distinct_facet_strings": len(distinct_facet_strings),
            "generic_promoted_to_entities": len(generic_promoted_to_entities),
            "status": "PASSED" if len(generic_promoted_to_entities) == 0 else "FAILED",
            "probe_words": gate_probes,
        },
        "hierarchy": {
            "total_tree_edges": sum(tree_edges.values()),
            "non_facet_subtopic_edges": sum(tree_edges_non_facet.values()),
            "tree_edges_by_book": dict(tree_edges),
            "non_facet_edges_by_book": dict(tree_edges_non_facet),
            "grays_part_of_candidates": len(part_of_candidates),
        },
        "parenthetical_aliases": {
            "total_parenthetical_headings": len(aliases),
            "abbreviations_count": len(abbrevs),
            "synonym_lists_count": len(syns),
            "alias_only_matches": len(alias_only_matches),
            "merge_proposals_count": len(merge_proposals),
        },
        "cross_book_headings": {
            "identical_key_cross_book_count": len(cross_books),
            "matched_in_ontology": len(cross_books_matched),
            "new_cross_book_concepts": len(cross_books) - len(cross_books_matched),
            "near_duplicates_count": len(near_duplicates),
        },
        "case_links": {
            "total_grays_cases": len(grays_cases),
            "named_condition_cases": len(grays_case_conds),
            "matched_to_ontology": len(grays_case_matched),
            "match_rate": round(len(grays_case_matched) / max(len(grays_case_conds), 1), 4),
        },
        "leak_gate": {
            "tier_distribution": dict(tiers),
            "t1_records_in_headings": t1_records_in_headings,
            "ontology_file_heading_contamination": ont_heading_records,
            "ast_hops_isolation": ast_hops_clean,
            "ast_answer_isolation": ast_answer_clean,
            "gate_passed": (
                t1_records_in_headings == 0
                and ont_heading_records == 0
                and ast_hops_clean
                and ast_answer_clean
            ),
        },
    }
    return report


def print_report(m: dict[str, Any]) -> None:
    """Print formatted summary metrics to stdout."""
    print("=" * 80)
    print("TEXTBOOK HEADINGS DENSIFICATION (STAGE A) METRICS REPORT")
    print("=" * 80)
    print(f"Total ToC Nodes Processed: {m['summary']['total_tree_nodes']:,}")
    print(f"Total Section Leaves:     {m['summary']['total_section_leaves']:,}")
    print(f"Distinct Clean Keys:      {m['summary']['distinct_clean_keys']:,}\n")

    print("-" * 80)
    print("1. BOOK COVERAGE AND DISTRIBUTION")
    print("-" * 80)
    print(f"{'Book':12s} {'Nodes':8s} {'Sections':10s} {'Clean Strings':15s} {'Clean Keys':12s}")
    for b, d in m["book_distribution"].items():
        print(f"{b:12s} {d['total_nodes']:<8d} {d['sections']:<10d} {d['distinct_clean_strings']:<15d} {d['distinct_clean_keys']:<12d}")

    print("\n" + "-" * 80)
    print("2. CLASSIFICATION BREAKDOWN")
    print("-" * 80)
    print(f"{'Class':15s} {'All Nodes':12s} {'Share':8s} {'Leaf Sections':15s} {'Share':8s}")
    tot_all = m["summary"]["total_tree_nodes"]
    tot_leaf = m["summary"]["total_section_leaves"]
    for c, cnt in sorted(m["classification_totals"]["all_nodes"].items(), key=lambda x: -x[1]):
        l_cnt = m["classification_totals"]["leaf_sections"].get(c, 0)
        print(f"{c:15s} {cnt:<12d} {cnt / tot_all:6.1%}   {l_cnt:<15d} {l_cnt / tot_leaf:6.1%}")

    print("\n" + "-" * 80)
    print("3. PRIMARY TOPIC YIELD (RULE 1)")
    print("-" * 80)
    pt = m["primary_topic"]
    print(f"Strict matches (All Nodes):   {pt['strict_matched_total']} ({pt['strict_matched_total'] / tot_all:.1%})")
    print(f"Strict matches (Leaf Secs):   {pt['strict_matched_leaves']} ({pt['strict_matched_leaf_share']:.1%})")
    print(f"Relaxed matches (Rule 1 add): {pt['relaxed_matches_count']}")
    print(f"Single-word non-Tripathi:     {pt['single_word_non_tripathi_matched']}")
    print(f"Single-word bridges flagged:  {pt['single_word_bridges']}")
    print("Leaf provenance verification:")
    print(f"  - Same-section certified fact: {pt['provenance_checked']['same_section']} / {pt['provenance_checked']['n']} ({pt['same_section_pct']:.1%})")
    print(f"  - Same-book certified fact:    {pt['provenance_checked']['same_book']} / {pt['provenance_checked']['n']} ({pt['same_book_pct']:.1%})")

    print("\n" + "-" * 80)
    print("4. FACET PROTECTION HARD GATE (RULE 3)")
    print("-" * 80)
    fpg = m["facet_protection_gate"]
    print(f"Total Generic Facets:         {fpg['total_facet_headings']}")
    print(f"Distinct Facet Strings:       {fpg['distinct_facet_strings']}")
    print(f"Generic Promoted to Entities: {fpg['generic_promoted_to_entities']} (HARD GATE: 0 required)")
    print(f"Gate Status:                  {fpg['status']}")
    print("Critical Probe Check:")
    for w, p in fpg["probe_words"].items():
        print(f"  - {w:10s}: count={p['count']}, classes={p['classes']}, concept_ids_present={p['has_concept_ids']}")

    print("\n" + "-" * 80)
    print("5. HIERARCHY EDGES & CANDIDATES (RULE 4)")
    print("-" * 80)
    h = m["hierarchy"]
    print(f"Total Tree Parent->Child Steps:  {h['total_tree_edges']}")
    print(f"Non-facet subtopic_of Edges:     {h['non_facet_subtopic_edges']}")
    print(f"Gray's part_of Candidates (T3):  {h['grays_part_of_candidates']}")

    print("\n" + "-" * 80)
    print("6. PARENTHETICAL ALIASES & MERGES (RULE 5A)")
    print("-" * 80)
    pa = m["parenthetical_aliases"]
    print(f"Headings with Parentheses:       {pa['total_parenthetical_headings']}")
    print(f"Parsed Abbreviations:            {pa['abbreviations_count']}")
    print(f"Parsed Synonym Lists:            {pa['synonym_lists_count']}")
    print(f"Alias-only Matches to Ontology:  {pa['alias_only_matches']}")
    print(f"Merge Proposals:                 {pa['merge_proposals_count']}")

    print("\n" + "-" * 80)
    print("7. CROSS-BOOK IDENTICAL HEADINGS (RULE 6)")
    print("-" * 80)
    cb = m["cross_book_headings"]
    print(f"Identical Headings (>=2 books):  {cb['identical_key_cross_book_count']}")
    print(f"Already in Certified Ontology:   {cb['matched_in_ontology']}")
    print(f"Newly Discovered Cross-Book:     {cb['new_cross_book_concepts']}")
    print(f"Near-Duplicate Groups:           {cb['near_duplicates_count']}")

    print("\n" + "-" * 80)
    print("8. GRAY'S CLINICAL CASES (RULE 8)")
    print("-" * 80)
    cl = m["case_links"]
    print(f"Total Case Sections:             {cl['total_grays_cases']}")
    print(f"Named Condition Cases:           {cl['named_condition_cases']}")
    print(f"Conditions Matched to Ontology:  {cl['matched_to_ontology']} ({cl['match_rate']:.1%})")

    print("\n" + "-" * 80)
    print("9. LEAK PREVENTION VERIFICATION GATE")
    print("-" * 80)
    lg = m["leak_gate"]
    print(f"Tiers on headings.jsonl:         {lg['tier_distribution']}")
    print(f"T1 Records in headings.jsonl:    {lg['t1_records_in_headings']} (HARD GATE: 0 required)")
    print(f"Heading Contamination in Ont:    {lg['ontology_file_heading_contamination']} (HARD GATE: 0 required)")
    print(f"AST hops.py Isolation Clean:     {lg['ast_hops_isolation']}")
    print(f"AST answer.py Isolation Clean:   {lg['ast_answer_isolation']}")
    print(f"Leak Gate Overall Result:        {'PASSED' if lg['gate_passed'] else 'FAILED'}")
    print("=" * 80)


def main() -> int:
    metrics = compute_metrics()
    print_report(metrics)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    print(f"\nWritten structured report to {REPORT_PATH}")
    return 0 if metrics["leak_gate"]["gate_passed"] and metrics["facet_protection_gate"]["status"] == "PASSED" else 1


if __name__ == "__main__":
    sys.exit(main())
