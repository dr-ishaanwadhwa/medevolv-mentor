"""Split Gray's Anatomy for Students (5th ed.) into heading-level OKF sections.

The PDF bookmarks only list the 9 regional chapters. Inside a chapter the book's own typography gives the hierarchy:

  part       Sense-Bold 18, grey     Conceptual overview / Regional anatomy / Surface anatomy / Clinical cases (Part I..XI in ch. 9)
  level 1    Sense-Medium 12 CAPS    e.g. PLEURAL CAVITIES
  level 2    Sense-Bold 12           e.g. Pleura
  level 3    Sense-Bold 11, grey     e.g. Parietal pleura
  level 4    MinionPro-Bold 10.5, grey   (stays inside its section as a "####" line)
  box        Sense-Bold 11 "In the clinic" + Sense-Bold 10 title; boxes stay in the section they sit in
  case       Sense-ExtraBold 12.5 "Case N" followed by the case title (Clinical cases part)

A node (part / heading) that is longer than MAX_WORDS is split at its children, recursively; shorter ones stay whole
with their sub-headings as "###" lines. Sections under MIN_WORDS are folded into their neighbour. Everything before
the first part heading of a chapter (title page, chapter ToC, learning-resources panel) is dropped, as are running
headers, page numbers, figure captions and figure labels (only Sense*/MinionPro* fonts are read).

Usage: python -m ingest.grays_toc data/books/978-0-323-93423-7.pdf --book-id grays \
         --title "Gray's Anatomy for Students (5th ed.)" --subject Anatomy --isbn 978-0-323-93423-7
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pymupdf

from ingest.pdf_to_okf import slugify, yaml_front

MAX_WORDS = 2500
MAX_PAGES = 10          # figure-heavy chapters have few words per page, so page span also forces a split
MIN_WORDS = 100
GREY = 0x808285
SPACES = str.maketrans({c: " " for c in "    \xa0"})


def style(span: dict) -> tuple[str, float, int]:
    return span["font"].split("+")[-1], span["size"], span["color"]


def classify(line: dict, y0: float, prev_kind: str | None) -> str:
    """Kind of a text line: part, h1..h4, box, boxtitle, case, or p."""
    sp = line["spans"][0]
    font, size, color = style(sp)
    text = "".join(s["text"] for s in line["spans"]).strip()
    if y0 < 30:
        return "skip"                                            # running header
    if font == "Sense-Bold" and 17 < size < 19 and color == GREY:
        return "part"
    if font == "Sense-Medium" and 11.5 < size < 12.5 and text.isupper():
        return "h1"
    if font == "Sense-Bold" and 11.5 < size < 12.5 and color != 0xffffff:
        return "h2"
    if font == "Sense-Bold" and 10.5 < size < 11.5:
        return "h3" if color == GREY else ("box" if text.lower().startswith("in the clinic") else "p")
    if font == "MinionPro-Bold" and 10.3 < size < 10.8 and color == GREY:
        return "h4"
    if font == "Sense-Bold" and size == 10.0 and prev_kind in ("box", "boxtitle"):
        return "boxtitle"
    if font == "Sense-ExtraBold" and size >= 10 and re.match(r"case \d+", text, re.I):
        return "case-cont" if "cont" in text.lower() else "case"
    return "p"


def join_lines(lines: list[str]) -> str:
    out = ""
    for t in lines:
        t = t.translate(SPACES)
        out = out[:-1] + t.lstrip() if out.endswith("\xad") else (out + " " + t if out else t)
    return " ".join(out.replace("-\xad", "-").replace("\xad", "").split())


def page_items(page: pymupdf.Page) -> list[tuple[str, str]]:
    """(kind, text) for one page in reading order (left column, right column; tables row by row)."""
    w, h = page.rect.width, page.rect.height
    blocks = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        lines = []
        for l in b["lines"]:
            l["spans"] = [s for s in l["spans"] if s["text"].strip() and s["color"] != 0xffffff
                          and s["font"].split("+")[-1].startswith(("Sense", "MinionPro"))]
            if l["spans"] and not (l["bbox"][1] > h - 70 and len("".join(s["text"] for s in l["spans"])) <= 12):
                lines.append(l)                                  # (page numbers sit at the very bottom)
        if not lines:
            continue
        first = lines[0]["spans"][0]
        if first["font"].endswith("ExtraBold") and re.match(r"e?fig", first["text"], re.I):
            continue                                             # figure caption (whole block)
        table = all(s["size"] <= 8.1 for l in lines for s in l["spans"])
        x0, y0 = b["bbox"][0], b["bbox"][1]
        key = (0, int(y0 // 6), x0) if table else (0 if x0 < w / 2 - 10 else 1, y0, x0)
        blocks.append((key, table, lines))
    blocks.sort(key=lambda t: t[0])

    items: list[tuple[str, str]] = []
    prev_kind, prev_bottom, prev_row = None, 0.0, None
    for key, table, lines in blocks:
        if table:                                                # one paragraph per table row
            text = join_lines(["".join(s["text"] for s in l["spans"]) for l in lines])
            if prev_row == key[1] and items and items[-1][0] == "p":
                items[-1] = ("p", items[-1][1] + " | " + text)
            else:
                items.append(("p", text))
            prev_row, prev_kind = key[1], "p"
            continue
        prev_row = None
        para: list[str] = []
        for l in lines:
            kind = classify(l, l["bbox"][1], prev_kind)
            text = "".join(s["text"] for s in l["spans"])
            if kind == "skip":
                continue
            if kind == "p":
                para.append(text)
            else:
                if para:
                    items.append(("p", join_lines(para)))
                    para = []
                same = items and items[-1][0] == kind and l["bbox"][1] - prev_bottom < 8   # wrapped heading
                if same:
                    items[-1] = (kind, items[-1][1] + " " + text)
                else:
                    items.append((kind, text))
            prev_kind, prev_bottom = kind, l["bbox"][3]
        if para:
            items.append(("p", join_lines(para)))
            prev_kind = "p"
    return [(k, join_lines([t])) for k, t in items if join_lines([t])]


LEVEL = {"part": 0, "h1": 1, "h2": 2, "h3": 3, "h4": 4, "case": 1}


def sentence_case(t: str, known: dict[str, str]) -> str:
    if not t.isupper():
        return t
    return known.get(t.lower()) or t.lower().capitalize()


def build_tree(items: list[tuple[str, str, int]], known: dict[str, str]) -> dict | None:
    """Items (kind, text, page) of one chapter -> tree of {title, level, page, body, kids}. Drops the opener."""
    root = {"title": "", "level": -1, "page": 0, "body": [], "kids": []}
    stack, started, pending_case = [root], False, None
    for kind, text, page in items:
        if kind == "part":
            started = True
        if not started:
            continue
        if kind == "boxtitle":
            if stack[-1]["body"] and stack[-1]["body"][-1][0] == "#### In the clinic":
                stack[-1]["body"][-1] = ("#### In the clinic: " + text.strip(), page, "box")
            else:
                stack[-1]["body"].append(("#### " + text.strip(), page, "box"))
            continue
        if kind == "box":
            if "cont" not in text.lower():
                stack[-1]["body"].append(("#### In the clinic", page, "box"))
            continue
        if text.strip().lower() == "continued":
            continue
        if kind == "case-cont" or (kind == "case" and any(n["title"].split(":")[0] == text.strip() for n in stack)):
            continue                                             # "Case 18—cont'd" at the top of a later page
        if kind in LEVEL:
            title = sentence_case(" ".join(text.split()), known)
            pending_case = kind == "case"
            node = {"title": title, "level": LEVEL[kind], "page": page, "body": [], "kids": []}
            while stack[-1]["level"] >= node["level"]:
                stack.pop()
            stack[-1]["kids"].append(node)
            stack.append(node)
            continue
        if pending_case:                                         # a short first line after "Case N" is the case title
            pending_case = False
            if len(text.split()) <= 8:
                stack[-1]["title"] += ": " + sentence_case(text.strip(" \x07"), known)
                continue
        stack[-1]["body"].append((text, page, "p"))
    return root if root["kids"] else None


def words(node: dict) -> int:
    return sum(len(t.split()) for t, _, k in node["body"] if k == "p") + sum(words(c) for c in node["kids"])


def span(node: dict) -> int:
    pages = span_pages(node)
    return max(pages) - min(pages) + 1


def span_pages(node: dict) -> list[int]:
    return [node["page"]] + [p for _, p, _ in node["body"]] + [q for c in node["kids"] for q in span_pages(c)]


def flatten(node: dict, depth: int = 0) -> list[tuple[str, int]]:
    """Node content as (line, page): own text, then children under '###' headings."""
    out = [(t, p) for t, p, _ in node["body"]]
    for c in node["kids"]:
        out.append(("#" * min(3 + depth, 6) + " " + c["title"], c["page"]))
        out += flatten(c, depth + 1)
    return out


def split(node: dict, path: list[str]) -> list[dict]:
    """Sections for a node: whole if short, else its own text as 'Overview' + each child recursively."""
    path = path + [node["title"]]
    if (words(node) <= MAX_WORDS and span(node) <= MAX_PAGES) or not node["kids"]:
        return [{"path": path, "title": node["title"], "lines": flatten(node), "page": node["page"]}]
    secs = []
    if node["body"]:
        secs.append({"path": path + ["Overview"], "title": "Overview", "lines": flatten({**node, "kids": []}),
                     "page": node["page"]})
    for c in node["kids"]:
        secs += split(c, path)
    return fold(secs)


def sec_words(s: dict) -> int:
    return sum(len(t.split()) for t, _ in s["lines"] if not t.startswith("#"))


def fold(secs: list[dict]) -> list[dict]:
    """Merge sections under MIN_WORDS into the next one (its title becomes a '###' line), or the previous at the end."""
    out, carry = [], None
    for s in secs:
        if carry:
            lead = [] if carry["title"] == "Overview" else [("### " + carry["title"], carry["page"])]
            s["lines"] = lead + carry["lines"] + s["lines"]
            s["page"] = carry["page"]
            carry = None
        if sec_words(s) < MIN_WORDS and s is not secs[-1]:
            carry = s
        else:
            out.append(s)
    if out and sec_words(out[-1]) < MIN_WORDS and len(out) > 1:
        last = out.pop()
        out[-1]["lines"] += [("### " + last["title"], last["page"])] + last["lines"]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--book-id", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--isbn", default="")
    ap.add_argument("--out", default="data/okf")
    a = ap.parse_args()

    doc = pymupdf.open(a.pdf)
    chapters = [(t, p) for lvl, t, p in doc.get_toc(simple=True) if lvl == 1 and re.match(r"^\d+ ", t)]
    ends = [p - 1 for _, p in chapters[1:]] + [doc.page_count]
    out = Path(a.out) / a.book_id
    (out / "sections").mkdir(parents=True, exist_ok=True)
    for old in (out / "sections").glob("*.md"):
        old.unlink()

    toc_json, index_lines, n = [], [], 0
    for (ch_title, start), end in zip(chapters, ends):
        items = []
        for p in range(start, end + 1):
            items += [(k, t, p) for k, t in page_items(doc[p - 1])]
        # Mixed-case titles printed in the chapter opener's ToC give proper capitalisation for the CAPS headings.
        known = {t.lower(): t for k, t, _ in items if k in ("h2", "h3") for t in [t.strip()]}
        tree = build_tree(items, known)
        secs = fold([s for part in tree["kids"] for s in split(part, [ch_title])]) if tree else []
        for s, nxt in zip(secs, secs[1:] + [None]):                   # every page belongs to some section
            pages = [p for _, p in s["lines"]] + [s["page"]]
            s["pages"] = [min(pages), max(pages)]
        secs[0]["pages"][0] = start
        for s, nxt in zip(secs, secs[1:]):
            s["pages"][1] = max(s["pages"][1], nxt["pages"][0] - 1)
        secs[-1]["pages"][1] = end
        index_lines.append(f"\n## {ch_title}\n")
        for s in secs:
            n += 1
            body = "\n\n".join(t for t, _ in s["lines"])
            path = [a.title] + s["path"]
            leaf = s["title"]
            slug = slugify(s["path"][-2] if leaf == "Overview" else leaf, 40) + ("-overview" if leaf == "Overview" else "")
            sid = f"{a.book_id}/{n:03d}-{slugify(ch_title.split(' ', 1)[1], 20)}-{slug}"
            front = {"type": "textbook-section", "id": sid, "title": leaf, "chapter": ch_title,
                     "book_id": a.book_id, "book": a.title, "subject": a.subject, "isbn": a.isbn,
                     "section_path": path, "level": "heading", "pages": s["pages"], "words": len(body.split()),
                     "source": Path(a.pdf).name, "toc_source": "font-reconstructed",
                     "license": "copyrighted; local study use only; do not redistribute"}
            fname = sid.split("/", 1)[1] + ".md"
            (out / "sections" / fname).write_text(yaml_front(front) + f"\n# {leaf}\n\n{body}\n")
            toc_json.append({"id": sid, "chapter": ch_title, "path": " › ".join(path), "pages": s["pages"]})
            index_lines.append(f"- [{leaf}](sections/{fname}) (pp. {s['pages'][0]}–{s['pages'][1]})")

    index = yaml_front({"type": "index", "book_id": a.book_id, "book": a.title, "subject": a.subject,
                        "chapters": len(chapters), "sections": n, "toc_source": "font-reconstructed"})
    (out / "index.md").write_text(index + f"\n# {a.title}\n" + "\n".join(index_lines) + "\n")
    (out / "toc.json").write_text(json.dumps(toc_json, indent=1, ensure_ascii=False))
    print(f"{len(chapters)} chapters -> {n} heading-level sections -> {out}/")


if __name__ == "__main__":
    main()
