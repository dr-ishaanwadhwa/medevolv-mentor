"""Rank OKF sections for ontology extraction by expected clinical yield.

    .venv/bin/python -m ontology.rank [--top 100] [--out reports/ontology_ranking.csv]

Score (higher = extract sooner), each part visible as its own CSV column:

  condition   +3  the title names a BODHI Condition (all its distinctive words appear in title or chapter)
  drug        +2  the title names a BODHI Drug, or is a drug-class/therapy section (drugs, agents, therapy...)
  eval        +2  the title's distinctive words appear in an evaluation question (eval/*.jsonl)
  book        +0..2  clinical axis of the book: harrison/davidson/tripathi 2, micro 1.5, robbins 1, guyton 0
  kind        -3  front matter, intros, history, appendices, glossaries, lab-value tables, methods
  length      -2 if under 300 words (too little to extract), +1 if over 800 (long ones are capped at 4 chunks
                 by the extractor, so more length adds nothing)
  duplicate   -3  same book AND same topic (distinctive title words) as a pilot section or a higher-ranked
                  pick, or the chapter already has CHAPTER_CAP picks/pilot sections from this book (keeps 100 slots
                  spread over many diseases instead of 6 subsections of one drug chapter). The same topic from a
                  DIFFERENT book is not penalised: it adds a new axis (e.g. Tripathi pharmacology for a Harrison
                  disease).

The pilot's 20 sections (ontology.builder.HIGH_YIELD_SECTIONS) are excluded. Ties break by book order, then path.
The CSV goes to reports/ (git-ignored): it lists section titles of the copyrighted books, nothing more.
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import math
import re
from pathlib import Path

BOOK_WEIGHT = {"harrison": 2.0, "davidson": 2.0, "tripathi": 2.0, "micro": 1.5, "robbins": 1.0, "guyton": 0.0}
CHAPTER_CAP = 2
BOOK_ORDER = ["harrison", "davidson", "tripathi", "micro", "robbins", "guyton"]
GENERIC = {"acute", "chronic", "severe", "mild", "primary", "secondary", "disease", "diseases", "disorder",
           "disorders", "syndrome", "syndromes", "infection", "infections", "general", "other", "overview",
           "chapter", "part", "section", "clinical", "introduction", "principles", "approach", "patient",
           "patients", "with", "from", "and", "the", "type", "unspecified", "system", "management", "treatment"}
THERAPY = re.compile(r"\b(drugs?|agents?|therap\w*|antibiotics?|antimicrobials?|antivirals?|antifungals?|"
                     r"anti\w+|inhibitors?|blockers?|antagonists?|agonists?|vaccines?|chemotherapy|pharmacotherapy|"
                     r"treatment|management)\b", re.I)
NOT_CLINICAL = re.compile(r"\b(preface|foreword|contents|index|appendix|appendices|glossary|abbreviations|"
                          r"acknowledg\w*|history of|introduction to|laboratory values|reference values|"
                          r"further (information|reading)|methods|ethics|the practice of medicine|"
                          r"global health|evidence-based|decision-making|professionalism|"
                          # general-principles chapters: few diseases, drugs or contraindications to extract
                          r"pharmacokinetic\w*|pharmacodynamic\w*|epigenetic\w*|drug regulation|good prescribing|"
                          r"routes of drug|plateau principle)\b", re.I)


def words(text: str) -> list[str]:
    return re.findall(r"[a-z]+|\d+", text.lower())


def keys(text: str) -> frozenset:
    return frozenset(w for w in words(text) if (len(w) >= 4 or w.isdigit()) and w not in GENERIC
                     and not w.isdigit())


def front_matter(path: str) -> tuple[dict, int]:
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    meta = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        for line in text[3:end].splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        text = text[end + 4:]
    return meta, len(text.split())


def vocab() -> tuple[list[frozenset], list[frozenset]]:
    from rag.graph import load_graph
    g = load_graph()
    cond, drug = [], []
    for _, d in g.nodes(data=True):
        k = keys(d.get("name", ""))
        if not k or len(k) > 4:
            continue
        if d.get("type") == "Condition":
            cond.append(k)
        elif d.get("type") == "Drug":
            drug.append(k)
    return cond, drug


def eval_words() -> set[str]:
    out = set()
    for f in ("eval/questions.jsonl", "eval/product_questions.jsonl"):
        p = Path(f)
        if p.exists():
            for line in p.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    out |= keys(r.get("question", "") + " " + " ".join(r.get("gold_sections", [])))
    return out


def rank(top: int = 100) -> list[dict]:
    from ontology.builder import HIGH_YIELD_SECTIONS
    pilot = set(HIGH_YIELD_SECTIONS)
    cond, drug = vocab()
    ev = eval_words()
    covered: set[tuple[str, frozenset]] = set()
    per_chapter: dict[tuple[str, str], int] = {}
    rows = []
    for path in sorted(glob.glob("data/okf/*/sections/*.md")):
        meta, n = front_matter(path)
        book = meta.get("book_id", path.split("/")[2])
        title = re.sub(r"^\d+(\.\d+)*\.?\s*", "", meta.get("title", ""))
        chapter = re.sub(r"^\d+\.?\s*", "", meta.get("chapter", ""))
        tk, ck = keys(title), keys(chapter)
        if path in pilot:
            covered.add((book, tk or ck))
            per_chapter[(book, chapter)] = per_chapter.get((book, chapter), 0) + 1
            continue
        both = tk | ck
        s = {
            "condition": 3.0 if any(c <= both for c in cond) else 0.0,
            "drug": 2.0 if (any(d <= tk for d in drug) or THERAPY.search(title + " " + chapter)) else 0.0,
            "eval": 2.0 if tk and len(tk & ev) >= max(1, math.ceil(len(tk) / 2)) else 0.0,
            "book_w": BOOK_WEIGHT.get(book, 0.0),
            "kind": -3.0 if NOT_CLINICAL.search(title + " " + chapter) else 0.0,
            "length": -2.0 if n < 300 else (1.0 if n > 800 else 0.0),
        }
        rows.append({"path": path, "book": book, "title": title, "chapter": chapter, "words": n,
                     "topic": tk or ck, **s, "base": sum(s.values())})
    rows.sort(key=lambda r: (-r["base"], BOOK_ORDER.index(r["book"]) if r["book"] in BOOK_ORDER else 9, r["path"]))
    # greedy duplicate penalty in rank order: same book + same topic as something already chosen/covered
    out = []
    for r in rows:
        ch = (r["book"], r["chapter"])
        dup = -3.0 if ((r["book"], r["topic"]) in covered or per_chapter.get(ch, 0) >= CHAPTER_CAP) else 0.0
        r["duplicate"] = dup
        r["score"] = r["base"] + dup
        if not dup:
            covered.add((r["book"], r["topic"]))
            per_chapter[ch] = per_chapter.get(ch, 0) + 1
        out.append(r)
    out.sort(key=lambda r: (-r["score"], BOOK_ORDER.index(r["book"]) if r["book"] in BOOK_ORDER else 9, r["path"]))
    for i, r in enumerate(out, 1):
        r["rank"] = i
        r["chunks"] = min(4, max(1, math.ceil(r["words"] / 2500)))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100)
    ap.add_argument("--out", default="reports/ontology_ranking.csv")
    a = ap.parse_args()
    rows = rank(a.top)
    Path(a.out).parent.mkdir(exist_ok=True)
    cols = ["rank", "score", "book", "title", "chapter", "words", "chunks",
            "condition", "drug", "eval", "book_w", "kind", "length", "duplicate", "path"]
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in rows:
            w.writerow([r["rank"], r["score"], r["book"], r["title"], r["chapter"], r["words"], r["chunks"],
                        r["condition"], r["drug"], r["eval"], r["book_w"],
                        r["kind"], r["length"], r["duplicate"], r["path"]])
    Path(a.out).with_suffix(".top.txt").write_text("\n".join(r["path"] for r in rows[:a.top]) + "\n")
    print(f"ranked {len(rows)} sections -> {a.out}; top {a.top} paths -> {Path(a.out).with_suffix('.top.txt')}")


if __name__ == "__main__":
    main()
