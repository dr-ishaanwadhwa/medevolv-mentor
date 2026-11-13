"""Automated 5-barrier leak test suite and functional tests for textbook headings densification.

Enforces the strict integrity invariants mandated by docs/headings_to_ontology_plan.md:
Barrier 1: Tier Invariant - Every heading record must have tier in ("T2", "T3", "navigation"), never "T1".
Barrier 2: Ontology Contamination - clinical_ontology.jsonl must contain 0 heading records.
Barrier 3: AST Static Isolation - rag/hops.py and rag/answer.py must never import rag.headings.
Barrier 4: Poisoning Test - Monkeypatched rag.headings methods must never trigger during multi-hop execution.
Barrier 5: Prompt Inspection - real hops.plan / answer_multihop with stubbed chat: no heading-derived text in graph_facts or prompt.

Also exercises all public query APIs in rag/headings.py.
"""
from __future__ import annotations

import ast
import collections
import inspect
import json
from pathlib import Path
import re

import pytest

from rag import answer, headings, hops, ontology_facts

HEADINGS_PATH = Path("data/graph/headings.jsonl")
ONTOLOGY_PATH = Path("data/ontology/clinical_ontology.jsonl")


# ==============================================================================
# Barrier 1: Tier Invariant
# ==============================================================================

def test_barrier1_tier_invariant():
    """Verify that every record in headings.jsonl has a non-T1 tier and valid schema, without hardcoded counts."""
    assert HEADINGS_PATH.exists(), "data/graph/headings.jsonl does not exist"
    lines = [l for l in HEADINGS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [json.loads(l) for l in lines]
    assert rows

    required_keys = {
        "heading_id", "book", "section_id", "level", "class", "facet",
        "concept_ids", "concept_label", "parent_id", "tier", "method", "evidence",
    }

    for i, r in enumerate(rows, 1):
        for k in required_keys:
            assert k in r, f"Line {i} missing required key '{k}': {r}"

        tier = r["tier"]
        assert tier in ("T2", "T3", "navigation"), f"Line {i} has forbidden tier: {tier}"
        assert tier != "T1", f"HARD GATE VIOLATION: Line {i} has tier T1!"

        cls = r["class"]
        if cls == "facet":
            assert r["tier"] == "navigation", f"Facet line {i} must have tier navigation"
            assert r["concept_ids"] == [], f"Facet line {i} must never have concept_ids"
            assert r["facet"] is not None, f"Facet line {i} must have facet name"
        elif cls == "entity":
            assert r["tier"] == "T3", f"Entity line {i} must have tier T3 in Stage A"
            assert r["concept_ids"] == [], f"Entity line {i} must have empty concept_ids in Stage A"
        elif cls == "matched":
            assert r["tier"] == "T2", f"Matched line {i} must have tier T2"
            assert len(r["concept_ids"]) >= 1, f"Matched line {i} must have at least one concept_id"
            assert r["concept_label"] is not None, f"Matched line {i} must have concept_label"
        elif cls == "case_cond":
            assert r["tier"] == "T2", f"Case cond line {i} must have tier T2"

    # Counts must add up, whatever the current toc size is.
    assert sum(collections.Counter(r["tier"] for r in rows).values()) == len(rows)
    assert sum(collections.Counter(r["class"] for r in rows).values()) == len(rows)
    assert len({r["heading_id"] for r in rows}) == len(rows), "heading_id collision"
    assert all(r["tier"] != "T1" for r in rows)

    # Every toc section has a record. Sections that repeat the same path (the file keys sections by path)
    # collapse into one record, so the check is per distinct path.
    by_path: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    for b in headings.BOOKS:
        toc_file = Path(f"data/okf/{b}/toc.json")
        if toc_file.exists():
            for x in json.loads(toc_file.read_text(encoding="utf-8")):
                by_path[(b, x["path"])].add(x["id"])
    assert by_path, "no toc files found"
    recorded = {(r["book"], " \u203a ".join(r["path"])): r["section_id"] for r in rows if r.get("is_section")}
    for key, ids in by_path.items():
        assert key in recorded, f"toc section path has no heading record: {sorted(ids)}"
        assert recorded[key] in ids, f"record for {key} points at a section id not in the toc"


# ==============================================================================
# Barrier 2: Ontology Contamination
# ==============================================================================

def test_barrier2_ontology_contamination():
    """Verify data/ontology/clinical_ontology.jsonl contains 0 heading records and ontology_facts loads only certified."""
    assert ONTOLOGY_PATH.exists(), "clinical_ontology.jsonl does not exist"
    lines = ONTOLOGY_PATH.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 0

    heading_contaminants = 0
    statuses = set()
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        f = json.loads(line)
        statuses.add(f.get("status"))
        if (
            f.get("source") in ("heading", "headings")
            or "heading" in str(f.get("id", "")).lower()
            or "rule" in str(f.get("method", "")).lower()
        ):
            heading_contaminants += 1

    assert heading_contaminants == 0, f"HARD GATE VIOLATION: Found {heading_contaminants} heading records in ontology!"
    assert statuses == {"CERTIFIED", "CANDIDATE"}, f"Unexpected statuses in ontology: {statuses}"
    # Verify that ontology_facts.facts() filters strictly for CERTIFIED facts
    assert all(f.get("status") == "CERTIFIED" for f in ontology_facts.facts())


# ==============================================================================
# Barrier 3: AST Static Isolation
# ==============================================================================

def test_barrier3_ast_static_isolation():
    """Verify statically via AST that rag/hops.py and rag/answer.py never import rag.headings."""
    for filename in ("rag/hops.py", "rag/answer.py"):
        filepath = Path(filename)
        assert filepath.exists()
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=filename)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "headings" not in alias.name, f"{filename} forbidden import of {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert "headings" not in mod, f"{filename} forbidden from-import from {mod}"
                for alias in node.names:
                    assert "headings" not in alias.name, f"{filename} forbidden from-import name {alias.name}"

        # Source code string check
        src = filepath.read_text(encoding="utf-8")
        assert "rag.headings" not in src, f"{filename} contains forbidden string 'rag.headings'"
        assert "headings." not in src, f"{filename} contains forbidden string 'headings.'"


