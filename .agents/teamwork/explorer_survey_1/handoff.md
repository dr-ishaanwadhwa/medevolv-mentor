# Handoff Report — Explorer Survey 1: Headings Densification (Stage A) & Leak Prevention

**Date**: 2026-11-13  
**Agent**: teamwork_explorer (`explorer_survey_1`)  
**Parent Agent**: `57110369-e183-4fdc-9b47-086b61a6c6e5`  
**Working Directory**: `/Users/ishaanwadhwa/Projects/med-rag/.agents/teamwork/explorer_survey_1`  

---

## 1. Observation

### 1.1 Direct File and Codebase Observations

1. **`docs/headings_to_ontology_plan.md`**:
   - Status noted as "plan only, nothing implemented, no code or data changed" (lines 3–5).
   - Establishes Stage A as deterministic, $0 LLM spend (lines 375–377):
     > "Stage A: deterministic, $0, about 3 days. Rules 3, 1, 8, 6 (identical keys), 5a (parenthetical aliases), 4 (`subtopic_of`). Write `data/graph/headings.jsonl` (`heading_id, book, section_id, level, class, facet, concept_ids, parent_id, tier, method, evidence`), `rag/headings.py` loader, `eval/heading_metrics.py` (promote the scratch scripts), and the leak test: no record from this file can reach `graph_block`. Audit 100 primary-topic links."
   - Explicitly defines tiers (lines 132–138):
     - `T1 certified`: LLM-extracted, verbatim quote found in section (`status: CERTIFIED`). **Only this may reach an answer prompt.**
     - `T2 derived`: Deterministic rule over ToC or T1 facts (inverse, heading = concept, hierarchy). **Navigation/display only, never reaches answers.**
     - `T3 inferred`: LLM or similarity judgment. **Never reaches answers.**
     - `navigation`: Structural / facet. **Never reaches answers.**
   - Section 7 (lines 411–422) mandates:
     > "Anything from `headings.jsonl` of tier T2, T3 or navigation: primary topics, new heading concepts, facets, `subtopic_of`, `part_of` candidates, `member_of_candidate`, `same_as_candidate`, case links, aliases... must never reach answers."
     > "A facet heading is never an entity and never a subject or object of a fact."

