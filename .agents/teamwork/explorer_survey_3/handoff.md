# Handoff Report: R3 (Targeted Fact Gap-Fill Dry-Run) & R4 (Regression and Leak Testing)

## 1. Observation

### 1.1 `ontology/gapfill.py` CLI Arguments, Execution Flow & Cost Logic
- **File location**: `ontology/gapfill.py` (211 lines).
- **CLI Arguments** (`ontology/gapfill.py:183-189`):
  - `--conditions`: path to JSON conditions file (required).
  - `--limit`: integer, limits evaluation to first N conditions.
  - `--workers`: integer, thread pool size (default: 6).
  - `--dry-run`: boolean flag (`action="store_true"`).
  - `--max-usd`: float, budget cap guardrail (default: 3.0).
- **Dry-run flow** (`ontology/gapfill.py:190-195`):
  ```python
  conds = json.loads(Path(a.conditions).read_text())[: a.limit]
  js = jobs(conds)
  est = estimate([j for j in js if not _key(j[0], j[2], j[3]).exists()])
  print(json.dumps({"conditions": len(conds), "jobs": len(js), "to_run": est}))
  if a.dry_run:
      return
  ```
  `_extract(job, spend)` (lines 117-149) imports `from rag.backends import chat`. Because `a.dry_run` executes `return` immediately after printing the estimation JSON (line 195), `_extract`, `ThreadPoolExecutor`, and `chat` are never invoked or imported.
- **Budget Guardrail** (`ontology/gapfill.py:196-197`):
  ```python
  if est["usd"] > a.max_usd:
      raise SystemExit(f"estimated ${est['usd']} exceeds --max-usd {a.max_usd}; not running")
  ```
- **Token Estimation Formula** (`ontology/gapfill.py:35, 173-178`):
  - Pricing constants: `PRICE_IN = 0.28`, `PRICE_OUT = 0.42` ($/M tokens DeepSeek pricing assumption).
  - `sys_tok = (len(CLINICAL_SYSTEM_PROMPT) + 600) // 4`
  - `tin = sum(sys_tok + len(p) // 4 + 80 for *_, p in js)`
  - `tout = 700 * len(js)`
  - `usd = round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 2)`

### 1.2 `reports/gapfill_conditions.json` Evaluation Scope
- **File location**: `reports/gapfill_conditions.json` (1,153 lines, 17,815 bytes).
- **Condition count**: exactly 100 conditions (e.g. Tuberculosis, Malaria, Dengue, Typhoid fever, Influenza, etc.).
- **Item schema**:
  ```json
  {
    "condition": "Tuberculosis",
    "missing": ["CONTRAINDICATES"],
    "search_terms": ["tuberculosis", "tb", "mycobacterium tuberculosis"]
  }
  ```
- **Job matching**: `find_passages(terms)` matches across 4 textbooks: `tripathi`, `davidson`, `harrison`, `micro`. For the 100 conditions, `jobs(conds)` generates 618 extraction jobs.
- **Cache status**: `data/ontology/cache_gapfill/` currently contains 620 pre-existing cached JSON result files from earlier runs.

### 1.3 Execution of `ontology/gapfill.py --dry-run`
- **Command executed**:
  `.venv/bin/python -m ontology.gapfill --conditions reports/gapfill_conditions.json --dry-run`
- **Output obtained**:
  `{"conditions": 100, "jobs": 618, "to_run": {"calls": 0, "tokens_in": 0, "tokens_out_guess": 0, "usd": 0.0}}`
- **Exit code**: `0`.
- **Zero-token verification**: Because all 618 jobs are cached in `data/ontology/cache_gapfill/`, `to_run` calls = 0 and estimated cost = $0.00.
- **Cold-run / Uncached Baseline Analysis**:
  Evaluated with `estimate(js)` on all 618 jobs ignoring cache:
  - Total jobs: 618 calls
  - Total input tokens: 1,653,524 tokens (~1.65M tokens)
  - Total output tokens guess: 432,600 tokens (~0.43M tokens)
  - Total uncached cost: **$0.64** (well within default `--max-usd 3.0`).

