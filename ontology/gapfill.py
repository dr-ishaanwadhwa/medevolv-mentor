"""Targeted gap-fill: extract missing facts (warnings, presentation, first-line therapy, diagnosis) for chosen
conditions from the passages of Tripathi / Davidson / Harrison / Micro that discuss them.

For each condition: the two best sections per book (by how often it names the condition), and from it the paragraphs that
name it (plus warning/presentation/treatment cue words), up to ~1,500 words. One LLM call per (condition, section).
Every fact then goes through the normal gates (reconciler: types/direction, verbatim quote against that passage,
first-line gating, negation) and the verifier, and is merged with the usual multi-source + entity-merge logic.

  python -m ontology.gapfill --conditions reports/gapfill_conditions.json --dry-run   # passages + cost estimate
  python -m ontology.gapfill --conditions reports/gapfill_conditions.json --limit 5   # trial
  python -m ontology.gapfill --conditions reports/gapfill_conditions.json             # all, then re-save

Each call is cached in data/ontology/cache_gapfill/ (never committed); failed calls are not cached, so a rerun
resumes. builder --rebuild re-adds the cached gap-fill facts without LLM calls.
"""
from __future__ import annotations

import argparse
import functools
import hashlib
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ontology.extractor import parse_okf_section
from ontology.prompt import CLINICAL_SYSTEM_PROMPT, build_extraction_prompt
from ontology.schema import ExtractionItem, SectionExtractionResult

CACHE = Path("data/ontology/cache_gapfill")
BOOKS = ("tripathi", "davidson", "harrison", "micro")
MAX_WORDS = 1500
PRICE_IN, PRICE_OUT = 0.28, 0.42          # assumed DeepSeek $/M tokens; same assumption as ontology/verifier.py
CUES = re.compile(r"contraindicat|avoid|should not|caution|hazard|danger|present(s|ation|ing) |symptom|sign|"
                  r"clinical feature|diagnos|confirm|first[- ]line|drug of choice|treatment of choice|preferred|"
                  r"mainstay|treat", re.I)
logger = logging.getLogger("ontology.gapfill")
_lock = threading.Lock()

TARGET = """

### Targeted mode
This passage was selected because it discusses the condition "{cond}". Extract ONLY facts whose subject is
"{cond}" (or a named subtype of it). Cover, in this order of priority: {focus}. Use the condition's standard name
as subject_name.
- CONTRAINDICATES means a drug or intervention is harmful in this condition (or in a named group of these patients,
  e.g. in pregnancy) and should be avoided or used with caution. Drug RESISTANCE, a drug being ineffective, or a
  regimen being less effective is NOT a contraindication: skip it.
- MANIFESTS_AS: the presenting symptoms and signs the passage lists (one triple per symptom/sign).
- TREATED_BY: name the specific drugs the passage recommends; set FIRST_LINE only when the sentence says so.
Only extract what the passage states; return {{"triples": []}} if it states none of these. At most 15 triples."""
FOCUS = {"CONTRAINDICATES": "CONTRAINDICATES (drugs or interventions to avoid / use with caution in this condition)",
         "MANIFESTS_AS": "MANIFESTS_AS (presenting symptoms and signs)",
         "FIRST_LINE": "TREATED_BY (first-line / drug of choice, with line_of_therapy)",
         "CONFIRMED_BY": "CONFIRMED_BY (the tests that establish the diagnosis)"}


@functools.cache
def _sections(book: str) -> tuple[tuple[Path, str, str], ...]:
    """(path, title, body) for every section of a book."""
    out = []
    for p in sorted(Path(f"data/okf/{book}/sections").glob("*.md")):
        meta, body = parse_okf_section(p)
        out.append((p, str(meta.get("title", p.stem)), body))
    return tuple(out)


def _term_re(terms: list[str]) -> re.Pattern:
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + r")\b", re.I)


def find_passages(terms: list[str], per_book: int = 2, min_hits: int = 3) -> list[tuple[Path, str]]:
    """[(section path, passage)] — the best section of each book for these terms, and its relevant paragraphs."""
    rx = _term_re([t for t in terms if len(t) >= 2])
    out = []
    for book in BOOKS:
        scored = []
        for p, title, body in _sections(book):
            hits = len(rx.findall(body)) + 20 * len(rx.findall(title))
            if any(title.lower().strip() == t or title.lower().startswith(t + " ") for t in terms):
                hits += 200                              # a section named after the condition beats '...portal hypertension'

            if hits >= min_hits:
                scored.append((hits, p, body, bool(rx.search(title))))
        for _, p, body, about in sorted(scored, key=lambda x: -x[0])[:per_book]:
            paras = [x for x in body.split("\n\n") if x.strip()]
            # a section about the condition: any paragraph with warning/presentation/treatment cues counts too
            rank = sorted(((len(rx.findall(x)) * 2 + len(CUES.findall(x)), i) for i, x in enumerate(paras)
                           if rx.search(x) or (about and CUES.search(x))), reverse=True)
            keep, words = set(), 0
            for _, i in rank:
                n = len(paras[i].split())
                if words + n > MAX_WORDS:
                    continue
                keep.add(i)
                words += n
            if keep:
                out.append((p, "\n\n".join(paras[i] for i in sorted(keep))))
    return out


