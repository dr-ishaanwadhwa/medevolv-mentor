## 2026-11-13T08:46:56Z

Execute ontological term and relationship densification across the med-rag pipeline for production use, implementing Headings Densification (Stage A), updating the Graph Networking Pipeline, and evaluating Targeted Fact Gap-Fill under dry-run mode.

Working directory: /Users/ishaanwadhwa/Projects/med-rag
Integrity mode: development

## Requirements

### R1. Headings Densification (Stage A)
Promote heading extraction and classification logic from scratchpad scripts (`hlib.py`, `hclass.py`, `h2.py`, `h4.py`–`h7.py` in `/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/`) into `rag/headings.py` in accordance with `docs/headings_to_ontology_plan.md`. Generate `data/graph/headings.jsonl` implementing Rules 1, 3, 4, 5a, 6, and 8 (primary topic, facets, hierarchy `subtopic_of` and `part_of`, parenthetical aliases, identical cross-book headings, and case links). Implement heading evaluation in `eval/heading_metrics.py` and implement leak tests to ensure non-T1 heading records never enter `graph_block` in answers.

### R2. Graph Networking Pipeline Update
Update and execute the graph networking pipeline scripts (`scripts/build_mentions.py`, `scripts/build_hubs.py`, `scripts/build_crosswalk.py`, `scripts/build_comention.py`, `scripts/build_atlas_crosswalk.py`) per `docs/graph_networking_plan.md` to produce updated artifacts in `data/graph/` (`mentions.jsonl`, `hubs.jsonl`, `crosswalk.jsonl`, `comention.jsonl`, `atlas_crosswalk.jsonl`). Measure graph metrics before and after the pipeline update with `scripts/graph_metrics.py`.

### R3. Targeted Fact Gap-Fill Evaluation
Evaluate `ontology/gapfill.py` against `reports/gapfill_conditions.json` strictly using `--dry-run`. Review requirements, output, and token cost estimates; do not spend live LLM tokens without prior review.

### R4. Regression and Leak Testing
Ensure that all existing tests pass with `.venv/bin/pytest tests/`. Verify through automated tests that non-T1 heading records are prevented from entering `graph_block` in answers.

## Acceptance Criteria

### Headings Densification
- [ ] Logic from scratchpad scripts is promoted into `rag/headings.py` adhering to `docs/headings_to_ontology_plan.md`.
- [ ] `data/graph/headings.jsonl` is generated implementing Rules 1, 3, 4, 5a, 6, and 8.
- [ ] `eval/heading_metrics.py` is implemented and successfully reports heading metrics.
- [ ] Leak tests verify non-T1 heading records do not enter `graph_block` in answers.

### Graph Networking
- [ ] Pipeline scripts produce updated `mentions.jsonl`, `hubs.jsonl`, `crosswalk.jsonl`, `comention.jsonl`, and `atlas_crosswalk.jsonl` in `data/graph/`.
- [ ] `scripts/graph_metrics.py` is executed before and after the run and outputs comparison metrics.

### Gap-Fill & Token Safety
- [ ] `ontology/gapfill.py --dry-run` executes against `reports/gapfill_conditions.json` without errors.
- [ ] Cost and requirement review is completed before any live LLM tokens are expended.

### System Integrity
- [ ] All tests in `.venv/bin/pytest tests/` pass cleanly without regressions.
