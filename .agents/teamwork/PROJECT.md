# Project: med-rag Ontological Term and Relationship Densification

## Architecture
The med-rag system provides high-precision clinical question answering by combining text retrieval across 7 medical textbooks with a certified clinical ontology knowledge graph. This project densifies ontological terms, navigational hierarchies, entity relationships, and crosswalks:
- **Headings Layer (`rag/headings.py`, `data/graph/headings.jsonl`)**: Extracts, cleans, and classifies 3,135 ToC nodes across 7 textbooks into primary topics, facets, subtopic hierarchies, Gray's part-of anatomy candidates, parenthetical aliases, identical cross-book headings, and case condition links. Operates at T2/T3/navigation tiers; strictly isolated from `graph_block` in answer generation.
- **Graph Networking Layer (`scripts/build_*.py`, `data/graph/`)**: Mentions index (285k links), Hubs (6 types, 7,923 edges, elevating giant component to 98.4%), BODHI Crosswalk (13,824 mappings), Co-mentions (24,644 paragraph PMI pairs), and 3D Human Atlas Crosswalk (3,470 records). Measured before and after via `scripts/graph_metrics.py`.
- **Targeted Fact Gap-Fill (`ontology/gapfill.py`)**: Evaluates 100 clinical conditions from `reports/gapfill_conditions.json` strictly in `--dry-run` mode to verify execution and zero token spend ($0.00 cached, $0.64 uncached ceiling).
- **Regression and Non-T1 Leak Testing (`tests/test_headings_leak.py`)**: 5-barrier automated verification ensuring non-T1 heading records never enter `graph_block` in answers, and all 143 existing tests pass with 0 regressions.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Rule 3: Facet Filtering | Filter 91 generic structural facet strings before entity matching to prevent false-positive ontology links | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 2 | Rule 1: Primary Topic Linking | Strict + relaxed matching of ToC heading leaves to certified ontology nodes with book-expected type disambiguation | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 3 | Rule 4: Hierarchy Extraction | Extract parent-child `subtopic_of` steps and Gray's `part_of` anatomy candidates | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 4 | Rule 5a: Parenthetical Aliases | Parse abbreviations and synonyms from headings, linking unmatched concepts and proposing merges | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 5 | Rule 6: Identical Cross-Book Headings | Detect identical heading keys across 2+ books to form cross-book concept clusters | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 6 | Rule 8: Gray's Case Links | Match clinical case conditions to ontology nodes (`illustrated_by`) | M1 | Survey / `docs/headings_to_ontology_plan.md` |
| 7 | Headings Module & Data Artifact | Promote scratchpad logic into `rag/headings.py` and generate `data/graph/headings.jsonl` | M1 | Survey / R1 Requirement |
| 8 | Headings Evaluation Tool | Promote scratchpad metrics into `eval/heading_metrics.py` and output `reports/heading_metrics.json` | M1 | Survey / R1 Requirement |
| 9 | Non-T1 Automated Leak Prevention | 5-barrier test in `tests/test_headings_leak.py` verifying non-T1 heading records never enter `graph_block` | M1 | Survey / R1 & R4 Requirement |
| 10 | Baseline Graph Metrics | Execute `scripts/graph_metrics.py` to record pre-update baseline and generate `reports/merge_proposals.csv` | M2 | Survey / R2 Requirement |
| 11 | Mentions Build | Execute `scripts/build_mentions.py` to generate `data/graph/mentions.jsonl`, `by_section.jsonl`, `meta.json` | M2 | Survey / R2 Requirement |
| 12 | Hubs Build | Execute `scripts/build_hubs.py` to generate `data/graph/hubs.jsonl` across 6 hub types | M2 | Survey / R2 Requirement |
| 13 | BODHI Crosswalk Build | Execute `scripts/build_crosswalk.py` to generate `data/graph/crosswalk.jsonl` and metadata | M2 | Survey / R2 Requirement |
| 14 | Co-mention Build | Execute `scripts/build_comention.py` to generate `data/graph/comention.jsonl` | M2 | Survey / R2 Requirement |
| 15 | Atlas Crosswalk Build | Execute `scripts/build_atlas_crosswalk.py` to generate `data/graph/atlas_crosswalk.jsonl` | M2 | Survey / R2 Requirement |
| 16 | Post-update Graph Metrics | Re-run `scripts/graph_metrics.py` and compare before/after connectivity and coverage metrics | M2 | Survey / R2 Requirement |
| 17 | Gap-Fill Dry-Run Execution | Execute `ontology/gapfill.py --dry-run` on `reports/gapfill_conditions.json` without errors | M3 | Survey / R3 Requirement |
| 18 | Token & Cost Review | Document token cost calculation, existing cache verification ($0.00), and budget safety guardrails | M3 | Survey / R3 Requirement |
| 19 | Full Pytest Regression Suite | Run `.venv/bin/pytest tests/` ensuring all existing tests (143) pass cleanly without regressions | M4 | Survey / R4 Requirement |
| 20 | End-to-End System Integration Verification | Verify all generated artifacts exist in `data/graph/` and satisfy integrity requirements | M4 | Survey / Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Headings Densification (Stage A) & Leak Prevention | Implement `rag/headings.py`, generate `data/graph/headings.jsonl` (Rules 1, 3, 4, 5a, 6, 8), implement `eval/heading_metrics.py`, implement `tests/test_headings_leak.py` | none | PLANNED |
| M2 | Graph Networking Pipeline & Metrics | Execute baseline `graph_metrics.py`, execute pipeline scripts (`build_mentions`, `build_hubs`, `build_crosswalk`, `build_comention`, `build_atlas_crosswalk`), re-execute `graph_metrics.py` | none | PLANNED |
| M3 | Targeted Fact Gap-Fill Dry-Run & Cost Review | Execute `ontology/gapfill.py --dry-run` against `reports/gapfill_conditions.json`, generate review report, verify zero LLM spend | none | PLANNED |
| M4 | Final Regression & Leak Verification | Execute full test suite `.venv/bin/pytest tests/`, verify 100% pass, verify zero non-T1 leaks, verify artifact integrity | M1, M2, M3 | PLANNED |

