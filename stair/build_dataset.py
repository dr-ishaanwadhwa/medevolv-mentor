"""Turn (question -> section) pairs into two-stage chat training data for STAIR fine-tuning.

Why two stages: putting all 447 Tripathi section paths in every prompt would be ~6k tokens per example,
too long to train on an 8 GB GPU. Instead:
  Stage A  question + the book's chapter list           -> chapter title
  Stage B  question + that chapter's section list       -> section title (path below the chapter)
Each prompt stays around 1k tokens. At inference, both stages use constrained decoding over the same lists,
so the model can only output titles that exist.

Usage:
  python -m stair.build_dataset --book tripathi --level section
Writes stair/data/<book>/ (git-ignored):
  train.jsonl, val.jsonl     {"messages": [system, user, assistant], "stage": "A"|"B", "target": ...}
  labels.json                chapters + sections per chapter (for constrained decoding and evaluation)
Split: per target, one question goes to val (if the target has >= 3), the rest to train.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

from rag import config

SYSTEM_A = ("You are STAIR, a retriever for the textbook \"{book}\". Given a question and the book's chapter list, "
            "reply with the exact title of the one chapter that answers it. Reply with the title only.")
SYSTEM_B = ("You are STAIR, a retriever for the textbook \"{book}\". Given a question, a chapter, and that "
            "chapter's sections, reply with the exact title of the one section that answers it. Title only.")


def load_labels(book: str) -> dict:
    toc = json.loads((config.OKF_DIR / book / "toc.json").read_text())
    chapters, sections = [], defaultdict(list)
    book_title = toc[0]["path"].split(" › ")[0]
    for t in toc:
        parts = t["path"].split(" › ")
        ch = t.get("chapter") or parts[-1]
        if ch not in chapters:
            chapters.append(ch)
        below = " › ".join(parts[parts.index(ch) + 1:]) if ch in parts else ""
        if below and below not in sections[ch]:
            sections[ch].append(below)
    return {"book": book_title, "chapters": chapters, "sections": dict(sections)}


def split_target(path: str, chapters: list[str]) -> tuple[str, str]:
    """'Book › Section 12: … › 51. Beta-Lactam Antibiotics › Cephalosporins › Uses' -> (chapter, 'Cephalosporins › Uses')"""
    parts = path.split(" › ")
    for i, p in enumerate(parts):
        if p in chapters:
            return p, " › ".join(parts[i + 1:])
    return parts[-1], ""


def example_a(q: str, chapter: str, labels: dict) -> dict:
    listing = "\n".join(f"- {c}" for c in labels["chapters"])
    return {"stage": "A", "target": chapter, "messages": [
        {"role": "system", "content": SYSTEM_A.format(book=labels["book"])},
        {"role": "user", "content": f"Chapters:\n{listing}\n\nQuestion: {q}"},
        {"role": "assistant", "content": chapter},
    ]}


def example_b(q: str, chapter: str, section: str, labels: dict) -> dict:
    listing = "\n".join(f"- {s}" for s in labels["sections"][chapter])
    return {"stage": "B", "target": f"{chapter} › {section}", "messages": [
        {"role": "system", "content": SYSTEM_B.format(book=labels["book"])},
        {"role": "user", "content": f"Chapter: {chapter}\nSections:\n{listing}\n\nQuestion: {q}"},
        {"role": "assistant", "content": section},
    ]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True)
    ap.add_argument("--level", choices=["section", "chapter"], default="section")
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    random.seed(a.seed)

    labels = load_labels(a.book)
    pairs = [json.loads(l) for l in Path(f"stair/pairs/{a.book}.{a.level}.jsonl").read_text().splitlines() if l]
    by_target = defaultdict(list)
    for p in pairs:
        by_target[p["target"]].append(p["question"])

    train, val = [], []
    skipped = 0
    for target, qs in by_target.items():
        chapter, section = split_target(target, labels["chapters"])
        if chapter not in labels["chapters"]:
            skipped += len(qs)
            continue
        random.shuffle(qs)
        held = qs[:1] if len(qs) >= 3 else []
        for q in qs:
            dest = val if q in held else train
            dest.append(example_a(q, chapter, labels))
            # Stage B only when the chapter has more than one section to choose from
            if a.level == "section" and section and len(labels["sections"].get(chapter, [])) > 1:
                dest.append(example_b(q, chapter, section, labels))

    out = Path("stair/data") / a.book
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in (("train", train), ("val", val)):
        random.shuffle(rows)
        (out / f"{name}.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
    (out / "labels.json").write_text(json.dumps(labels, indent=1, ensure_ascii=False))

    def approx_tokens(r):  # ~0.75 words per token for English
        return int(sum(len(m["content"].split()) for m in r["messages"]) / 0.75)
    toks = sorted(approx_tokens(r) for r in train) or [0]
    print(f"targets={len(by_target)} train={len(train)} val={len(val)} skipped={skipped}")
    print(f"stage A/B in train: {sum(r['stage']=='A' for r in train)}/{sum(r['stage']=='B' for r in train)}")
    print(f"approx tokens/example median={toks[len(toks)//2]} max={toks[-1]} total={sum(toks):,}")
    print(f"-> {out}/train.jsonl, val.jsonl, labels.json")


if __name__ == "__main__":
    main()
