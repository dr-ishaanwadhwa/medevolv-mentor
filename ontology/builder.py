"""CLI Orchestrator for Medical Ontology Extraction and Compilation.

Usage:
  python -m ontology.builder --high-yield             # Run core clinical benchmark sections
  python -m ontology.builder --book tripathi --limit 10
  python -m ontology.builder --book all --limit 5
  python -m ontology.builder --section data/okf/harrison/sections/436-436-seizures-and-epilepsy.md
  python -m ontology.builder --stats                  # Print compiled ontology statistics
"""
from __future__ import annotations

import argparse
import glob
import logging
from pathlib import Path

from ontology.compiler import (
    ONTOLOGY_FILE,
    build_ontology_graph,
    load_compiled_facts,
    save_compiled_facts,
)
from concurrent.futures import ThreadPoolExecutor, as_completed

from ontology.extractor import cache_file_for, extract_from_section, parse_okf_section
from ontology.reconciler import reconcile_section_facts
from ontology.schema import ProvenancedOntologyFact

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ontology.builder")

# High-yield benchmark sections targeting our 15 clinical gold cases
HIGH_YIELD_SECTIONS = [
    # 1. Epilepsy, Seizures, and Status Epilepticus
    "data/okf/tripathi/sections/0178-30-antiepileptic-drugs-treatment-of-epilepsies.md",
    "data/okf/tripathi/sections/0176-30-antiepileptic-drugs-valproic-acid-sodium-valproate.md",
    "data/okf/tripathi/sections/0174-30-antiepileptic-drugs-phenytoin-diphenylhydantoin.md",
    "data/okf/davidson/sections/257-epilepsy.md",
    "data/okf/harrison/sections/436-436-seizures-and-epilepsy.md",

    # 2. Dengue & Viral Hemorrhagic Fevers
    "data/okf/micro/sections/034-34-viral-hemorrhagic-fever-vhf-arboviral-vhf-dengue-chikungu.md",
    "data/okf/harrison/sections/215-215-arthropod-borne-and-rodent-borne-virus-infections.md",
    "data/okf/davidson/sections/075-presenting-problems-in-infectious-diseases.md",

    # 3. Enteric Fever / Typhoid
    "data/okf/micro/sections/030-30-enteric-fever-salmonella-typhi-and-salmonella-paratyphi.md",
    "data/okf/harrison/sections/171-171-salmonellosis.md",

    # 4. Tuberculosis & MDR-TB
    "data/okf/micro/sections/063-63-tuberculosis-and-nontuberculous-mycobacteria-infections.md",
    "data/okf/harrison/sections/183-183-tuberculosis.md",
    "data/okf/tripathi/sections/0348-55-antitubercular-drugs-overview.md",
    "data/okf/tripathi/sections/0349-55-antitubercular-drugs-isoniazid-isonicotinic-acid-hy.md",
    "data/okf/tripathi/sections/0350-55-antitubercular-drugs-rifampin-rifampicin-r.md",

    # 5. Diabetic Ketoacidosis & Hyperglycemic Crises
    "data/okf/davidson/sections/181-presenting-problems-in-diabetes-mellitus.md",
    "data/okf/harrison/sections/416-416-diabetes-mellitus-management-and-therapies.md",
    "data/okf/harrison/sections/417-417-diabetes-mellitus-complications.md",

    # 6. Acute Coronary Syndrome & Myocardial Infarction
    "data/okf/harrison/sections/286-286-st-segment-elevation-myocardial-infarction.md",
    "data/okf/robbins/sections/030-infarction.md",
]


