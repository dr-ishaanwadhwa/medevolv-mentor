"""Rebuild a missing ToC from printed heading fonts, then write the OKF bundle at heading granularity.

For books whose PDF bookmarks stop at chapter level (e.g. KD Tripathi 7th ed.). Chapters still come from the
bookmarks; inside each chapter, headings are recognised by typography:

  major heading   bold, body-size, ALL CAPS       e.g. "PENICILLINS", "SEMISYNTHETIC PENICILLINS"
  sub-heading     bold, body-size, mixed case     e.g. "Mechanism of action", "Carbamazepine"
                  (also run-in heads: a bold phrase starting a paragraph)
  ignored         other sizes (SECTION/CHAPTER tabs, TABLE labels, figure captions, boxes), running headers

Each chapter is split at its major headings (or at sub-headings if it has no major ones). Text before the first
heading becomes an "Overview" section. Sub-headings stay inside the section as "### " lines, so the chunker can
attach them to passages. Pages are two-column, so blocks are read column by column.

Usage:
  python -m ingest.font_toc data/books/978-93-5025-937-5.pdf --book-id tripathi \
      --title "Essentials of Medical Pharmacology (7th ed.)" --subject Pharmacology --isbn 978-93-5025-937-5 \
      --parent-pattern "^(Section \\d+:|Appendices$)"
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pymupdf

from ingest.pdf_to_okf import (DEFAULT_SKIP, EDGE_BAND, MARGIN_TAB, effective_toc, norm, running_edges,
                               slugify, yaml_front)

BODY_SIZE = (9.6, 10.4)          # Tripathi body and heading text are 10pt; headings differ by weight/case
MIN_SECTION_WORDS = 60           # smaller sections are folded into the next one
NOISE = re.compile(r"^(fig\.?|figure|table|box|problem directed study)\b", re.I)
ENUM_ONLY = re.compile(r"^([IVX]+|\d+|[a-z])[.)]$", re.I)
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with", "vs"}


def is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower()


def body_sized(span: dict) -> bool:
    return BODY_SIZE[0] <= span["size"] <= BODY_SIZE[1]


def clean_title(t: str) -> str:
    t = " ".join(t.split())
    t = re.sub(r"^((?:\d+|[IVX]+)\.)(?=\S)", r"\1 ", t)          # "1.CNS" -> "1. CNS"
    return t.strip(" :–-")


def is_upper(t: str) -> bool:
    letters = [c for c in t if c.isalpha()]
    return len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) > 0.8


def smart_title(t: str) -> str:
    """'PENICILLIN-G (BENZYL PENICILLIN)' -> 'Penicillin-G (Benzyl Penicillin)'; mixed case is kept.
    'ANTICHOLINERGIC DRUGS (Muscarinic ...)' -> only the capitalised part before the bracket is changed."""
    if not is_upper(t):
        head, sep, tail = t.partition("(")
        return (smart_title(head.strip()) + " " + sep + tail).strip() if sep and is_upper(head) else t
    def piece(p: str, first: bool) -> str:
        core = re.sub(r"[^A-Za-z]", "", p)
        if 2 <= len(core) <= 3 and core.lower() not in SMALL_WORDS:
            return p                                      # acronyms: CHF, ACE, TB, CNS stay upper-case
        if not first and p.lower() in SMALL_WORDS:
            return p.lower()
        return re.sub(r"[A-Za-z]", lambda m: m.group(0).upper(), p.lower(), count=1)

    out = []
    for i, w in enumerate(t.split()):
        parts = re.split(r"([-(/])", w)                   # title-case each piece of "ANTI-TB", "(BENZYL"
        out.append("".join(x if x in "-(/" else piece(x, i == 0) for x in parts))
    return " ".join(out)


def block_text(lines: list[list[dict]]) -> str:
    text = "\n".join("".join(s["text"] for s in sl) for sl in lines)
    text = re.sub(r"-\n(?=[a-z])", "", text)
    return " ".join(text.split())


def page_items(page: pymupdf.Page, edges: set[str]) -> list[tuple]:
    """Return ('h', title, is_runin) / ('p', text) items for one page in reading order."""
    h, w = page.rect.height, page.rect.width
    blocks = [b for b in page.get_text("dict")["blocks"] if b["type"] == 0]
    col = lambda b: 0 if b["bbox"][0] < w / 2 - 10 else 1
    blocks.sort(key=lambda b: (col(b), b["bbox"][1]))

    items: list[tuple] = []
    for b in blocks:
        lines = [[s for s in l["spans"] if s["text"].strip()] for l in b["lines"]]
        lines = [sl for sl in lines if sl]
        if not lines:
            continue
        raw = block_text(lines)
        y0, y1 = b["bbox"][1], b["bbox"][3]
        if (y1 < h * EDGE_BAND or y0 > h * (1 - EDGE_BAND)) and (norm(raw) in edges or raw.isdigit()):
            continue
        raw = MARGIN_TAB.sub("", raw).strip()
        if not raw:
            continue
        spans = [s for sl in lines for s in sl]

        # Whole block is a heading
        if all(is_bold(s) and body_sized(s) for s in spans) and len(raw.split()) <= 15 and not NOISE.match(raw):
            items.append(("h", clean_title(raw), False))
            continue

        # Run-in heading: leading bold body-size spans, then regular text on the same line
        lead = []
        for s in lines[0]:
            if is_bold(s) and body_sized(s):
                lead.append(s)
            else:
                break
        lead_txt = clean_title("".join(s["text"] for s in lead))
        if lead and len(lead) < len(lines[0]) and 1 <= len(lead_txt.split()) <= 6 and not NOISE.match(lead_txt):
            items.append(("h", lead_txt, True))
            rest = [lines[0][len(lead):]] + lines[1:]
            items.append(("p", block_text(rest)))
        else:
            items.append(("p", raw))
    return items


def tidy(items: list[tuple[tuple, int]]) -> list[tuple[tuple, int]]:
    """Join split headings: 'I.' + 'As antisecretory', and '(Muscarinic receptor antagonists...)' continuations.
    Items are (item, page) pairs; pages pass through unchanged."""
    out: list[tuple[tuple, int]] = []
    prefix = ""
    for it, page in items:
        if it[0] == "h" and ENUM_ONLY.match(it[1]):
            prefix = it[1] + " "
            continue
        if it[0] == "h" and not it[2] and out and out[-1][0][0] == "h" and not out[-1][0][2]:
            prev, prev_page = out[-1]
            unclosed = prev[1].count("(") > prev[1].count(")")
            continues = (it[1].startswith("(") or it[1][:1].islower() or prev[1].endswith((",", "and", "of", "&"))
                         or (is_upper(prev[1]) and is_upper(it[1])))   # "DRUGS ACTING ON AUTONOMIC" + "GANGLIA"
            if unclosed or continues:                     # one heading wrapped across two text blocks
                out[-1] = (("h", prev[1] + " " + it[1], prev[2]), prev_page)
                continue
        if it[0] == "h" and prefix:
            it = ("h", prefix + it[1], it[2])
        prefix = ""
        out.append((it, page))
    return out


MAX_SECTION_WORDS = 2500        # bigger sections are split again at their sub-headings


def heading_kind(it: tuple) -> str:
    """major = bold ALL CAPS block heading; h3 = bold mixed-case block heading; h4 = run-in bold phrase."""
    if it[2]:
        return "h4"
    return "major" if is_upper(it[1].split("(")[0]) else "h3"   # judge case before any parenthetical


def _words(body: list[tuple]) -> int:
    return sum(len(t.split()) for t, _, kind in body if kind == "p")


def _split(body: list[tuple], title: str, parent: str | None, page: int | None, on: str) -> list[dict]:
    secs = [{"title": title, "parent": parent, "page": page, "body": []}]
    for e in body:
        if e[2] == on:
            secs.append({"title": e[0], "parent": parent, "page": e[1], "body": []})
        else:
            secs[-1]["body"].append(e)
    return secs


def _fold_tiny(secs: list[dict]) -> list[dict]:
    """Fold sections with < MIN_SECTION_WORDS of text into the next one (their title becomes a sub-heading)."""
    out, carry = [], None
    for s in secs:
        if carry:
            lead = [] if carry["title"] == "Overview" else [(carry["title"], carry["page"], "h3")]
            s["body"] = lead + carry["body"] + s["body"]
            s["page"] = carry["page"] or s["page"]
            carry = None
        if _words(s["body"]) < MIN_SECTION_WORDS:
            carry = s
            continue
        out.append(s)
    if carry:
        if out:
            out[-1]["body"] += ([] if carry["title"] == "Overview" else [(carry["title"], carry["page"], "h3")]) + carry["body"]
        else:
            out.append(carry)
    return out


def split_chapter(items: list[tuple[tuple, int]]) -> list[dict]:
    """Split a chapter's (item, page) stream into sections.

    Level 1: split at ALL-CAPS headings if the chapter has any, else at mixed-case headings.
    Level 2: any section still over MAX_SECTION_WORDS is split again at its mixed-case headings.
    """
    stream = [((smart_title(it[1]), page, heading_kind(it)) if it[0] == "h" else (it[1], page, "p"))
              for it, page in items]
    top = "major" if any(k == "major" for _, _, k in stream) else "h3"
    sections = _fold_tiny(_split(stream, "Overview", None, None, top))

    final = []
    for s in sections:
        if top == "major" and _words(s["body"]) > MAX_SECTION_WORDS and any(k == "h3" for *_, k in s["body"]):
            parent = None if s["title"] == "Overview" else s["title"]
            subs = _fold_tiny(_split(s["body"], s["title"], parent, s["page"], "h3"))
            subs[0]["parent"] = None   # the first piece keeps the original section's own title
            final += subs
        else:
            final.append(s)

    rendered = []
    for s in final:
        lines, pages = [], [s["page"]] if s["page"] else []
        for text, page, kind in s["body"]:
            lines.append(text if kind == "p" else ("#### " if kind == "h4" else "### ") + text)
            pages.append(page)
        if pages:
            rendered.append({"title": s["title"], "parent": s["parent"], "body": lines, "pages": pages})
    return rendered


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--isbn", default="")
    ap.add_argument("--parent-pattern", default=None)
    ap.add_argument("--skip-pattern", default=DEFAULT_SKIP)
    ap.add_argument("--out", default="data/okf")
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    parent_re = re.compile(a.parent_pattern, re.I) if a.parent_pattern else None
    skip_re = re.compile(a.skip_pattern, re.I)
    entries = effective_toc(doc.get_toc(simple=True), parent_re)
    chapter_level = 2 if parent_re else 1
    edges = running_edges(doc)

    out = Path(a.out) / a.book_id
    (out / "sections").mkdir(parents=True, exist_ok=True)
    for old in (out / "sections").glob("*.md"):
        old.unlink()

    toc_json, index_lines, n, n_chapters = [], [], 0, 0
    for i, e in enumerate(entries):
        if e["parent"]:
            index_lines.append(f"\n## {e['title']}\n")
            continue
        if e["level"] != chapter_level or skip_re.search(e["title"]):
            continue
        nxt = next((x for x in entries[i + 1:] if x["level"] <= e["level"]), None)
        start, end = e["page"], max(e["page"], (nxt["page"] - 1) if nxt else doc.page_count)

        items = []
        for p in range(start, end + 1):
            items += [(it, p) for it in page_items(doc[p - 1], edges)]
        sections = split_chapter(tidy(items))
        if not sections:
            continue
        n_chapters += 1
        index_lines.append(f"- **{e['title']}** (pp. {start}–{end})")
        for s in sections:
            n += 1
            body = "\n\n".join(s["body"])
            sid = f"{a.book_id}/{n:04d}-{slugify(e['title'], 30)}-{slugify(s['title'], 30)}"
            path = [a.title] + e["path"] + ([s["parent"]] if s["parent"] else []) + [s["title"]]
            front = {
                "type": "textbook-section",
                "id": sid,
                "title": s["title"],
                "chapter": e["title"],
                "book_id": a.book_id,
                "book": a.title,
                "subject": a.subject,
                "isbn": a.isbn,
                "section_path": path,
                "level": "heading",
                "pages": [min(s["pages"]), max(s["pages"])],
                "words": len(body.split()),
                "source": Path(a.pdf).name,
                "toc_source": "font-reconstructed",
                "license": "copyrighted; local study use only; do not redistribute",
            }
            fname = sid.split("/", 1)[1] + ".md"
            (out / "sections" / fname).write_text(yaml_front(front) + f"\n# {s['title']}\n\n{body}\n")
            toc_json.append({"id": sid, "chapter": e["title"], "path": " › ".join(path),
                             "pages": front["pages"]})
            index_lines.append(f"  - [{s['title']}](sections/{fname}) (pp. {front['pages'][0]}–{front['pages'][1]})")

    index = yaml_front({"type": "index", "book_id": a.book_id, "book": a.title, "subject": a.subject,
                        "chapters": n_chapters, "sections": n, "toc_source": "font-reconstructed"})
    (out / "index.md").write_text(index + f"\n# {a.title}\n" + "\n".join(index_lines) + "\n")
    (out / "toc.json").write_text(json.dumps(toc_json, indent=1, ensure_ascii=False))
    print(f"{n_chapters} chapters -> {n} heading-level sections -> {out}/")


if __name__ == "__main__":
    main()
