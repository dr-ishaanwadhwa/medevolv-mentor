"""Chunking, parsing and graph logic (synthetic inputs; graph tests skip if BODHI isn't downloaded)."""
from pathlib import Path

import pytest

from rag.answer import PERSONAL, _cited
from rag.chunk import Section, chunk_section
from stair.make_pairs import longest_copy, parse_questions


def _sec(body):
    return Section({"id": "b/001-x", "title": "1. Chapter", "chapter": "1. Chapter", "book_id": "b", "book": "Book",
                    "subject": "S", "section_path": ["Book", "1. Chapter"], "pages": [1, 2]}, body)


def test_chunker_respects_headings_and_size():
    para = " ".join(["alpha"] * 120)
    body = "\n\n".join([para, "### Mechanism of action", para, para, para, "#### Uses", para])
    chunks = chunk_section(_sec(body), target_words=250)
    assert all(len(c.passage.split()) <= 250 + 120 for c in chunks)
    assert {c.meta["heading"] for c in chunks} >= {"Mechanism of action", "Uses"}
    assert all(c.text.startswith("1. Chapter") for c in chunks)          # heading context embedded
    assert len({c.id for c in chunks}) == len(chunks)


def test_parse_questions_handles_json_and_junk():
    good = '{"questions": ["What is the first-line drug for absence seizures?", "Too short?", "No question mark"]}'
    assert parse_questions(good) == ["What is the first-line drug for absence seizures?"]
    broken = 'Sure! {"questions": ["Which receptor does atropine block in the eye?",'
    assert parse_questions(broken) == ["Which receptor does atropine block in the eye?"]


def test_longest_copy():
    passage = "the quick brown fox jumps over the lazy dog near the river bank today"
    assert longest_copy("Why does the quick brown fox jump?", passage) == 4     # "the quick brown fox"
    assert longest_copy("the quick brown fox jumps over the lazy dog near here?", passage) == 10


@pytest.mark.parametrize("q,personal", [
    ("My mother has TB, how much rifampicin should she take?", True),
    ("Should I take ibuprofen for my headache?", True),
    ("What is the dose of rifampicin in tuberculosis?", False),
    ("A patient with fever and rash — likely diagnosis?", False),
])
def test_personal_advice_guard(q, personal):
    assert bool(PERSONAL.search(q)) is personal


def test_citation_parsing():
    text = "Ethosuximide [3]. Also valproate [1, 2] and [9]. Graph says [G2, G4]."
    assert _cited(text, r"\[([\d,\s]+)\]", 6) == [1, 2, 3]
    assert _cited(text, r"\[(G\d+(?:\s*,\s*G?\d+)*)\]", 5) == [2, 4]


bodhi = pytest.mark.skipif(not Path("data/bodhi/BODHI-S/data/triples.jsonl").exists(),
                           reason="BODHI not downloaded (python -m ingest.fetch_bodhi)")


@bodhi
def test_entity_linking_exact_lay_and_no_false_bite():
    from rag.graph import link_entities
    names = {e["name"] for e in link_entities("A patient presents with fever, joint pain and rash.")}
    assert {"Fever", "Joint pain", "Skin rash"} <= names
    assert not any("Seizure" in e["name"] for e in link_entities("fever after a mosquito bite"))
    assert link_entities("What is the mechanism of action of penicillin?") == []


@bodhi
def test_symptoms_rank_arboviral_conditions():
    from rag.graph import conditions_for_symptoms, link_entities
    ents = link_entities("high fever, headache and joint pain after a mosquito bite")
    top = [c["name"] for c in conditions_for_symptoms([e["ids"] for e in ents if e["type"] == "Symptom"], top=5)]
    assert {"Chikungunya fever", "Dengue fever"} <= set(top)


def test_clean_strips_echoed_headers():
    from rag.answer import clean
    assert clean("[1] (Robbins, 2 Cell › Morphology (pp. 52-61))\n\nThe area is grey [1].") == "The area is grey [1]."
    assert clean("[3] [8]\n\nValproate [3].") == "Valproate [3]."
    assert clean("Valproate is the drug of choice [2].") == "Valproate is the drug of choice [2]."


def test_graph_route_only_for_case_questions():
    from rag.hops import is_case
    one = [{"name": "Seizure"}]
    assert not is_case("What is the drug of choice for absence seizures?", one)
    assert is_case("A 30 year old presents with seizures. Likely diagnosis?", one)
    assert is_case("fever and joint pain", [{"name": "Fever"}, {"name": "Joint pain"}])
    assert not is_case("Mechanism of penicillin", [])