### 1.4 Test Suite Survey & Baseline Execution
- **Command executed**:
  `.venv/bin/pytest tests/`
- **Output obtained**:
  `143 passed, 5 warnings in 8.70s` (Python 3.13.18, pytest-9.2.0, macOS Darwin).
- **Test files breakdown** (15 test modules, 143 total tests):
  1. `tests/test_atlas.py` (10 tests): UMLS / anatomical atlas variants and link resolution.
  2. `tests/test_clinical_graph.py` (7 tests): graph store nodes, edges, queries.
  3. `tests/test_comention.py` (3 tests): co-mention graph construction and querying.
  4. `tests/test_concepts.py` (9 tests): concept registry, BODHI differential vs certified facts routing.
  5. `tests/test_crosswalk.py` (8 tests): textbook crosswalk resolution and trust tiers.
  6. `tests/test_deploy_imports.py` (2 tests): import sanity in production deployment.
  7. `tests/test_diagrams.py` (10 tests): clinical diagram extraction and validation.
  8. `tests/test_graph_walk.py` (15 tests): multihop graph traversal and tier leak prevention.
  9. `tests/test_hops_axes.py` (23 tests): clinical case three-axis decomposition and routing.
  10. `tests/test_hubs.py` (4 tests): hub data layer query API and tier verification.
  11. `tests/test_ingest.py` (11 tests): section parsing, tokenization, text extraction.
  12. `tests/test_mentions.py` (4 tests): mention index building and querying.
  13. `tests/test_ontology.py` (7 tests): clinical ontology schema, reconciler, and verification.
  14. `tests/test_ontology_reinforce.py` (14 tests): ontology compiler, gold triples, validation gates.
  15. `tests/test_rag.py` (16 tests): end-to-end RAG answer pipeline, citation checks, guardrails.
- **Key fixture patterns**:
  - `monkeypatch` / `tmp_path` for ephemeral disk mocking (`monkeypatch.setattr(module, "PATH", tmp_file)`).
  - Stubbing LLM chat via `monkeypatch.setattr(hops, "chat", fake_chat)`.
  - Cache clearing (`hubs._load.cache_clear()`, `ontology_facts.facts.cache_clear()`).

### 1.5 Existing Leak Tests in `tests/`
Direct inspection of `tests/` identified existing leak prevention tests:
1. `tests/test_graph_walk.py:159-204`:
   - `test_mention_hub_comention_text_never_reaches_graph_facts`: Uses poison sentinel text in hubs/co-mentions; verifies sentinel never appears in `p.graph_facts` and all facts start with `("Textbook ontology:", "WARNING (textbook ontology)")`.
   - `test_non_trusted_crosswalk_labels_never_resolve`: Ensures broader/related/unchecked crosswalk tiers resolve 0 entities.
   - `test_every_graph_fact_comes_from_graph_facts_for`: Ensures `set(p.graph_facts) <= allowed_certified`.
   - `test_hops_source_has_no_forbidden_tiers`: Inspects AST/source code of `hops.py` asserting no forbidden module imports (`rag.hubs`, `import hubs`, `comention`, `rag.concepts`, `bodhi_for(`, `ontology_for(`) and ensures `graph_facts.append` only ever receives certified lines.
   - `test_expansion_hits_are_plain_evidence_not_graph_facts`: Verifies secondary graph expansion hits remain textbook evidence passages and do not enter `graph_facts`.
2. `tests/test_concepts.py:113-135`:
   - `test_bodhi_never_reaches_graph_facts`: BODHI may provide differential, but BODHI drug links never enter `p.graph_facts`.
   - `test_answer_prompt_has_only_certified_facts_and_passages`: Intercepts prompt sent to `chat` in `answer_multihop` and asserts `[G#]` lines contain exclusively certified ontology facts.
3. `tests/test_hubs.py:44-50`:
   - `test_built_data_never_claims_certified`: Asserts all records in `data/graph/hubs.jsonl` are `tier in ("T2", "T3")` and never `"T1"`.

