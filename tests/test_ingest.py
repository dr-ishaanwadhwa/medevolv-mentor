"""Ingestion logic on synthetic PDFs and strings (no textbook content in the test suite)."""
import pymupdf
import pytest

from ingest.font_toc import heading_kind, smart_title, split_chapter, tidy
from ingest.pdf_to_okf import effective_toc, position, slice_text


@pytest.mark.parametrize("raw,expected", [
    ("TREATMENT OF CHF", "Treatment of CHF"),
    ("SECOND LINE ANTI-TB DRUGS", "Second Line Anti-TB Drugs"),
    ("PENICILLIN-G (BENZYL PENICILLIN)", "Penicillin-G (Benzyl Penicillin)"),
    ("ANTICHOLINERGIC DRUGS (Muscarinic receptor antagonists)", "Anticholinergic Drugs (Muscarinic receptor antagonists)"),
    ("Mechanism of action", "Mechanism of action"),          # mixed case is left alone
])
def test_smart_title(raw, expected):
    assert smart_title(raw) == expected


def test_tidy_joins_wrapped_and_enumerated_headings():
    items = [(("h", "I.", False), 1), (("h", "As antisecretory", False), 1),
             (("h", "DRUGS ACTING ON AUTONOMIC", False), 2), (("h", "GANGLIA", False), 2),
             (("h", "ANTICHOLINERGIC DRUGS (Muscarinic", False), 3), (("h", "receptor antagonists)", False), 3)]
    titles = [it[1] for it, _ in tidy(items)]
    assert titles == ["I. As antisecretory", "DRUGS ACTING ON AUTONOMIC GANGLIA",
                      "ANTICHOLINERGIC DRUGS (Muscarinic receptor antagonists)"]


def test_heading_kind():
    assert heading_kind(("h", "SEMISYNTHETIC PENICILLINS", False)) == "major"
    assert heading_kind(("h", "ANTICHOLINERGIC DRUGS (Muscarinic receptor antagonists)", False)) == "major"
    assert heading_kind(("h", "Adverse effects", False)) == "h3"
    assert heading_kind(("h", "Chemistry", True)) == "h4"


def _words(n):
    return " ".join(["word"] * n)


def test_split_chapter_splits_at_majors_and_folds_tiny_sections():
    items = [(("p", _words(80)), 1),
             (("h", "FIRST TOPIC", False), 1), (("p", _words(100)), 1),
             (("h", "Uses", False), 2), (("p", _words(30)), 2),
             (("h", "TINY TOPIC", False), 3), (("p", _words(10)), 3),
             (("h", "LAST TOPIC", False), 3), (("p", _words(100)), 4)]
    secs = split_chapter(items)
    assert [s["title"] for s in secs] == ["Overview", "First Topic", "Last Topic"]
    assert "### Uses" in secs[1]["body"]                     # mixed-case heading stays inside its section
    assert "### Tiny Topic" in secs[2]["body"]               # <60-word section folded into the next one
    assert secs[2]["pages"][0] == 3


def test_split_chapter_without_majors_splits_on_subheadings():
    items = [(("h", "Phenytoin", False), 1), (("p", _words(100)), 1),
             (("h", "Carbamazepine", False), 2), (("p", _words(100)), 2)]
    assert [s["title"] for s in split_chapter(items)] == ["Phenytoin", "Carbamazepine"]


@pytest.fixture
def two_column_pdf(tmp_path):
    """3 pages; section B starts mid-page in the right column of page 2."""
    doc = pymupdf.open()
    for p in range(3):
        page = doc.new_page(width=600, height=800)
        page.insert_textbox(pymupdf.Rect(40, 120, 290, 700), f"left column page {p + 1} " + _words(40))
        page.insert_textbox(pymupdf.Rect(310, 120, 560, 700), f"right column page {p + 1} " + _words(40))
    # Bookmarks: B points at the right column of page 2, 120pt from the top (bookmark y is from the page bottom).
    doc.set_toc([[1, "A", 1, {"kind": pymupdf.LINK_GOTO, "page": 0, "to": pymupdf.Point(40, 800 - 110)}],
                 [1, "B", 2, {"kind": pymupdf.LINK_GOTO, "page": 1, "to": pymupdf.Point(310, 800 - 110)}]])
    path = tmp_path / "t.pdf"
    doc.save(path)
    return pymupdf.open(path)


def test_position_reads_bookmark_from_page_bottom(two_column_pdf):
    entries = effective_toc(two_column_pdf.get_toc(simple=False), None)
    page, col, y = position(two_column_pdf, entries[1])
    assert (page, col) == (2, 1) and 100 < y < 120


def test_slice_text_splits_mid_page_without_duplication(two_column_pdf):
    entries = effective_toc(two_column_pdf.get_toc(simple=False), None)
    a, *_ = slice_text(two_column_pdf, set(), position(two_column_pdf, entries[0]),
                       position(two_column_pdf, entries[1]))
    b, *_ = slice_text(two_column_pdf, set(), position(two_column_pdf, entries[1]), None)
    assert "left column page 2" in a and "right column page 2" not in a
    assert "right column page 2" in b and "left column page 2" not in b
    assert "page 3" in b and "page 1" in a
