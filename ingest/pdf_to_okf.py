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
    for raw_level, title, page in toc:
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
                 "path": [s["title"] for s in stack] + [title]}
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


def page_text(page: pymupdf.Page, edges: set[str]) -> str:
    h = page.rect.height
    parts = []
    for x0, y0, x1, y1, text, _no, btype in page.get_text("blocks"):
        if btype != 0:  # image block
            continue
        in_band = y1 < h * EDGE_BAND or y0 > h * (1 - EDGE_BAND)
        if in_band and (norm(text) in edges or text.strip().isdigit()):
            continue
        text = re.sub(r"-\n(?=[a-z])", "", text)        # re-join hyphenated words
        text = " ".join(text.split())
        text = MARGIN_TAB.sub("", text).strip()          # side-tab labels like "Chapter Chapter Chapter 8 8 8"
        if not text:
            continue
        parts.append(text)
    return "\n\n".join(p for p in parts if p)


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
    ap.add_argument("--out", default="data/okf")
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    parent_re = re.compile(a.parent_pattern, re.I) if a.parent_pattern else None
    skip_re = re.compile(a.skip_pattern, re.I)
    entries = effective_toc(doc.get_toc(simple=True), parent_re)
    edges = running_edges(doc)

    out = Path(a.out) / a.book_id
    (out / "sections").mkdir(parents=True, exist_ok=True)
    for old in (out / "sections").glob("*.md"):
        old.unlink()

    toc_json, index_lines = [], []
    n = 0
    for i, e in enumerate(entries):
        if e["parent"]:
            index_lines.append(f"\n## {e['title']}\n")
            continue
        if e["level"] != a.level + (1 if parent_re else 0) or skip_re.search(e["title"]):
            continue
        # End = page before the next entry at the same or a higher level.
        nxt = next((x for x in entries[i + 1:] if x["level"] <= e["level"]), None)
        start = e["page"]
        end = max(start, (nxt["page"] - 1) if nxt else doc.page_count)
        text = "\n\n".join(page_text(doc[p - 1], edges) for p in range(start, end + 1))
        if len(text) < 200:  # bookmark with no real body (e.g. a divider page)
            continue

        n += 1
        sid = f"{a.book_id}/{n:03d}-{slugify(e['title'])}"
        path = [a.title] + e["path"]
        front = {
            "type": "textbook-section",
            "id": sid,
            "title": e["title"],
            "book_id": a.book_id,
            "book": a.title,
            "subject": a.subject,
            "isbn": a.isbn,
            "section_path": path,
            "level": a.level,
            "pages": [start, end],
            "words": len(text.split()),
            "source": Path(a.pdf).name,
            "license": "copyrighted; local study use only; do not redistribute",
        }
        fname = f"{n:03d}-{slugify(e['title'])}.md"
        (out / "sections" / fname).write_text(yaml_front(front) + f"\n# {e['title']}\n\n{text}\n")
        toc_json.append({"id": sid, "path": " › ".join(path), "pages": [start, end]})
        index_lines.append(f"- [{e['title']}](sections/{fname}) (pp. {start}–{end})")

    index = yaml_front({"type": "index", "book_id": a.book_id, "book": a.title, "subject": a.subject,
                        "sections": n}) + f"\n# {a.title}\n" + "\n".join(index_lines) + "\n"
    (out / "index.md").write_text(index)
    (out / "toc.json").write_text(json.dumps(toc_json, indent=1, ensure_ascii=False))
    print(f"{n} sections -> {out}/  (running headers/footers removed: {len(edges)} patterns)")


if __name__ == "__main__":
    main()