---

## 2. Logic Chain

1. **Safety of Gap-Fill Dry-Run (Observation 1.1, 1.3)**:
   - In `ontology/gapfill.py`, `--dry-run` prints the JSON summary and returns immediately before `ThreadPoolExecutor` or `_extract` are invoked.
   - `chat` is imported locally inside `_extract`. Thus, in dry-run mode, the LLM backend is not imported and zero network requests or token expenditures occur.
   - Running `.venv/bin/python -m ontology.gapfill --conditions reports/gapfill_conditions.json --dry-run` successfully produced `{"conditions": 100, "jobs": 618, "to_run": {"calls": 0, "tokens_in": 0, "tokens_out_guess": 0, "usd": 0.0}}` with return code 0.

2. **Cost Analysis (Observation 1.1, 1.2, 1.3)**:
   - Because 618 cached results already exist in `data/ontology/cache_gapfill/`, executing gap-fill would require 0 calls and $0.00.
   - Even in a hypothetical zero-cache cold run across all 100 conditions in `reports/gapfill_conditions.json`, total input tokens would be ~1.65M and output tokens ~0.43M, totaling **$0.64** at DeepSeek rates ($0.28/M in, $0.42/M out).
   - This is far below the default built-in safety ceiling of `$3.00` (`--max-usd 3.0`).

3. **Regression Baseline (Observation 1.4)**:
   - The test suite in `tests/` contains 143 tests across 15 files.
   - All 143 tests pass cleanly in 8.70s with zero failures.
   - Any modifications introduced in Stages A, B, or R2 must maintain this 143-test green baseline.

4. **Mechanism of `graph_block` in Answer Formulation (Observation 1.1, 1.5)**:
   - In `rag/answer.py:201-209`, `graph_block` is formatted as `"\n".join(f"[G{i}] {f}" for i, f in enumerate(p.graph_facts, 1))` and injected into the prompt alongside textbook passages.
   - Facts in `p.graph_facts` are populated strictly via `rag/ontology_facts.py:graph_facts_for`, which filters only facts where `status == "CERTIFIED"` from `data/ontology/clinical_ontology.jsonl`.
   - Per `docs/headings_to_ontology_plan.md` sections 2 and 7, heading records generated in `data/graph/headings.jsonl` represent T2 derived, T3 inferred, or navigation tiers (primary topic links, parent/child subtopic, part-of candidates, facets, case links).
   - Non-T1 records are navigation metadata; they must NEVER enter `clinical_ontology.jsonl` as CERTIFIED facts and must NEVER reach `graph_block`.

5. **Design of Automated Non-T1 Leak Tests (Observation 1.5)**:
   - Following the established pattern from `test_graph_walk.py` and `test_concepts.py`, automated tests must be placed in a dedicated test file `tests/test_headings_leak.py` (or within `tests/test_headings.py`).
   - The tests must assert five separate invariant barriers:
     1. *Static/AST Import Boundary*: `rag.answer`, `rag.hops`, and `rag.ontology_facts` do not import `rag.headings`.
     2. *File Tier Purity*: Every record in `data/graph/headings.jsonl` has `tier in ("T2", "T3", "navigation")` and never `"T1"` or `status: "CERTIFIED"`.
     3. *Sentinel Prompt Leak Test*: Mock heading data containing sentinel tokens (e.g. `SENTINEL = "NON_T1_HEADING_LEAK_TOKEN"`). Execute `answer_multihop` and intercept the prompt sent to `chat`. Assert `SENTINEL not in prompt.split("Textbook passages:")[0]`.
     4. *Line Prefix Invariant*: Assert all lines in `p.graph_facts` and `[G#]` prompt blocks start strictly with `("Textbook ontology:", "WARNING (textbook ontology)")` or allowed `BODHI` differential strings, and never heading metadata.
     5. *Concept Triple Gating*: Assert that a concept minted solely from a heading (T3) without certified clinical triples returns empty `graph_facts_for(heading_concept) == []`.