def print_stats() -> None:
    """Print current compiled ontology metrics."""
    facts = load_compiled_facts()
    if not facts:
        print(f"No compiled ontology found at {ONTOLOGY_FILE}. Run extraction first.")
        return

    g = build_ontology_graph(facts)
    print("\n" + "=" * 60)
    print(f"MEDEVOLV MEDICAL ONTOLOGY STATISTICS")
    print("=" * 60)
    print(f"Total Certified Facts: {len(facts)}")
    print(f"Unique Graph Nodes:    {g.number_of_nodes()}")
    print(f"Unique Graph Edges:    {g.number_of_edges()}")

    # Count by predicate
    pred_counts: dict[str, int] = {}
    lot_counts: dict[str, int] = {}
    sev_counts: dict[str, int] = {}
    for f in facts:
        pred_counts[f.predicate.value] = pred_counts.get(f.predicate.value, 0) + 1
        if f.clinical_facets.line_of_therapy:
            lot_counts[f.clinical_facets.line_of_therapy.value] = lot_counts.get(f.clinical_facets.line_of_therapy.value, 0) + 1
        if f.clinical_facets.contraindication_severity:
            sev_counts[f.clinical_facets.contraindication_severity.value] = sev_counts.get(f.clinical_facets.contraindication_severity.value, 0) + 1

    print("\nFacts by Clinical Predicate:")
    for pred, count in sorted(pred_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {pred:<25} {count:>5}")

    print("\nTherapy Classifications:")
    for lot, count in sorted(lot_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  • {lot:<25} {count:>5}")

    if sev_counts:
        print("\nContraindication Warnings:")
        for sev, count in sorted(sev_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  • [WARNING] {sev:<15} {count:>5}")
    print("=" * 60 + "\n")


def process_section_paths(paths: list[Path], force: bool = False, rebuild: bool = False, workers: int = 1) -> None:
    """Process OKF section files and update the compiled ontology. rebuild=True starts from an empty file
    (uses the extraction cache, so no LLM calls for cached sections) so stale facts don't survive."""
    existing_facts = [] if rebuild else load_compiled_facts()
    facts_dict: dict[str, ProvenancedOntologyFact] = {f.id: f for f in existing_facts}
    stats: dict = {}

    new_count = 0
    paths = [p for p in paths if p.exists() or logger.warning("Path does not exist: %s", p)]
    total = len(paths)
    # 1) extraction: the slow, LLM-bound part, in parallel threads inside this one process
    results: dict[Path, object] = {}
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {pool.submit(extract_from_section, p, force): p for p in paths}
        for i, fut in enumerate(as_completed(futures), 1):
            p = futures[fut]
            try:
                results[p] = fut.result()
            except Exception as e:                       # one bad section must not stop the run
                logger.error("Extraction crashed for %s: %s", p, e)
            logger.info("[%d/%d] extracted %s", i, total, p.name)
    failed = [p for p in paths if not cache_file_for(p).exists()]
    if failed:
        Path("reports").mkdir(exist_ok=True)
        Path("reports/ontology_failed.txt").write_text("\n".join(str(p) for p in failed) + "\n")
        logger.warning("%d section(s) failed (not cached; rerun to retry): see reports/ontology_failed.txt", len(failed))
    # 2) reconciliation: sequential (the registry is not built for threads)
    for path in paths:
        if path not in results:
            continue
        meta, body = parse_okf_section(path)
        extraction_res = results[path]
        reconciled = reconcile_section_facts(extraction_res, meta, source_text=body, stats=stats)
        for f in reconciled:
            if f.id not in facts_dict:
                new_count += 1
            facts_dict[f.id] = f

    # targeted gap-fill extractions (ontology/gapfill.py) are kept on rebuild, from their cache
    from ontology.gapfill import reconcile_cached
    for f in reconcile_cached(stats):
        facts_dict.setdefault(f.id, f)

    save_compiled_facts(list(facts_dict.values()), merge_report=Path("reports/ontology_merges.tsv"))
    logger.info("Reconciliation: %s", ", ".join(f"{k}={v}" for k, v in sorted(stats.items())))
    logger.info("Done! Added/updated %d facts. Total compiled facts: %d", new_count, len(facts_dict))
    print_stats()


def main() -> None:
    parser = argparse.ArgumentParser(description="MedEvolv Clinical Ontology Builder")
    parser.add_argument("--high-yield", action="store_true", help="Process high-yield benchmark sections")
    parser.add_argument("--book", type=str, choices=["tripathi", "harrison", "davidson", "guyton", "robbins", "micro", "all"], help="Process sections for a book")
    parser.add_argument("--section", type=str, help="Process a single section path")
    parser.add_argument("--limit", type=int, default=10, help="Max sections to process when --book is passed")
    parser.add_argument("--force", action="store_true", help="Force re-extraction ignoring disk cache")
    parser.add_argument("--stats", action="store_true", help="Print ontology stats and exit")
    parser.add_argument("--rebuild", action="store_true", help="Start from an empty compiled file (uses cache)")
    parser.add_argument("--sections-file", type=str, help="Text file with one section path per line "
                        "(e.g. reports/ontology_ranking.top.txt); combine with --high-yield to include the pilot")
    parser.add_argument("--workers", type=int, default=1, help="Parallel LLM extraction threads (one process)")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    if args.sections_file:
        listed = [l.strip() for l in Path(args.sections_file).read_text().splitlines() if l.strip()]
        wanted = list(dict.fromkeys((HIGH_YIELD_SECTIONS if args.high_yield else []) + listed))
        logger.info("Processing %d sections (%s%d from %s)", len(wanted),
                    f"{len(HIGH_YIELD_SECTIONS)} pilot + " if args.high_yield else "", len(listed), args.sections_file)
        process_section_paths([Path(p) for p in wanted], force=args.force, rebuild=args.rebuild, workers=args.workers)
        return

    if args.high_yield:
        paths = [Path(p) for p in HIGH_YIELD_SECTIONS if Path(p).exists()]
        logger.info("Running high-yield pilot over %d verified sections...", len(paths))
        process_section_paths(paths, force=args.force, rebuild=args.rebuild, workers=args.workers)
        return

    if args.section:
        process_section_paths([Path(args.section)], force=args.force, rebuild=args.rebuild, workers=args.workers)
        return

    if args.book:
        if args.book == "all":
            all_files = sorted(glob.glob("data/okf/*/sections/*.md"))
            paths = [Path(p) for p in all_files[:args.limit]]
        else:
            book_files = sorted(glob.glob(f"data/okf/{args.book}/sections/*.md"))
            paths = [Path(p) for p in book_files[:args.limit]]
        logger.info("Processing %d sections for book '%s'...", len(paths), args.book)
        process_section_paths(paths, force=args.force, rebuild=args.rebuild, workers=args.workers)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
