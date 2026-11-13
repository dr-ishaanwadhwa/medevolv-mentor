"""Split OKF section files into passage chunks for embedding.

Chunking strategy (explain this in the presentation):
  * The OKF section (one chapter for Tripathi) is the unit of *structure*; it is too long to embed (median ~6k words).
  * Inside it we split on paragraphs and pack them into ~CHUNK_WORDS-word passages, never cutting a paragraph,
    with the last paragraph repeated at the start of the next passage (overlap) so a fact on a boundary survives.
  * Short ALL-CAPS paragraphs are the book's own headings (e.g. "PENICILLINS"); the current heading is stored in
    metadata and prefixed to the passage text, so "Mechanism of action" text still knows it is about penicillins.
  * Every passage keeps its section id, so retrieval can be restricted to sections chosen by the router / STAIR.

Gray's Anatomy (book_id "grays") has its own policy, because its sections are made of many very short sub-headings
(an inguinal canal section has one 100-word sub-section per wall) and of "In the clinic" boxes and figure-label lists:
  * sub-headings (### to ######) no longer force a new passage while the current one is under GRAYS_HEAD_FLUSH words;
    the sub-heading stays in the passage text as its own line, so sibling parts (roof / floor / walls) share one passage;
  * "#### In the clinic: ..." boxes and "Figure labels: ..." paragraphs always start / end a passage of their own;
  * the embedded text carries the whole heading path (chapter > region > section > sub-heading), not just chapter > section;
  * the target passage size is GRAYS_CHUNK_WORDS (dense reference text embeds better in smaller pieces).
The other six books are chunked exactly as before.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from ingest.font_toc import smart_title
from rag import config


@dataclass
class Section:
    meta: dict
    body: str


@dataclass
class Chunk:
    id: str
    text: str            # what gets embedded (heading context + passage)
    passage: str         # raw passage shown to the user as evidence
    meta: dict = field(default_factory=dict)


def read_section(path: Path) -> Section:
    raw = path.read_text()
    _, front, body = raw.split("---\n", 2)
    meta = {}
    for line in front.strip().splitlines():
        k, v = line.split(": ", 1)
        meta[k] = json.loads(v)
    body = re.sub(r"^\s*# .*\n", "", body, count=1)     # drop the duplicated H1 title
    return Section(meta, body)


GRAYS = "grays"
GRAYS_CHUNK_WORDS = 260
GRAYS_HEAD_FLUSH = 120                  # a sub-heading starts a new passage only once the current one has this many words
GRAYS_PARTS = {"Conceptual overview", "Regional anatomy", "Surface anatomy", "Overview"}   # part labels carry no topic
FIGURE_PREFIX = "Figure labels: "       # written by ingest.grays_toc


def grays_crumbs(meta: dict) -> list[str]:
    """Heading path for the embedded text: chapter, then the section path without the book title and part labels."""
    path = [p for p in meta["section_path"][1:] if p not in GRAYS_PARTS]
    chapter = meta.get("chapter", meta["title"])
    rest = [p for p in path if p != chapter][-3:]
    return [chapter] + rest


NOT_A_HEADING = re.compile(r"^(section|chapter|table|fig(ure)?)\s*\d+", re.I)   # page labels, captions


def is_heading(par: str) -> bool:
    if NOT_A_HEADING.match(par):
        return False
    letters = [c for c in par if c.isalpha()]
    return 0 < len(par.split()) <= 12 and len(letters) >= 3 and sum(c.isupper() for c in letters) / len(letters) > 0.8


def chunk_section(sec: Section, target_words: int | None = None) -> list[Chunk]:
    grays = sec.meta.get("book_id") == GRAYS
    if target_words is None:
        target_words = GRAYS_CHUNK_WORDS if grays else config.CHUNK_WORDS
    pars = [p.strip() for p in sec.body.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    heading, buf, buf_heading = "", [], ""
    figure = boxed = False

    def flush(carry: str | None):
        nonlocal buf
        if not buf:
            return
        passage = "\n\n".join(buf)
        n = len(chunks) + 1
        chapter = sec.meta.get("chapter", sec.meta["title"])
        crumbs = [chapter] + ([sec.meta["title"]] if sec.meta["title"] != chapter else []) + \
                 ([buf_heading] if buf_heading else [])
        if grays:
            crumbs = grays_crumbs(sec.meta)
            first = buf_heading.split(" / ")[0]
            if first and first not in crumbs:
                crumbs.append(first)
        chunks.append(Chunk(
            id=f"{sec.meta['id']}#p{n:03d}",
            text=" › ".join(crumbs) + "\n" + passage,   # heading context is embedded with the passage
            passage=passage,
            meta={
                "section_id": sec.meta["id"],
                "section_title": sec.meta["title"],
                "chapter": chapter,
                "section_path": " › ".join(sec.meta["section_path"]),
                "heading": buf_heading,
                "book_id": sec.meta["book_id"],
                "book": sec.meta["book"],
                "subject": sec.meta["subject"],
                "pages": f"{sec.meta['pages'][0]}-{sec.meta['pages'][1]}",
                **({"kind": "figure"} if figure else {}),
            },
        ))
        buf = [carry] if carry else []

    for par in pars:
        if grays and par.startswith(FIGURE_PREFIX):
            # a figure's label list is a passage of its own; the text being collected carries on around it
            saved, saved_heading = buf, buf_heading
            buf, buf_heading, figure = [par], heading, True
            flush(None)
            buf, buf_heading, figure = saved, saved_heading, False
            continue
        md = re.match(r"^#{3,6} (.+)$" if grays else r"^#{3,4} (.+)$", par)   # sub-headings written by ingest
        if grays and md:
            box = md.group(1).startswith("In the clinic")
            if box or boxed:
                boxed = box                              # a box ends at the next heading; never merge across it
                md_flush = True
            else:
                md_flush = sum(len(p.split()) for p in buf) >= GRAYS_HEAD_FLUSH
        if grays and md and not md_flush:
            if buf:                                      # short passage so far: keep the sibling sub-heading inside it
                buf.append(md.group(1))
                if md.group(1) not in buf_heading and buf_heading.count(" / ") < 2:
                    buf_heading = f"{buf_heading} / {md.group(1)}" if buf_heading else md.group(1)
            heading = md.group(1)
            if not buf:
                buf_heading = heading
            continue
        if md or is_heading(par):
            flush(None)                    # a new heading starts a fresh passage, no overlap across topics
            heading = md.group(1) if md else smart_title(par)
            buf_heading = heading
            continue
        if not buf:
            buf_heading = heading
        if sum(len(p.split()) for p in buf) + len(par.split()) > target_words and buf:
            last = buf[-1] if len(buf[-1].split()) < target_words // 3 else None
            flush(last)
            buf_heading = heading
        buf.append(par)
    flush(None)
    return _merge_tiny(chunks, min_words=60)


def _merge_tiny(chunks: list[Chunk], min_words: int) -> list[Chunk]:
    """Fold passages shorter than min_words (a heading with one line under it) into the next passage."""
    out: list[Chunk] = []
    pending: Chunk | None = None
    for c in chunks:
        if c.meta.get("kind") == "figure":               # figure-label passages stay as they are
            if pending:
                out.append(pending)
                pending = None
            out.append(c)
            continue
        if pending:
            c.passage = pending.passage + "\n\n" + c.passage
            c.text = pending.text + "\n\n" + c.passage[len(pending.passage) + 2:]
            if pending.meta["heading"] and pending.meta["heading"] != c.meta["heading"]:
                c.meta["heading"] = f"{pending.meta['heading']} / {c.meta['heading']}".strip(" /")
            pending = None
        if len(c.passage.split()) < min_words:
            pending = c
            continue
        out.append(c)
    if pending:
        if out:
            out[-1].passage += "\n\n" + pending.passage
            out[-1].text += "\n\n" + pending.passage
        else:
            out.append(pending)
    for i, c in enumerate(out, 1):                       # renumber so ids stay contiguous
        c.id = f"{c.meta['section_id']}#p{i:03d}"
    return out


def iter_chunks(okf_dir: Path = config.OKF_DIR):
    for f in sorted(okf_dir.glob("*/sections/*.md")):
        yield from chunk_section(read_section(f))


if __name__ == "__main__":
    cs = list(iter_chunks())
    words = sorted(len(c.passage.split()) for c in cs)
    print(f"{len(cs)} chunks; words min/median/max = {words[0]}/{words[len(words)//2]}/{words[-1]}")
    print("example:\n", cs[len(cs) // 2].text[:500])
