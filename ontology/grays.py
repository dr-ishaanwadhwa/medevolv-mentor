"""Clinical facts from Gray's Anatomy for Students: only its clinical content, never the plain anatomy.

Passages:
  - each "Clinical cases" section (section_path contains "Clinical cases"), whole, up to ~1,500 words;
  - the "In the clinic" boxes of every other section: from a "#### In the clinic: <title>" line to the next
    ###/#### heading, the boxes of one section joined (headings kept) into passages of up to ~1,500 words.
One LLM call per passage. Facts then go through the normal gates (reconciler: types/direction, verbatim quote
against that passage, negation, contraindication qualifiers), the verifier, entity merges and multi-source merging.

  python -m ontology.grays --dry-run     # passages + cost estimate
  python -m ontology.grays --limit 10    # trial
  python -m ontology.grays               # all, then re-save the ontology

Calls are cached in data/ontology/cache_grays/ (never committed; same format as ontology/gapfill.py); failed calls
are not cached, so a rerun resumes. builder --rebuild re-adds the cached facts without LLM calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from ontology.extractor import parse_okf_section
from ontology.gapfill import MAX_WORDS, PRICE_IN, PRICE_OUT, reconcile_cached
from ontology.prompt import CLINICAL_SYSTEM_PROMPT, build_extraction_prompt
from ontology.schema import ExtractionItem

CACHE = Path("data/ontology/cache_grays")
SECTIONS = Path("data/okf/grays/sections")
BOX = re.compile(r"^#### In the clinic\b.*$", re.M)
NEXT_HEADING = re.compile(r"^#{1,4} ", re.M)
logger = logging.getLogger("ontology.grays")
_lock = threading.Lock()

ADDENDUM = """

### Anatomy-book mode
This passage is clinical material from an anatomy textbook (an "In the clinic" box or a clinical case).
Extract only clinical facts whose subject is a disease, injury, syndrome or clinical finding. Priority:
MANIFESTS_AS (signs and symptoms), CAUSED_BY (the injury, lesion or agent that causes it), CONFIRMED_BY (the test or
imaging that establishes it), DIFFERENTIAL_OF, DISRUPTS_PATHWAY, and TREATED_BY / CONTRAINDICATES only when the
passage states them.
One extra class and predicate are allowed here:
- AnatomicalStructure: a named organ, vessel, nerve, bone, muscle, ligament, duct or space (e.g. "Ulnar nerve",
  "Middle meningeal artery", "Cauda equina").
- INVOLVES_STRUCTURE: Condition -> AnatomicalStructure that the condition damages, compresses, blocks or arises in
  (e.g. Extradural hematoma INVOLVES_STRUCTURE Middle meningeal artery).
Do NOT extract normal anatomy (what supplies, drains or lies next to what) or surgical steps, and do not make an
individual patient's details into facts unless the passage states them as general. Never use vague objects such as
"Asymptomatic", "Drug treatment" or "Surgery": name the finding, drug or operation. At most 12 triples."""


def boxes(body: str) -> list[str]:
    """The text of each 'In the clinic' box, heading included."""
    out = []
    for m in BOX.finditer(body):
        nxt = NEXT_HEADING.search(body, m.end())
        out.append(body[m.start(): nxt.start() if nxt else len(body)].strip())
    return out


def _chunks(parts: list[str]) -> list[str]:
    out, cur, n = [], [], 0
    for part in parts:
        w = len(part.split())
        if cur and n + w > MAX_WORDS:
            out.append("\n\n".join(cur))
            cur, n = [], 0
        cur.append(" ".join(part.split()[:MAX_WORDS]) if w > MAX_WORDS else part)
        n += min(w, MAX_WORDS)
    return out + (["\n\n".join(cur)] if cur else [])


def passages(sections: Path = SECTIONS) -> list[tuple[Path, str]]:
    """[(section path, passage)] for every clinical case section and every section's clinic boxes."""
    out = []
    for p in sorted(sections.glob("*.md")):
        meta, body = parse_okf_section(p)
        if "Clinical cases" in (meta.get("section_path") or []):
            parts = [x for x in body.split("\n\n") if x.strip()]
        else:
            parts = boxes(body)
        out += [(p, c) for c in _chunks(parts)]
    return out


def _key(path: Path, passage: str) -> Path:
    return CACHE / (hashlib.md5(f"{path}|{passage}".encode()).hexdigest() + ".json")


def _extract(job, spend) -> None:
    from rag.backends import chat
    path, passage = job
    cache = _key(path, passage)
    if cache.exists():
        return
    meta, _ = parse_okf_section(path)
    system = CLINICAL_SYSTEM_PROMPT + ADDENDUM
    user = build_extraction_prompt(str(meta.get("title", path.stem)), str(meta.get("book", "")),
                                   str(meta.get("chapter", "")), passage)
    try:
        raw = chat(system, user, temperature=0.0, max_tokens=4000, json_mode=True, purpose="grays clinical")
        triples = []
        for item in json.loads(raw).get("triples", []):
            try:
                triples.append(ExtractionItem(**item).model_dump(mode="json"))
            except Exception:
                pass
    except Exception as e:                         # not cached: a rerun retries it
        logger.warning("grays failed for %s: %s", path.name, e)
        with _lock:
            spend["failed"] += 1
        return
    with _lock:
        spend["in"] += (len(system) + len(user)) // 4
        spend["out"] += len(raw) // 4
        spend["calls"] += 1
    CACHE.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"condition": None, "section": str(path), "passage": passage, "triples": triples}),
                     encoding="utf-8")


def estimate(js) -> dict:
    sys_tok = (len(CLINICAL_SYSTEM_PROMPT) + len(ADDENDUM)) // 4
    tin = sum(sys_tok + len(p) // 4 + 80 for _, p in js)
    tout = 600 * len(js)
    return {"calls": len(js), "tokens_in": tin, "tokens_out_guess": tout,
            "usd": round(tin / 1e6 * PRICE_IN + tout / 1e6 * PRICE_OUT, 2)}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="first N passages only")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-usd", type=float, default=3.0)
    a = ap.parse_args()
    js = passages()[: a.limit]
    est = estimate([j for j in js if not _key(*j).exists()])
    print(json.dumps({"passages": len(js), "to_run": est}))
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
    new = reconcile_cached(stats, CACHE)
    save_compiled_facts(list(load_compiled_facts()) + new)
    print(json.dumps({"spend": spend, "reconcile": stats, "grays_facts": len(new)}))


if __name__ == "__main__":
    main()
