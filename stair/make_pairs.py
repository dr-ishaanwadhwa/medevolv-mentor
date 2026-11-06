"""Generate STAIR training pairs: (question -> ToC section) for one OKF book.

STAIR learns to map a question to the section that answers it. We create those examples synthetically:
for each target section, sample a few of its passages and ask an LLM to write exam-style questions that
the passage answers. Only the questions and the section ids are saved (stair/pairs/, git-ignored) --
never the textbook text.

Usage:
  python -m stair.make_pairs --book tripathi --level section --per-section 10      # all 447 sections
  python -m stair.make_pairs --book tripathi --level chapter --per-section 10      # 78 chapter targets
  python -m stair.make_pairs --book tripathi --limit 5                             # quick smoke test

Resumable: targets already present in the output file are skipped, so a crash or rate limit costs nothing.
Held-out guard: questions too similar to eval/questions.jsonl are dropped so STAIR is never trained on
the evaluation set.
"""
from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

from rag import config
from rag.backends import chat
from rag.chunk import iter_chunks

SYSTEM = """You write exam questions for medical students from a pharmacology textbook passage.
Return a JSON object: {"questions": ["...", "..."]}.
Rules:
- Every question must be answerable from the passage alone.
- Mix styles: direct fact, mechanism ("why/how"), clinical vignette ("A patient with ... which drug ..."),
  comparison, adverse effect / contraindication, use / indication.
- Do NOT copy sentences from the passage; paraphrase like a student or examiner would ask.
- Do NOT mention the chapter, section, or heading names, or say "according to the passage".
- Each question is one sentence, under 30 words."""

USER = """Section topic (for your context only, do not name it): {path}

Passage:
{passage}

Write {n} different questions."""


def load_eval_questions(path: Path = Path("eval/questions.jsonl")) -> list[set[str]]:
    if not path.exists():
        return []
    qs = [json.loads(l)["question"] for l in path.read_text().splitlines() if l.strip()]
    return [set(re.findall(r"[a-z0-9]+", q.lower())) for q in qs]


def too_close_to_eval(q: str, eval_sets: list[set[str]], thresh: float = 0.6) -> bool:
    words = set(re.findall(r"[a-z0-9]+", q.lower()))
    return any(len(words & e) / max(1, len(words | e)) >= thresh for e in eval_sets)


MAX_COPY_WORDS = 7   # a question sharing 8+ consecutive words with its passage is copying, not paraphrasing


def longest_copy(question: str, passage: str) -> int:
    qw = re.findall(r"\w+", question.lower())
    pw = " " + " ".join(re.findall(r"\w+", passage.lower())) + " "
    for n in range(len(qw), 0, -1):
        if any(f" {' '.join(qw[i:i + n])} " in pw for i in range(len(qw) - n + 1)):
            return n
    return 0


def parse_questions(raw: str) -> list[str]:
    try:
        data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        qs = data.get("questions", [])
    except (json.JSONDecodeError, ValueError, AttributeError):
        qs = re.findall(r'"([^"]{15,250}\?)"', raw)          # salvage quoted questions from broken JSON
    out = []
    for q in qs:
        q = " ".join(str(q).split())
        if 15 <= len(q) <= 250 and q.endswith("?") and "passage" not in q.lower():
            out.append(q)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, help="book_id, e.g. tripathi")
    ap.add_argument("--level", choices=["section", "chapter"], default="section")
    ap.add_argument("--per-section", type=int, default=10)
    ap.add_argument("--passages", type=int, default=3, help="passages sampled per target")
    ap.add_argument("--limit", type=int, default=0, help="only the first N targets (smoke test)")
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()

    random.seed(a.seed)
    toc = json.loads((config.OKF_DIR / a.book / "toc.json").read_text())

    # Group passages by target: one target per section, or per chapter at chapter level.
    key_of = {t["id"]: (t["path"] if a.level == "section" else t.get("chapter", t["path"])) for t in toc}
    chapter_path = {}
    for t in toc:   # chapter-level label = path up to and including the chapter
        parts = t["path"].split(" › ")
        ch = t.get("chapter")
        chapter_path[ch] = " › ".join(parts[: parts.index(ch) + 1]) if ch in parts else t["path"]
    label_of = (lambda k: k) if a.level == "section" else (lambda k: chapter_path.get(k, k))

    passages = defaultdict(list)
    for c in iter_chunks():
        if c.meta["book_id"] == a.book and c.meta["section_id"] in key_of:
            passages[key_of[c.meta["section_id"]]].append(c)
    targets = sorted(passages, key=lambda k: list(key_of.values()).index(k))
    if a.limit:
        targets = targets[: a.limit]

    out_dir = Path("stair/pairs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{a.book}.{a.level}.jsonl"
    done = set()
    if out_path.exists():
        done = {json.loads(l)["target"] for l in out_path.read_text().splitlines() if l.strip()}
    eval_sets = load_eval_questions()

    written = dropped = 0
    with out_path.open("a") as f:
        for i, key in enumerate(targets, 1):
            label = label_of(key)
            if label in done:
                continue
            chosen = random.sample(passages[key], min(a.passages, len(passages[key])))
            per_passage = max(1, round(a.per_section / len(chosen)))
            seen: set[str] = set()
            for c in chosen:
                raw = chat(SYSTEM, USER.format(path=label, passage=c.passage, n=per_passage),
                           temperature=0.7, max_tokens=700, json_mode=True)
                for q in parse_questions(raw)[:per_passage]:
                    if q.lower() in seen:
                        continue
                    seen.add(q.lower())
                    if too_close_to_eval(q, eval_sets) or longest_copy(q, c.passage) > MAX_COPY_WORDS:
                        dropped += 1
                        continue
                    f.write(json.dumps({"question": q, "target": label, "book_id": a.book,
                                        "level": a.level, "source_chunk": c.id,
                                        "generator": config.LLM_BACKEND}, ensure_ascii=False) + "\n")
                    written += 1
            f.flush()
            print(f"[{i}/{len(targets)}] {len(seen):2d} q  {label.split(' › ')[-1][:60]}")
    print(f"\n{written} pairs written to {out_path} ({dropped} dropped: near an eval question or copied text)")


if __name__ == "__main__":
    main()