---

## 3. Caveats

- **Pre-existing Cache**: `data/ontology/cache_gapfill/` currently contains 620 cached JSON files from an earlier run. If the user intends to re-extract facts from scratch, those cache files would need to be cleared; however, retaining the cache saves 100% of LLM calls ($0.00 spend).
- **Rule 9 Headings Exception**: Per `docs/headings_to_ontology_plan.md`, Rule 9 (future anatomy relations from Gray's) is the *only* rule that will ever produce T1 certified facts with verbatim quote verification into `clinical_ontology.jsonl`. Stage A implements Rules 1, 3, 4, 5a, 6, and 8, which produce strictly T2/T3/navigation records into `data/graph/headings.jsonl`.
- **Scratchpad Logic Promotion**: The promotion of `hlib.py`, `hclass.py`, etc., into `rag/headings.py` is part of Stage A (R1) implementation. When implemented, the leak test suite designed here must run alongside it.

---

## 4. Conclusion

1. **R3 Status & Recommendation**:
   - The dry-run execution of `ontology/gapfill.py` is completely safe to execute with:
     ```bash
     .venv/bin/python -m ontology.gapfill --conditions reports/gapfill_conditions.json --dry-run
     ```
   - It performs zero LLM calls and consumes zero tokens.
   - Cost review summary:
     - With existing cache in `data/ontology/cache_gapfill/`: **0 calls, $0.00**.
     - Cold run (uncached): **618 calls, 1.65M tokens in, 432K tokens out, estimated cost $0.64**.
     - Both scenarios are well within the `$3.00` safety limit.

2. **R4 Test Baseline**:
   - Pytest suite currently has **143 tests**, all passing in **8.70s**.
   - No broken tests or regressions exist in the current tree.

3. **R4 Non-T1 Leak Testing Architecture**:
   - A multi-barrier leak test harness must be implemented (recommended: `tests/test_headings_leak.py`) asserting AST import isolation, `headings.jsonl` tier compliance, prompt interception verifying sentinel exclusion from `graph_block`, and prefix validation on `p.graph_facts`.

---

## 5. Verification Method

To independently verify these findings, execute the following commands in `/Users/ishaanwadhwa/Projects/med-rag`:

1. **Verify Existing Pytest Suite**:
   ```bash
   .venv/bin/pytest tests/
   ```
   *Expected result*: 143 passed, 0 failures.

2. **Verify Gap-Fill Dry-Run Execution & Safety**:
   ```bash
   .venv/bin/python -m ontology.gapfill --conditions reports/gapfill_conditions.json --dry-run
   ```
   *Expected output*:
   `{"conditions": 100, "jobs": 618, "to_run": {"calls": 0, "tokens_in": 0, "tokens_out_guess": 0, "usd": 0.0}}`
   *Exit code*: `0`.

3. **Verify Gap-Fill Uncached Cost Calculation**:
   ```bash
   .venv/bin/python -c "
   import json
   from pathlib import Path
   from ontology.gapfill import jobs, estimate

   conds = json.loads(Path('reports/gapfill_conditions.json').read_text())
   js = jobs(conds)
   print(json.dumps(estimate(js), indent=2))
   "
   ```
   *Expected output*: `{"calls": 618, "tokens_in": 1653524, "tokens_out_guess": 432600, "usd": 0.64}`.

4. **Verify Existing Leak Test Patterns**:
   ```bash
   .venv/bin/pytest tests/test_graph_walk.py -k "leak or forbidden or certified"
   .venv/bin/pytest tests/test_concepts.py -k "graph_facts or answer_prompt"
   ```
   *Expected result*: All targeted leak tests pass.

*Invalidation conditions*:
- If `ontology/gapfill.py --dry-run` attempts to call `chat` or access external APIs.
- If existing pytest test count falls below 143 or tests fail.
- If any non-T1 record or sentinel from `data/graph/headings.jsonl` appears in `p.graph_facts` or `graph_block`.