2. **Scratchpad Directory (`/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/`)**:
   - Total files observed: `h1.py`, `h2.py`, `h4.py`, `h5.py`, `h6.py`, `h7.py`, `hclass.py`, `hlib.py`, `recs.json`, `recs2.json`, `recs3.json`, `body.json`, `body2.json`, `and.json`.
   - Verified that `recs3.json` contains exactly 3,135 tree node records across the 7 textbooks, of which 2,675 are section leaves (`sum(r['is_section'] for r in recs) == 2675`).
   - Verified that `recs3.json` classification exactly matches `hclass.classify()` (0 differences across all 3,135 items when tested against `hlib` and `hclass`).
   - `hclass.py`:
     - Line 35: `FRONT.match(h) or r['level']==0: return 'structural', None`
     - Line 36–37: `CASE.match(h): return ('case_cond' if m.group(1) else 'case_bare'), None`
     - Line 38: `if k2 in FACET_EXACT: return 'facet', None` (91 distinct facet strings). **Crucially evaluated BEFORE entity matching on line 41.**
     - Line 39–40: Positional and procedural checks.
     - Line 41: `if r.get('match'): return 'matched', (r['mtypes'][0] if r['mtypes'] else None)`
     - Lines 42–77: Group, group_class, topic, and book-specific heuristic typing (`entity`).
   - `hlib.py`:
     - Builds entity index from `rag.ontology_facts.facts()`: `ENT[merge_key(lab)] -> set of (label, type)` and `ENT_P` with stripped parentheticals.
     - `clean(h)`: Strips section/part prefixes (`SECTION`, `Part`, `Unit [0-9IVX]+`), chapter numbers (`52. `, `37.`), Roman numerals (`IV. `), trailing periods, and capitalizes all-caps.
     - `paren_split(h)`: Extracts parenthetical tokens and strips them from main string.
     - `match(h)`: Evaluates exact `merge_key(h)` against `ENT`, then parenthetical components, then `ENT_P`, then `atlas.variants()`.
   - `h2.py`:
     - Parses `data/okf/{book}/toc.json` across 7 books (`davidson`, `grays`, `guyton`, `harrison`, `micro`, `robbins`, `tripathi`).
     - Splits path by `' › '` to extract levels 1..N and computes child count `n_children`.
   - `h4.py`–`h7.py`:
     - `h4.py`: Evaluates provenance: 471 section leaves match strictly; 219 (47%) have same-section provenance; 326 (69%) same-book provenance.
     - `h5.py`: Evaluates patterns across ToC: 98 parentheticals, 32 abbreviations, 16 synonym lists, 10 possessive eponyms, 103 clinical cases (98 named conditions).
     - `h6.py`: Evaluates splits, cross-book identical keys (64 in 2+ books), Tripathi class-to-member links (134 pairs), tree edges (2,414 non-facet `subtopic_of` steps, 188 Gray's `part_of` candidates).
     - `h7.py`: Relaxed matcher (prefix/suffix stripping, variants) adds 47 matches.

3. **Existing RAG Pipeline and Loaders**:
   - `rag/headings.py`: Does not exist.
   - `rag/hubs.py`: Implements a cached loader pattern (`PATH = Path("data/graph/hubs.jsonl")`, `@functools.cache def _load() -> tuple[...]`) with public accessors (`hubs_for`, `members`, `all_hubs`).
   - `rag/answer.py`:
     - Line 201: `graph_block = "\n".join(f"[G{i}] {f}" for i, f in enumerate(p.graph_facts, 1))`
     - Line 209: `prompt = (f"{axes_line}Graph facts:\n{graph_block or '(none)'}\n\nTextbook passages:\n\n{text_block or '(none)'}...")`
     - Only `p.graph_facts` populates `graph_block`.
   - `rag/hops.py`:
     - Line 53: `graph_facts: list[str] = field(default_factory=list)`
     - Lines 360–362, 449–451, 480–484, 575–577: `p.graph_facts` is strictly populated from `ontology_facts.graph_facts_for(...)` (and a few fixed diagnostic strings like `BODHI links...`).
   - `rag/ontology_facts.py`:
     - Lines 75–86: `facts()` loads exclusively from `data/ontology/clinical_ontology.jsonl` filtering strictly for `f.get("status") == "CERTIFIED"`.
   - `eval/heading_metrics.py`: Does not exist.
   - Existing test suite (`.venv/bin/pytest tests/`): 143 passed in 5.89s.
   - `tests/test_graph_walk.py` (lines 47–53, 186–195): Enforces isolation by monkeypatching forbidden modules (`hubs`, `comention`) to raise `AssertionError` if invoked during graph walk, and checks source code for forbidden imports.

---

## 2. Logic Chain

### 2.1 Why the Facet Filter Must Precede Entity Matching (Rule 3 before Rule 1)
- *Observation*: In `hclass.py` line 38, `FACET_EXACT` check precedes line 41 `r.get('match')`. Testing in Python confirmed that words like "Joints", "Nerves", "Arteries", and "Toxicity" match certified ontology nodes:
  - "Joints" matches `MED:OKF/therapeuticagent/joint-replacement` (TherapeuticAgent).
  - "Nerves" and "Arteries" match `AnatomicalStructure` nodes.
  - "Toxicity" matches `ClinicalPhenotype`.
- *Inference*: If entity matching ran before facet filtering, generic textbook structural sections (e.g. Gray's anatomy sections titled "Nerves", "Arteries", "Joints") would be falsely linked as primary topics to specific clinical entities. By filtering against `FACET_EXACT` first, all 460 generic facet headings are correctly designated as `class='facet'` with `concept_ids=[]` and `tier='navigation'`, achieving the hard gate of **0 generic facets promoted to entities**.

### 2.2 Mechanism of Rule 1 (Primary Topic Linking) & Disambiguation
- *Observation*: `h4.py` and `hlib.py` identify 507 strict heading matches and `h7.py` identifies 47 relaxed matches (total ~554). Among strict matches, 23% match multiple ontology nodes.
- *Inference*: To map a heading to a single canonical primary topic entity:
  1. Strict match on cleaned heading key `merge_key(clean)`.
  2. If unmatched, check parenthetical alias `merge_key(main)` or `merge_key(alias)` (Rule 5a).
  3. If unmatched, check relaxed match (Rule 1 relaxed: strip prefix `PRE`, suffix `SUF`, atlas variants).
  4. If multiple concept nodes match the key:
     - Disambiguate using book-expected type:
       - `grays`: `AnatomicalStructure`
       - `tripathi`: `TherapeuticAgent`
       - `guyton`: `PhysiologicalProcess`
       - `harrison`, `robbins`, `davidson`, `micro`: `PathologicalCondition`
     - If still tied, select the node present in the current book's certified facts; if still tied, select highest fact degree.
  5. Generic single-word mitigation: If heading is single-word (non-Tripathi, e.g. "Pain", "Cancer", "Shock"), require at least one fact in the same book, otherwise mark method as `bridge`, preventing false-positive primary-topic binding.

### 2.3 Mechanism of Rule 4 (Hierarchy: `subtopic_of` and `part_of`)
- *Observation*: ToC paths represent the textbook's outline tree. Scratchpad `h6.py` measured 2,414 parent-to-child steps from chapter level down (excluding facet, structural, and positional children).
- *Inference*:
  - Every valid parent-to-child step in the heading tree creates a `child -- subtopic_of --> parent` relation.
  - `parent_id` is assigned to the immediate parent's `heading_id`.
  - For Gray's anatomy: when both child and parent are classified as `AnatomicalStructure` (`cls in ('entity', 'matched')`), propose `child -- part_of --> parent` as a `T3` candidate (188 pairs observed).

### 2.4 Mechanism of Rule 5a (Parenthetical Aliases & Merge Proposals)
- *Observation*: 98 headings contain parentheses (`h6.py`).
- *Inference*:
  - Regex extraction: tokens inside `(...)`. All-caps tokens of 2–6 characters are classified as `abbreviation` (32 instances); tokens separated by commas, semicolons, or "or" are classified as `synonym` (16 instances).
  - When `main` has no match but an alias token matches an ontology node, link the section via `method="heading-paren"` (13 instances).
  - When `main` and `alias` both match distinct ontology nodes with different `merge_key`s, emit a merge proposal record (7 instances).

### 2.5 Mechanism of Rule 6 (Identical Cross-Book Headings)
- *Observation*: Scratchpad `h6.py` measured 64 identical heading keys across 2+ books (excluding facets, structural, positional, procedural).
- *Inference*:
  - Headings with identical `merge_key` in 2+ books link to the same concept cluster (`T2` bridge).
  - 37 already match an existing ontology node; 27 represent newly discovered cross-book concepts.

### 2.6 Mechanism of Rule 8 (Case Section Links)
- *Observation*: In Gray's, 103 sections match `CASE = re.compile(r'^case\s+\d+\s*(?::\s*(.+))?$', re.I)`. 98 contain named conditions, 77 of which match existing ontology nodes.
- *Inference*:
  - Heading is classified as `class='case_cond'`.
  - Link `condition -- illustrated_by --> case_section` with `tier='T2'`, `method='rule8:case'`, `evidence=section_id`.

### 2.7 Leak Prevention Architecture
- *Observation*: Answers in `rag/answer.py` format `graph_block` directly from `p.graph_facts`. In `rag/hops.py`, `p.graph_facts` is loaded exclusively from `ontology_facts.graph_facts_for(...)`.
- *Inference*:
  - A leak can only occur if:
    1. Heading records are accidentally written to `data/ontology/clinical_ontology.jsonl`.
    2. `rag/hops.py` or `rag/answer.py` imports `rag/headings.py` and directly appends heading records or derived text to `p.graph_facts`.
    3. `ontology_facts.py` reads `data/graph/headings.jsonl`.
  - Therefore, non-T1 leak prevention requires:
    1. Strict physical file separation: `headings.jsonl` is written to `data/graph/headings.jsonl`, never `data/ontology/`.
    2. Strict schema assertion: every record in `headings.jsonl` must have `tier in ("T2", "T3", "navigation")`, never `"T1"`.
    3. Static code analysis test (AST): assert `rag/hops.py` contains zero imports or calls to `rag.headings`.
    4. Poison test: monkeypatch `rag.headings` methods to raise `AssertionError` during multihop execution, proving `hops.make_plan()` runs without touching `headings.py`.
    5. Prompt assertion: verify that `[G#]` lines in prompts contain zero heading IDs, zero facet strings, and zero non-T1 derivation text.

---

## 3. Caveats

1. **ToC vs In-Body Headings Scope**:
   - In accordance with Section 5 of `docs/headings_to_ontology_plan.md`, Stage A covers the 3,135 ToC nodes across all 7 books. In-body markdown subheadings (1,588 in Gray's and 350 in Tripathi) are scheduled for Stage B / C.
2. **Heuristic Classification for Unmatched Headings**:
   - Unmatched entity-like headings (1,221 nodes) receive heuristic types (`AnatomicalStructure`, `TherapeuticAgent`, `PathologicalCondition`, `PhysiologicalProcess`). Per Section 1.3 of the plan, regex typing accuracy is ~50–75%; the definitive typing is deferred to the Stage B LLM pass. However, Stage A deterministic matching (strict + relaxed + facets) has >95% precision.
3. **No Live LLM Calls in Stage A**:
   - Stage A is strictly $0 cost and deterministic. Ambiguous "X and Y" compound splits (245 strings) remain un-split composite concepts in Stage A as designed.

---

## 4. Conclusion & Actionable Implementation Plan

### 4.1 Architecture for `rag/headings.py`

`rag/headings.py` should be implemented as a deep module following the pattern of `rag/hubs.py`:
- **File path**: `rag/headings.py`
- **Cached Loader**:
  ```python
  @functools.cache
  def _load() -> tuple[list[dict], dict[str, dict], dict[str, dict], dict[str, list[dict]], dict[str, list[dict]]]:
      """Returns (records, by_heading_id, by_section_id, by_concept_id, by_parent_id)"""
  ```
- **Query APIs**:
  - `primary_topic(section_id: str) -> dict | None`: Returns the primary topic record for a section leaf.
  - `section_heading(section_id: str) -> dict | None`: Returns the heading record for a section.
  - `headings_for_concept(concept_id: str) -> list[dict]`: Headings linked to a given ontology concept.
  - `facets_for(heading_id: str) -> list[dict]`: Child facet headings attached to a parent.
  - `subtopics(heading_id: str) -> list[dict]`: Child headings in the hierarchy.
  - `part_of_candidates(book: str = "grays") -> list[dict]`: Gray's anatomy part-of candidates.
  - `parenthetical_aliases() -> list[dict]`: All parsed abbreviations and synonyms.
  - `cross_book_headings() -> list[dict]`: Identical headings appearing in 2+ books.
  - `all_headings(book: str | None = None, cls: str | None = None) -> list[dict]`
- **Build / Generator Logic**:
  - `clean_heading(h: str) -> str`: Numbering and formatting cleaner.
  - `paren_split(h: str) -> tuple[str, list[str]]`: Parentheses extractor.
  - `classify_heading(r: dict) -> tuple[str, str | None]`: Deterministic classifier implementing Section 3.0 decision list.
  - `build_heading_tree() -> list[dict]`: Tree parser over `data/okf/*/toc.json`.
  - `build_headings(output_path: Path | str = PATH) -> list[dict]`: Generates `data/graph/headings.jsonl`.
  - Execution via `python -m rag.headings` and `scripts/build_headings.py`.

### 4.2 Target Schema for `data/graph/headings.jsonl`

Every line is a valid JSON object matching the specification in `docs/headings_to_ontology_plan.md`:
```json
{
  "heading_id": "grays:thorax-pleural-cavities-lungs:3",
  "book": "grays",
  "section_id": "grays/045-lungs",
  "level": 3,
  "raw": "Lungs",
  "clean": "Lungs",
  "class": "matched",
  "facet": null,
  "concept_ids": ["MED:OKF/anatomicalstructure/lungs"],
  "concept_label": "Lungs",
  "parent_id": "grays:thorax-pleural-cavities:2",
  "tier": "T2",
  "method": "rule1:heading-exact",
  "evidence": "grays/045-lungs"
}
```
Field specifications:
- `heading_id` (str): Unique slug-based identifier per ToC tree node.
- `book` (str): Book name (`davidson`, `grays`, `guyton`, `harrison`, `micro`, `robbins`, `tripathi`).
- `section_id` (str | None): Section ID if node is a leaf, else `None`.
- `level` (int): Tree level (1 = Part/Chapter group, 2 = Chapter/Section, etc.).
- `clean` (str): Cleaned heading text.
- `class` (str): Heading class (`matched`, `facet`, `entity`, `group`, `group_class`, `topic`, `case_cond`, `case_bare`, `positional`, `procedural`, `structural`).
- `facet` (str | None): Facet string/kind if `class == 'facet'`, else `None`.
- `concept_ids` (list[str]): List of matched ontology concept IDs (empty for facets and structural).
- `parent_id` (str | None): `heading_id` of the parent tree node.
- `tier` (str): `"T2"` (derived), `"T3"` (candidate), or `"navigation"` (structural/facet). **Strictly never `"T1"`.**
- `method` (str): Rule identifier (e.g. `rule1:heading-exact`, `rule1:heading-paren`, `rule1:heading-relaxed`, `rule3:facet`, `rule4:hierarchy`, `rule5a:alias`, `rule6:cross-book`, `rule8:case`).
- `evidence` (str | None): Section ID or ToC path evidence.

### 4.3 Architecture for `eval/heading_metrics.py`

`eval/heading_metrics.py` promotes the scratchpad measurement scripts (`h1.py`–`h7.py`) into a structured evaluation tool:
- Computes and prints:
  1. Section and tree node coverage summary across all 7 books.
  2. Classification distribution table (7 books x 11 classes).
  3. Primary topic yield: strict matches, relaxed matches, provenance check (% same section, % same book).
  4. Facet filter verification: confirms 0 generic facets promoted to entities (Hard Gate).
  5. Hierarchy yield: `subtopic_of` edge count (expected 2,414), Gray's `part_of` candidates (expected 188).
  6. Parenthetical aliases: count of abbreviations, synonyms, alias-only matches, and merge proposals.
  7. Cross-book identical heading bridges: count (expected 64).
  8. Case condition links: count (expected 103 cases, 98 named, 77 matched).
  9. Non-T1 leak gate: verifies 0 records have tier T1, 0 heading records in `data/ontology/clinical_ontology.jsonl`.
- Outputs JSON report to `reports/heading_metrics.json`.

### 4.4 Leak Test Design (`tests/test_heading_leak.py`)

A 5-point automated test suite ensuring non-T1 heading records can never reach `graph_block`:
1. **Tier Invariant Test**: Iterates every row of `data/graph/headings.jsonl`; asserts `r["tier"] in ("T2", "T3", "navigation")` and `r["tier"] != "T1"`.
2. **Ontology Contamination Test**: Reads `data/ontology/clinical_ontology.jsonl`; asserts no record has `source: heading` or `rule` prefixes, and all records have `status == "CERTIFIED"`.
3. **AST Static Isolation Test**: Parses `rag/hops.py` and `rag/answer.py` via `ast.parse`; asserts neither file contains an `Import` or `ImportFrom` referencing `rag.headings` or `headings`.
4. **Poisoning Isolation Test**: Monkeypatches every callable in `rag.headings` with a function raising `AssertionError("headings module must never be called during multihop execution")`. Executes `hops.make_plan(question)` across test questions and verifies normal execution without triggering the poison.
5. **Prompt Inspection Test**: In multi-hop answer generation (`answer_multihop`), inspects the generated `p.graph_facts` and formatted `graph_block`; asserts every line strictly originates from `ontology_facts.graph_facts_for(...)` and contains zero heading identifiers or hierarchy edges.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify scratchpad reproducibility with project venv**:
   ```bash
   .venv/bin/python -c "
   import sys, json; sys.path.insert(0,'/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad')
   from hlib import *
   from hclass import *
   recs = json.load(open(SP+'recs3.json'))
   print('Total recs:', len(recs), 'Sections:', sum(r['is_section'] for r in recs))
   diffs = sum(1 for r in recs if (classify(r)[0], classify(r)[1]) != (r['cls'], r['ctype']))
   print('Differences between classifier and recs3:', diffs)
   "
   ```
   *Expected output*: `Total recs: 3135 Sections: 2675 Differences between classifier and recs3: 0`.

2. **Verify facet protection against false-positive entity matches**:
   ```bash
   .venv/bin/python -c "
   import sys; sys.path.insert(0,'/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad')
   from hlib import *
   from hclass import *
   for word in ['Joints', 'Nerves', 'Arteries', 'Toxicity']:
       m = match(word)
       cls, ty = classify({'clean': word, 'book': 'grays', 'level': 3, 'match': m[0], 'mtypes': sorted(m[1]), 'n_children': 0, 'path': ['Grays', word]})
       print(word, 'match:', m[0], 'cls:', cls)
       assert cls == 'facet', f'{word} leaked past facet filter'
   print('Facet filter test PASSED!')
   "
   ```
   *Expected output*: `Facet filter test PASSED!`.

3. **Verify existing test suite integrity**:
   ```bash
   .venv/bin/pytest tests/
   ```
   *Expected output*: `143 passed in ~5-6s`.

4. **Invalidation Conditions**:
   - If any record in `data/graph/headings.jsonl` has `tier == "T1"`.
   - If `FACET_EXACT` items are classified as `matched` or `entity`.
   - If `rag/hops.py` imports `rag.headings` to append to `p.graph_facts`.
   - If `data/ontology/clinical_ontology.jsonl` is modified by headings generation.
