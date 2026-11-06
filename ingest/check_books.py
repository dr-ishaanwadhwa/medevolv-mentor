"""Day-1 book check: which PDFs are usable for OKF ingestion and STAIR?

Usage:  python -m ingest.check_books data/books            (folder, searched recursively)
Writes: reports/book_check.csv and prints a summary table.

Per PDF it reports:
  pages        page count
  toc          number of embedded bookmark entries (0 = no ToC -> unusable for STAIR)
  depth        deepest bookmark level
  leaves       bookmark entries with no children = candidate STAIR sections
  chars/page   median extractable characters on sampled pages (~0 = scanned images)
  verdict      OK / NO_TOC / SCANNED / SHALLOW_TOC / ERROR
"""
from __future__ import annotations

import csv
import statistics
import sys
from pathlib import Path

import pymupdf

SAMPLE_PAGES = 15
MIN_CHARS_PER_PAGE = 300  # below this the page is probably an image scan
MIN_DEPTH = 2             # chapter-only ToC is too coarse for section retrieval


def count_leaves(toc: list[list]) -> int:
    """A bookmark is a leaf if the next entry is not deeper than it."""
    leaves = 0
    for i, (level, *_rest) in enumerate(toc):
        nxt = toc[i + 1][0] if i + 1 < len(toc) else 0
        if nxt <= level:
            leaves += 1
    return leaves


def median_chars(doc: pymupdf.Document) -> int:
    n = doc.page_count
    if n == 0:
        return 0
    # Spread samples over the body, skipping front/back matter.
    start, end = int(n * 0.1), max(int(n * 0.9), 1)
    step = max((end - start) // SAMPLE_PAGES, 1)
    counts = [len(doc[p].get_text("text").strip()) for p in range(start, end, step)][:SAMPLE_PAGES]
    return int(statistics.median(counts)) if counts else 0


def check(path: Path) -> dict:
    row = {"file": path.name, "pages": 0, "toc": 0, "depth": 0, "leaves": 0, "chars_per_page": 0}
    try:
        with pymupdf.open(path) as doc:
            toc = doc.get_toc(simple=True)
            row.update(
                pages=doc.page_count,
                toc=len(toc),
                depth=max((t[0] for t in toc), default=0),
                leaves=count_leaves(toc),
                chars_per_page=median_chars(doc),
            )
    except Exception as e:  # corrupt / encrypted PDFs
        row["verdict"] = f"ERROR: {e.__class__.__name__}"
        return row

    if row["chars_per_page"] < MIN_CHARS_PER_PAGE:
        row["verdict"] = "SCANNED"
    elif row["toc"] == 0:
        row["verdict"] = "NO_TOC"
    elif row["depth"] < MIN_DEPTH:
        row["verdict"] = "SHALLOW_TOC"
    else:
        row["verdict"] = "OK"
    return row


def main(folder: str) -> None:
    pdfs = sorted(Path(folder).rglob("*.pdf"))
    if not pdfs:
        sys.exit(f"No PDFs found under {folder}")

    rows = []
    for p in pdfs:
        print(f"checking {p.name} ...", file=sys.stderr)
        rows.append(check(p))

    out = Path("reports")
    out.mkdir(exist_ok=True)
    with open(out / "book_check.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'verdict':<12} {'pages':>6} {'toc':>5} {'depth':>5} {'leaves':>6} {'chars/pg':>8}  file")
    for r in sorted(rows, key=lambda r: (r["verdict"] != "OK", -r["leaves"])):
        print(f"{r['verdict']:<12} {r['pages']:>6} {r['toc']:>5} {r['depth']:>5} "
              f"{r['leaves']:>6} {r['chars_per_page']:>8}  {r['file']}")
    print(f"\n{sum(r['verdict'] == 'OK' for r in rows)}/{len(rows)} usable. CSV: reports/book_check.csv")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/books")