# ==============================================================================
# Barrier 4: Poisoning Test
# ==============================================================================

def test_barrier4_poisoning_isolation(monkeypatch):
    """Verify that execution of hops.plan does not invoke any callable in rag.headings."""
    def poison_trap(*args, **kwargs):
        raise AssertionError("POISON TRAP TRIGGERED: rag.headings was called during multihop execution!")

    # Poison every public callable in rag.headings
    for name, fn in list(vars(headings).items()):
        if callable(fn) and not name.startswith("__") and getattr(fn, "__module__", "") == headings.__name__:
            monkeypatch.setattr(headings, name, poison_trap)

    # Execute hops.plan on test questions; must not trigger poison trap
    plan = hops.plan("What is the treatment for Asthma?")
    assert plan is not None
    assert isinstance(plan.graph_facts, list)

    plan_case = hops.plan("A 45-year-old male presents with acute shortness of breath and wheezing.")
    assert plan_case is not None


# ==============================================================================
# Barrier 5: Prompt Inspection
# ==============================================================================

class _FakeHit:
    def __init__(self, id):
        self.id, self.similarity, self.passage, self.meta = id, 0.9, f"textbook passage {id}", {"book_id": "b", "book": "B"}

    def citation(self):
        return f"Book > {self.id}"


CERTIFIED_LINES = ["Textbook ontology: first-line treatment for Dengue fever: Paracetamol (Harrison, p. 1).",
                   "WARNING (textbook ontology): Aspirin is contraindicated in Dengue fever (Harrison, p. 2)."]
SENTINEL = "ZZHEADINGSENTINELZZ"


def test_barrier5_prompt_inspection_no_heading_leak(monkeypatch):
    """Run the real hops.plan and answer_multihop with stubbed retrieval and chat. Plant heading records that carry a
    sentinel and make every rag.headings query API return them: nothing heading-derived may reach graph_facts or the prompt."""
    all_rows = headings.all_headings()
    assert all_rows, "headings.jsonl is empty"
    planted = [dict(r, clean=SENTINEL, raw=SENTINEL, concept_label=SENTINEL) for r in all_rows[:20]]
    for name in ("primary_topic", "section_heading", "headings_for_concept", "facets_for", "subtopics",
                 "part_of_candidates", "parenthetical_aliases", "cross_book_headings", "all_headings"):
        monkeypatch.setattr(headings, name, lambda *a, **k: planted)
    monkeypatch.setattr(headings, "_load", lambda: (planted, {}, {}, {}, {}, {}))

    monkeypatch.setattr(hops, "link_entities", lambda q: [{"name": "Fever", "type": "Symptom", "ids": ["s1"]},
                                                          {"name": "Rash", "type": "Symptom", "ids": ["s2"]}])
    pool = [{"id": "c1", "name": "Dengue fever", "symptoms_matched": 2, "score": 6, "spec": 1.0}]
    monkeypatch.setattr(hops, "conditions_for_symptoms", lambda ids, top=5: [dict(c) for c in pool])
    monkeypatch.setattr(hops, "specialities_for", lambda cid: ["Infectious disease"])
    monkeypatch.setattr(hops, "drugs_for", lambda cid: [])
    monkeypatch.setattr(hops, "search", lambda q, k=5: [_FakeHit("a"), _FakeHit("b")])
    monkeypatch.setattr(hops, "mentions", lambda h, c: True)
    monkeypatch.setattr(hops, "names_condition", lambda h, c: True)
    monkeypatch.setattr(hops.ontology_facts, "available", lambda: True)
    monkeypatch.setattr(hops.ontology_facts, "match_conditions", lambda n: ["Dengue fever"])
    monkeypatch.setattr(hops.ontology_facts, "graph_facts_for", lambda n: list(CERTIFIED_LINES))

    prompts: list[str] = []
    monkeypatch.setattr(answer, "chat", lambda system, user, **kw: prompts.append(user) or "Paracetamol [G1] [1].")

    question = "Fever and rash after a mosquito bite, what is the diagnosis?"
    p = hops.plan(question)
    res = answer.answer_multihop(question)
    assert prompts, "the stubbed chat was never called"
    prompt = prompts[0]

    forbidden = [SENTINEL] + [r["heading_id"] for r in all_rows] + [
        "rule1:", "rule2:", "rule3:", "rule4:", "rule5:", "rule6:", "rule8:", "heading_id", "subtopic_of", "facet:",
    ]
    for plan_obj in (p, res.plan):
        for line in plan_obj.graph_facts:
            for bad in forbidden:
                assert bad not in line, f"heading-derived text {bad!r} in graph_facts"
    for bad in forbidden:
        assert bad not in prompt, f"heading-derived text {bad!r} in the answer prompt"
    assert "[G1] " in prompt and any(line in prompt for line in CERTIFIED_LINES)