## Interface Contracts
### `rag/headings.py` Public Interface
- `primary_topic(section_id: str) -> dict | None`: Returns primary topic dictionary for given section leaf.
- `section_heading(section_id: str) -> dict | None`: Returns heading record for section.
- `headings_for_concept(concept_id: str) -> list[dict]`: All headings linked to a concept.
- `facets_for(heading_id: str) -> list[dict]`: Child facet headings attached to parent.
- `subtopics(heading_id: str) -> list[dict]`: Child headings in ToC outline.
- `part_of_candidates(book: str = "grays") -> list[dict]`: Gray's anatomy part-of candidates.
- `parenthetical_aliases() -> list[dict]`: Parsed abbreviations and synonyms.
- `cross_book_headings() -> list[dict]`: Identical headings across 2+ books.
- `all_headings(book: str | None = None, cls: str | None = None) -> list[dict]`: All loaded headings.
- `build_headings(output_path: Path | str = "data/graph/headings.jsonl") -> list[dict]`: Generates headings jsonl.

### Non-T1 Boundary Contract (`rag/headings.py` <-> `rag/answer.py`, `rag/hops.py`)
- `data/graph/headings.jsonl` contains exclusively records with `tier in ("T2", "T3", "navigation")`.
- `data/ontology/clinical_ontology.jsonl` is NEVER touched or modified by headings logic.
- `rag/hops.py` and `rag/answer.py` do NOT import `rag.headings`.
- `p.graph_facts` and answer `graph_block` contain 0 records from `headings.jsonl`.

## Code Layout
- `rag/headings.py`: Core headings loader, classifier, and builder module.
- `eval/heading_metrics.py`: Heading metrics evaluation tool.
- `tests/test_headings_leak.py`: 5-barrier automated non-T1 leak test suite.
- `data/graph/headings.jsonl`: Generated headings data artifact.
- `data/graph/mentions.jsonl`, `by_section.jsonl`, `meta.json`: Mentions index artifacts.
- `data/graph/hubs.jsonl`: Hub edges artifact.
- `data/graph/crosswalk.jsonl`, `crosswalk_meta.json`: BODHI crosswalk artifacts.
- `data/graph/comention.jsonl`: Statistical co-mention artifact.
- `data/graph/atlas_crosswalk.jsonl`: 3D Human Atlas crosswalk artifact.
- `reports/heading_metrics.json`: Evaluated heading metrics report.
- `reports/merge_proposals.csv`: Generated merge proposals.
- `reports/graph_metrics_<date>.json`: Before and after graph connectivity metrics reports.
