"""Turn a textbook PDF into an OKF bundle: one markdown file per ToC section, YAML frontmatter on each.

Usage:
  python -m ingest.pdf_to_okf data/books/978-93-5025-937-5.pdf \
      --book-id tripathi --title "Essentials of Medical Pharmacology (7th ed.)" \
      --subject Pharmacology --isbn 978-93-5025-937-5 \
      --level 1 --parent-pattern "^(Section \\d+:|Appendices$)"

Output (data/okf/<book-id>/, git-ignored):
  index.md            OKF reserved index: the book's ToC with links to every section
  sections/NNN-*.md   one OKF concept per target section (type: textbook-section)
  toc.json            [{id, path, pages}] -- the label set STAIR is trained to emit

How sections are chosen:
  --level N           ToC depth that becomes one section (1 = chapters in most books).
  --parent-pattern    For flat ToCs (e.g. KD Tripathi lists "Section 1: ..." and its chapters at the same
                      level): entries matching this regex act as parents of the entries that follow them.
  --skip-pattern      Front/back matter to drop (cover, preface, index, ...).
A section runs from its start page to the page before the next entry at the same or a higher level.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pymupdf

DEFAULT_SKIP = (r"^(front cover|cover|inside front cover|half title|title page|copyright|dedication|preface|"
                r"extract from preface|contents|table of contents|list of abbreviations|abbreviations|index|"
                r"selected references|references|activate your ebook|video and audio contents|contributors)")
EDGE_BAND = 0.13      # top/bottom fraction of the page where running headers/footers live
# Repeated side-tab labels ("Chapter Chapter Chapter 8 8 8") or a block that is only "Chapter 8".
# A single in-text "see Chapter 12" is left alone.
MARGIN_TAB = re.compile(r"\b(?:chapter\s+){2,}(?:\d+[a-z]?\b\s*)*$|^chapter\s+\d+[a-z]?$|^(?:chapter\s*){2,}$", re.I)
REPEAT_MIN = 5       # an edge block repeated this often across the book is a running header/footer


def slugify(s: str, n: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:n].rstrip("-")


def norm(s: str) -> str:
    """Normalise header/footer text so 'Page 114' and 'Page 115' compare equal."""
    return re.sub(r"\d+", "#", " ".join(s.split())).lower()


def effective_toc(toc: list[list], parent_re: re.Pattern | None) -> list[dict]:
    """Attach an effective level and ancestor path to every ToC entry."""
    out, stack, in_parent = [], [], False
    for raw_level, title, page, *dest in toc:              # dest present when get_toc(simple=False)
        title = " ".join(title.replace("​", "").split())
        is_parent = bool(parent_re and raw_level == 1 and parent_re.search(title))
        if is_parent:
            in_parent = True
            level = 1
        else:
            level = raw_level + (1 if in_parent and parent_re else 0)
        while stack and stack[-1]["level"] >= level:
            stack.pop()
        entry = {"level": level, "title": title, "page": page, "parent": is_parent,
                 "path": [s["title"] for s in stack] + [title],
                 "to": dest[0].get("to") if dest and isinstance(dest[0], dict) else None}
        stack.append(entry)
        out.append(entry)
    return out


def running_edges(doc: pymupdf.Document) -> set[str]:
    """Find repeated blocks in the top/bottom band (running headers, footers, page numbers)."""
    c = Counter()
    for page in doc:
        h = page.rect.height
        for x0, y0, x1, y1, text, *_ in page.get_text("blocks"):
            if y1 < h * EDGE_BAND or y0 > h * (1 - EDGE_BAND):
                c[norm(text)] += 1
    return {t for t, n in c.items() if n >= REPEAT_MIN}


def page_blocks(page: pymupdf.Page, edges: set[str]) -> list[tuple[int, float, str]]:
    """Cleaned text blocks as (column, y0, text), in reading order (left column top-down, then right)."""
    w = page.rect.width
    out = []
    for x0, y0, x1, y1, _text, _no, btype in page.get_text("blocks"):
        if btype != 0:
            continue
        text = page_text_block(page, (x0, y0, x1, y1, _text), edges)
        if text:
            out.append((0 if x0 < w / 2 - 10 else 1, y0, text))
    return sorted(out)


def page_text_block(page: pymupdf.Page, block: tuple, edges: set[str]) -> str:
    x0, y0, x1, y1, text = block
    h = page.rect.height
    if (y1 < h * EDGE_BAND or y0 > h * (1 - EDGE_BAND)) and (norm(text) in edges or text.strip().isdigit()):
        return ""
    text = re.sub(r"-\n(?=[a-z])", "", text)
    return MARGIN_TAB.sub("", " ".join(text.split())).strip()


def position(doc: pymupdf.Document, entry: dict) -> tuple[int, int, float]:
    """Sort key (page, column, y-from-top) of where a bookmark points. PDF bookmark points are measured
    from the page bottom; without one, the section starts at the top of its page."""
    page = doc[entry["page"] - 1]
    to = entry.get("to")
    if to is None:
        return (entry["page"], 0, 0.0)
    y = page.rect.height - to.y - 3            # small tolerance so the heading line itself is included
    return (entry["page"], 0 if to.x < page.rect.width / 2 - 10 else 1, max(y, 0.0))


def slice_text(doc: pymupdf.Document, edges: set[str], start: tuple, end: tuple | None) -> tuple[str, int, int]:
    """Text from start (inclusive) to end (exclusive) positions; returns (text, first_page, last_page)."""
    parts, pages = [], []
    last = end[0] if end else doc.page_count
    for p in range(start[0], last + 1):
        for col, y0, text in page_blocks(doc[p - 1], edges):
            key = (p, col, y0)
            if key < start or (end and key >= end):
                continue
            parts.append(text)
            pages.append(p)
    return "\n\n".join(parts), (min(pages) if pages else start[0]), (max(pages) if pages else start[0])


def yaml_front(d: dict) -> str:
    # JSON scalars/lists are valid YAML, which keeps quoting safe for titles with colons etc.
    return "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in d.items()) + "\n---\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--isbn", default="")
    ap.add_argument("--level", type=int, default=1)
    ap.add_argument("--parent-pattern", default=None)
    ap.add_argument("--skip-pattern", default=DEFAULT_SKIP)
    ap.add_argument("--also-skip", default=None, help="extra regex of titles to drop (with their children)")
    ap.add_argument("--chapter-level", type=int, default=None,
                    help="effective ToC level that holds chapter titles (stored as 'chapter' for citations)")
    ap.add_argument("--out", default="data/okf")
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    parent_re = re.compile(a.parent_pattern, re.I) if a.parent_pattern else None
    skip_re = re.compile(a.skip_pattern + (f"|{a.also_skip}" if a.also_skip else ""), re.I)
    entries = effective_toc(doc.get_toc(simple=False), parent_re)
    edges = running_edges(doc)

    out = Path(a.out) / a.book_id
    (out / "sections").mkdir(parents=True, exist_ok=True)
    for old in (out / "sections").glob("*.md"):
        old.unlink()

    toc_json, index_lines = [], []
    n = 0
    target = a.level + (1 if parent_re else 0)
    min_level = (a.chapter_level or 1)

    def emit(title: str, ancestors: list[str], text: str, start: int, end: int) -> None:
        nonlocal n
        n += 1
        sid = f"{a.book_id}/{n:03d}-{slugify(ancestors[-1] if title == 'Overview' else title)}"
        if title == "Overview":
            sid += "-overview"
        path = [a.title] + ancestors + ([title] if title != ancestors[-1] else [])
        cl = a.chapter_level
        chapter = ancestors[cl - 1] if cl and len(ancestors) >= cl else ancestors[-1]
        front = {
            "type": "textbook-section", "id": sid, "title": title, "chapter": chapter,
            "book_id": a.book_id, "book": a.title, "subject": a.subject, "isbn": a.isbn,
            "section_path": path, "level": a.level, "pages": [start, end], "words": len(text.split()),
            "source": Path(a.pdf).name, "license": "copyrighted; local study use only; do not redistribute",
        }
        fname = sid.split("/", 1)[1] + ".md"
        (out / "sections" / fname).write_text(yaml_front(front) + f"\n# {title}\n\n{text}\n")
        toc_json.append({"id": sid, "chapter": chapter, "path": " › ".join(path), "pages": [start, end]})
        index_lines.append(f"- [{title}](sections/{fname}) (pp. {start}–{end})")

    for i, e in enumerate(entries):
        if e["parent"]:
            index_lines.append(f"\n## {e['title']}\n")
            continue
        if e["level"] > target or e["level"] < min_level or any(skip_re.search(t) for t in e["path"]):
            continue
        nxt_any = entries[i + 1] if i + 1 < len(entries) else None
        nxt_same = next((x for x in entries[i + 1:] if x["level"] <= e["level"]), None)
        has_children = nxt_any is not None and nxt_any["level"] > e["level"]

        if e["level"] == target or not has_children:
            # A target-level section, or a shallower entry with no sub-bookmarks (whole chapter = one section).
            # It runs from its bookmark's exact position to the next bookmark at the same or a higher level.
            text, start, end = slice_text(doc, edges, position(doc, e),
                                          position(doc, nxt_same) if nxt_same else None)
            if len(text) >= 200:          # shorter = a bookmark with no real body (e.g. a divider page)
                emit(e["title"], e["path"], text, start, end)
        else:
            # Shallower entry with children: capture its intro text (before the first child) as "Overview".
            text, start, end = slice_text(doc, edges, position(doc, e), position(doc, nxt_any))
            if len(text.split()) >= 60:
                emit("Overview", e["path"], text, start, end)

    index = yaml_front({"type": "index", "book_id": a.book_id, "book": a.title, "subject": a.subject,
                        "sections": n}) + f"\n# {a.title}\n" + "\n".join(index_lines) + "\n"
    (out / "index.md").write_text(index)
    (out / "toc.json").write_text(json.dumps(toc_json, indent=1, ensure_ascii=False))
    print(f"{n} sections -> {out}/  (running headers/footers removed: {len(edges)} patterns)")


if __name__ == "__main__":
    main()