# ==============================================================================
# Functional Tests for rag/headings.py Query APIs
# ==============================================================================

def test_clean_heading():
    """Verify cleaning of prefixes, chapter numbering, roman numerals, and capitalization."""
    assert headings.clean_heading("1 Fundamentals of Medicine") == "Fundamentals of Medicine"
    assert headings.clean_heading("SECTION 1: CLINICAL MEDICINE") == "Clinical medicine"
    assert headings.clean_heading("Part IV. Respiratory Disorders") == "Respiratory Disorders"
    assert headings.clean_heading("52. Jaundice.") == "Jaundice"
    assert headings.clean_heading("IV. The Cranial Nerves") == "The Cranial Nerves"


def test_paren_split():
    """Verify extraction of main term and parenthetical qualifiers."""
    main, par = headings.paren_split("Rifampin (Rifampicin, R)")
    assert main == "Rifampin"
    assert par == ["Rifampicin, R"]

    main, par = headings.paren_split("Amphotericin B (AMB)")
    assert main == "Amphotericin B"
    assert par == ["AMB"]

    main, par = headings.paren_split("Lungs")
    assert main == "Lungs"
    assert par == []


def test_facet_protection_hard_gate():
    """Verify generic structural headings are ALWAYS classified as facet and never as entities."""
    for word in ("Joints", "Nerves", "Arteries", "Toxicity", "Muscles", "Innervation", "Bones"):
        r = {"clean": word, "book": "grays", "level": 3, "match": "exact", "mtypes": ["AnatomicalStructure"], "n_children": 0}
        cls, ty = headings.classify_heading(r)
        assert cls == "facet", f"Hard gate failed: '{word}' classified as '{cls}', expected 'facet'"
        assert ty is None


def test_primary_topic_query():
    """Verify primary_topic query API."""
    # Matched section with same-section fact
    pt = headings.primary_topic("davidson/020-the-inflammatory-response")
    assert pt is not None
    assert pt["class"] == "matched"
    assert pt["tier"] == "T2"
    assert pt["concept_label"] == "Inflammatory response"
    assert "MED:OKF/physiologicalprocess/inflammatory-response" in pt["concept_ids"]

    # Single-word generic bridge with no fact in same book
    all_bridges = [r for r in headings.all_headings() if r.get("method") == "rule1:heading-bridge" and r.get("section_id")]
    if all_bridges:
        bridge_sec = all_bridges[0]["section_id"]
        # Default allow_bridge=False returns None
        assert headings.primary_topic(bridge_sec, allow_bridge=False) is None
        # allow_bridge=True returns record
        assert headings.primary_topic(bridge_sec, allow_bridge=True) is not None

    # Facet section has no primary topic
    assert headings.primary_topic("davidson/001-1-clinical-decision-making-overview") is None
    # Unknown section returns None
    assert headings.primary_topic("non_existent_book/999") is None


def test_section_heading_query():
    """Verify section_heading query API."""
    sh = headings.section_heading("davidson/001-1-clinical-decision-making-overview")
    assert sh is not None
    assert sh["clean"] == "Overview"
    assert sh["class"] == "facet"
    assert sh["tier"] == "navigation"
    assert headings.section_heading("invalid_section") is None