def _key(cond: str, path: Path, passage: str) -> Path:
    return CACHE / (hashlib.md5(f"{cond}|{path}|{passage}".encode()).hexdigest() + ".json")


def jobs(conditions: list[dict]) -> list[tuple[str, list[str], Path, str]]:
    out = []
    for c in conditions:
        terms = list(dict.fromkeys([c["condition"].lower()] + [t.lower() for t in c.get("search_terms", [])]))
        for path, passage in find_passages(terms):
            out.append((c["condition"], c.get("missing") or list(FOCUS), path, passage))
    return out


def _extract(job, spend) -> None:
    from rag.backends import chat
    cond, missing, path, passage = job
    cache = _key(cond, path, passage)
    if cache.exists():
        return
    meta, _ = parse_okf_section(path)
    order = [m for m in missing if m in FOCUS] + [m for m in FOCUS if m not in missing]   # thin ones first
    focus = "; ".join(FOCUS[m] for m in order)
    system = CLINICAL_SYSTEM_PROMPT + TARGET.format(cond=cond, focus=focus)
    user = build_extraction_prompt(str(meta.get("title", path.stem)), str(meta.get("book", "")),
                                   str(meta.get("chapter", "")), passage)
    try:
        raw = chat(system, user, temperature=0.0, max_tokens=4000, json_mode=True, purpose=f"gapfill: {cond}")
        triples = []
        for item in json.loads(raw).get("triples", []):
            try:
                triples.append(ExtractionItem(**item).model_dump(mode="json"))
            except Exception:
                pass
    except Exception as e:                         # not cached: a rerun retries it
        logger.warning("gapfill failed for %s / %s: %s", cond, path.name, e)
        with _lock:
            spend["failed"] += 1
        return
    with _lock:
        spend["in"] += (len(system) + len(user)) // 4
        spend["out"] += len(raw) // 4
        spend["calls"] += 1
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"condition": cond, "section": str(path), "passage": passage, "triples": triples}),
                     encoding="utf-8")


def cached_results(cache: Path = CACHE):
    """(SectionExtractionResult, meta, passage) for every cached gap-fill call (no LLM). ontology/grays.py uses the
    same cache format in its own folder."""
    for f in sorted(cache.glob("*.json")) if cache.exists() else []:
        d = json.loads(f.read_text(encoding="utf-8"))
        path = Path(d["section"])
        if not path.exists():
            continue
        meta, _ = parse_okf_section(path)
        res = SectionExtractionResult(section_id=meta.get("id", path.stem), book_id=meta.get("book_id", path.parts[2]),
                                      chapter=meta.get("chapter", ""), triples=[ExtractionItem(**t) for t in d["triples"]])
        yield res, meta, d["passage"]


def reconcile_cached(stats: dict | None = None, cache: Path = CACHE):
    from ontology.reconciler import reconcile_section_facts
    out = []
    for res, meta, passage in cached_results(cache):
        out += reconcile_section_facts(res, meta, source_text=passage, stats=stats)
    return out


def estimate(js) -> dict:
    sys_tok = (len(CLINICAL_SYSTEM_PROMPT) + 600) // 4
    tin = sum(sys_tok + len(p) // 4 + 80 for *_, p in js)
    tout = 700 * len(js)
    return {"calls": len(js), "tokens_in": tin, "tokens_out_guess": tout,
            "usd": round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 2)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--conditions", required=True)
    ap.add_argument("--limit", type=int, help="first N conditions only")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, default=3.0)
    a = ap.parse_args()
    conds = json.loads(Path(a.conditions).read_text())[: a.limit]
    js = jobs(conds)
    est = estimate([j for j in js if not _key(j[0], j[2], j[3]).exists()])
    print(json.dumps({"conditions": len(conds), "jobs": len(js), "to_run": est}))
    if a.dry_run:
        return
    if est["usd"] > a.max_usd:
        raise SystemExit(f"estimated ${est['usd']} exceeds --max-usd {a.max_usd}; not running")
    spend = {"in": 0, "out": 0, "calls": 0, "failed": 0}
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        list(pool.map(lambda j: _extract(j, spend), js))
    spend["usd"] = round(spend["in"] / 1e6 * PRICE_IN + spend["out"] / 1e6 * PRICE_OUT, 3)
    from ontology.compiler import load_compiled_facts, save_compiled_facts
    stats: dict = {}
    new = reconcile_cached(stats)
    save_compiled_facts(list(load_compiled_facts()) + new)
    print(json.dumps({"spend": spend, "reconcile": stats, "gapfill_facts": len(new)}))


if __name__ == "__main__":
    main()