def test_headings_for_concept_query():
    """Verify headings_for_concept query API."""
    cid = "MED:OKF/physiologicalprocess/inflammatory-response"
    recs = headings.headings_for_concept(cid)
    assert len(recs) >= 1
    assert any(r["section_id"] == "davidson/020-the-inflammatory-response" for r in recs)


def test_facets_for_and_subtopics_query():
    """Verify facets_for and subtopics query APIs."""
    sh = headings.section_heading("davidson/001-1-clinical-decision-making-overview")
    assert sh is not None
    pid = sh["parent_id"]
    assert pid is not None

    facets = headings.facets_for(pid)
    assert any(f["clean"] == "Overview" for f in facets)

    sub = headings.subtopics(pid)
    assert len(sub) >= 1
    # By default, facet is not included in subtopics
    assert not any(s["class"] == "facet" for s in sub)

    sub_with_facets = headings.subtopics(pid, include_facets=True)
    assert len(sub_with_facets) > len(sub)


def test_part_of_candidates_query():
    """Verify Gray's anatomy part_of candidates query API."""
    parts = headings.part_of_candidates("grays")
    assert parts, "expected Gray's part_of candidates"
    for cand in parts:
        assert cand["book"] == "grays"
        assert cand["tier"] == "T3"
        assert cand["method"] == "rule4:part_of"
        assert cand["child_id"]
        assert cand["parent_id"]


def test_parenthetical_aliases_query():
    """Verify parenthetical_aliases query API."""
    aliases = headings.parenthetical_aliases()
    assert len(aliases) == 98
    abbrevs = [a for a in aliases if a["abbreviations"]]
    syns = [a for a in aliases if a["synonyms"]]
    alias_only = [a for a in aliases if a["alias_only_match"]]
    merge_props = [a for a in aliases if a["merge_proposal"]]

    assert len(abbrevs) >= 30
    assert len(syns) >= 16
    assert len(alias_only) == 13
    assert len(merge_props) == 7


def test_cross_book_headings_query():
    """Verify cross_book_headings query API."""
    cb = headings.cross_book_headings()
    assert len(cb) == 64
    for item in cb:
        assert len(item["books"]) >= 2
        assert item["tier"] == "T2"

    matched_cb = [c for c in cb if c["in_ontology"]]
    assert len(matched_cb) == 37


def test_all_headings_query():
    """Verify all_headings query and filtering API."""
    all_h = headings.all_headings()
    assert all_h
    grays = headings.all_headings(book="grays")
    assert grays and all(r["book"] == "grays" for r in grays)
    assert len(grays) < len(all_h)
    facets = headings.all_headings(cls="facet")
    assert facets and all(r["class"] == "facet" for r in facets)
    assert sum(len(headings.all_headings(book=b)) for b in headings.BOOKS) == len(all_h)


# ==============================================================================
# Stage A defect fixes
# ==============================================================================

def test_strip_possessive_and_numbering():
    assert headings.strip_possessive("Hodgkin's Lymphoma") == "Hodgkin Lymphoma"
    assert headings.strip_possessive("Parkinson’s Disease") == "Parkinson Disease"
    assert headings.clean_heading("17a. Introduction") == "Introduction"
    assert headings.clean_heading("41b. Diuretics") == "Diuretics"
    assert headings.clean_heading("3D imaging") == "3D imaging"


def test_type_guard_applies_to_single_candidate():
    cands = [("n1", "Pulmonary valve replacement", "TherapeuticAgent")]
    monkey_match = ("exact", {"TherapeuticAgent"}, cands)
    orig = headings.match_heading
    headings.match_heading = lambda h: monkey_match
    try:
        assert headings.match_heading_for_book("grays", "Pulmonary valve")[0] is None
        assert headings.match_heading_for_book("tripathi", "Pulmonary valve")[2] == cands
    finally:
        headings.match_heading = orig
    for r in headings.all_headings(book="grays", cls="matched"):
        assert r["concept_ids"]
        assert "replacement" not in (r["concept_label"] or "").lower()


def test_grays_bone_and_fascia_are_not_facets_but_bones_is():
    base = {"book": "grays", "level": 4, "n_children": 0}
    for word in ("Bone", "Fascia"):
        cls, _ = headings.classify_heading(dict(base, clean=word))
        assert cls != "facet", word
    cls, _ = headings.classify_heading(dict(base, clean="Bones"))
    assert cls == "facet"
    cls, _ = headings.classify_heading(dict(base, clean="Fascia", book="tripathi"))
    assert cls == "facet"


def test_dpp4_class_does_not_match_the_enzyme():
    rec = next(r for r in headings.all_headings(book="tripathi") if "DPP-4" in r["clean"])
    assert "dipeptidyl peptidase 4" not in (rec["concept_label"] or "").lower() or rec["class"] != "matched"
    assert (rec["concept_label"] or "").strip().lower() != "dpp-4"
