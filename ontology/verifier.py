"""Second-pass check: does each fact's quote actually state the fact? Demote-only.

The reconciler proves the quote is in the book; it does not prove the quote says what the triple says (an
adverse-effect table row read as a treatment, a drug's metabolising enzyme read as its target). This asks the
LLM, per (triple, quote): yes / partial / no. A source answered "no" is removed from the fact; a fact left with no
source becomes CANDIDATE (hidden from the app). Nothing is ever added or promoted.

  python -m ontology.verifier            # check every unchecked CERTIFIED source, then re-save the ontology
  python -m ontology.verifier --limit 50 # a small trial

Verdicts are cached in data/ontology/verify_cache.jsonl (never committed), and compiler.save_compiled_facts
re-applies them on every rebuild without LLM calls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CACHE = Path("data/ontology/verify_cache.jsonl")
CI_TRIAGE = Path("data/ontology/ci_triage.jsonl")   # haiku triage of STRICT contraindications: {"k", "v", "q"}
BATCH = 25
PRICE_IN, PRICE_OUT = 0.28, 0.42          # assumed DeepSeek $/M tokens (cache miss); check the price page
logger = logging.getLogger("ontology.verifier")

SYSTEM = """You check facts extracted from medical textbooks. For each item you get a relationship
(SUBJECT -PREDICATE-> OBJECT) and the QUOTE it was taken from. Judge only whether the QUOTE states that relationship.
- yes: the quote states it (wording may differ; abbreviations count).
- partial: the quote states something close: only for a subgroup or situation, hedged, or clearly implied.
- no: the quote does not state it: it states a different relation (an adverse effect, a drug's metabolism or
  interaction, a test merely listed in a workup, a cause of something else), names a different subject, or rejects it.
Predicates: TREATED_BY = OBJECT is used to treat SUBJECT. CONFIRMED_BY = OBJECT is a test that diagnoses SUBJECT.
CONTRAINDICATES = OBJECT should be avoided in SUBJECT. MANIFESTS_AS = SUBJECT presents with OBJECT.
CAUSED_BY = SUBJECT is caused by OBJECT. CAUSES_ADVERSE_EFFECT = drug SUBJECT causes OBJECT.
TARGETS_MECHANISM = drug SUBJECT acts on OBJECT. DISRUPTS_PATHWAY = SUBJECT disturbs process OBJECT.
HAS_CLINICAL_STAGE = OBJECT is a stage/phase of SUBJECT. DIFFERENTIAL_OF = the two are considered in each other's
differential. is_a = SUBJECT is a kind of OBJECT. If the item has a line of therapy (e.g. FIRST_LINE), ignore it.
Reply as JSON: {"results": [{"i": <item number>, "v": "yes"|"partial"|"no"}, ...]} with one entry per item."""

_lock = threading.Lock()


def verdict_key(subject: str, predicate: str, obj: str, quote: str) -> str:
    return hashlib.md5(f"{subject.lower()}|{predicate}|{obj.lower()}|{quote.strip()}".encode()).hexdigest()


def load_cache(path: Path = CACHE) -> dict[str, str]:
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["k"]] = r["v"]
    return out


def apply_verdicts(facts, cache: dict[str, str] | None = None):
    """Drop sources judged "no"; a CERTIFIED fact with no source left becomes CANDIDATE. Unchecked sources stay."""
    cache = load_cache() if cache is None else cache
    if not cache:
        return facts
    out = []
    for f in facts:
        if f.status != "CERTIFIED":
            out.append(f)
            continue
        srcs = f.sources or [f.provenance]
        v = {id(p): cache.get(verdict_key(f.subject_label, f.predicate.value, f.object_label, p.verbatim_quote))
             for p in srcs}
        keep = [p for p in srcs if v[id(p)] != "no"]
        if not keep:
            out.append(f.model_copy(update={"status": "CANDIDATE", "llm_check": "no"}))
            continue
        seen = {v[id(p)] for p in keep}
        check = "yes" if "yes" in seen else "partial" if "partial" in seen else None
        primary = f.provenance if f.provenance in keep else keep[0]
        out.append(f.model_copy(update={"sources": keep, "provenance": primary, "llm_check": check}))
    return out


def apply_ci_triage(facts, path: Path = CI_TRIAGE):
    """Re-apply the triage of STRICT contraindications (labelled once by a haiku subagent, cached here; keyed like
    the verifier): "qualifier" -> CAUTIONARY limited to its context, "caution" -> CAUTIONARY, "not_ci" (an
    ineffective drug, a policy, ...) -> CANDIDATE. "ok" and untriaged facts are unchanged. Demote-only."""
    if not path.exists():
        return facts
    tri = {r["k"]: r for r in map(json.loads, path.read_text(encoding="utf-8").splitlines()) if r}
    out = []
    for f in facts:
        r = tri.get(verdict_key(f.subject_label, f.predicate.value, f.object_label, f.provenance.verbatim_quote))
        if f.predicate.value != "CONTRAINDICATES" or f.status != "CERTIFIED" or not r or r["v"] == "ok":
            out.append(f)
        elif r["v"] == "not_ci":
            out.append(f.model_copy(update={"status": "CANDIDATE"}))
        else:
            from ontology.schema import ContraindicationSeverity
            upd = {"contraindication_severity": ContraindicationSeverity.CAUTIONARY}
            if r["v"] == "qualifier" and r.get("q") and not f.clinical_facets.population:
                upd["population"] = f"limited to: {r['q']}"
            out.append(f.model_copy(update={"clinical_facets": f.clinical_facets.model_copy(update=upd)}))
    return out


def _ask(items: list[tuple[str, dict]], spend: dict) -> list[tuple[str, str]]:
    from rag.backends import chat
    lines = []
    for i, (_, it) in enumerate(items):
        lines.append(f"{i}. {it['s']} -{it['p']}-> {it['o']}\n   QUOTE: {it['q'][:700]}")
    user = "\n".join(lines)
    raw = chat(SYSTEM, user, temperature=0.0, max_tokens=60 + 18 * len(items), json_mode=True,
               purpose="ontology verifier")
    with _lock:
        spend["in"] += (len(SYSTEM) + len(user)) // 4
        spend["out"] += len(raw) // 4
        spend["calls"] += 1
    res = json.loads(raw).get("results", [])
    got = {int(r["i"]): str(r["v"]).lower() for r in res if str(r.get("v", "")).lower() in ("yes", "partial", "no")}
    return [(k, got[i]) for i, (k, _) in enumerate(items) if i in got]


def run(limit: int | None = None, workers: int = 8) -> dict:
    from ontology.compiler import load_compiled_facts, save_compiled_facts
    facts = load_compiled_facts()
    cache = load_cache()
    todo: dict[str, dict] = {}
    for f in facts:
        if f.status != "CERTIFIED":
            continue
        for p in (f.sources or [f.provenance]):
            k = verdict_key(f.subject_label, f.predicate.value, f.object_label, p.verbatim_quote)
            if k not in cache and k not in todo:
                todo[k] = {"s": f.subject_label, "p": f.predicate.value, "o": f.object_label, "q": p.verbatim_quote}
    items = list(todo.items())[:limit] if limit else list(todo.items())
    batches = [items[i:i + BATCH] for i in range(0, len(items), BATCH)]
    logger.info("%d sources to check in %d calls (%d already cached)", len(items), len(batches), len(cache))
    spend = {"in": 0, "out": 0, "calls": 0, "failed": 0}
    CACHE.parent.mkdir(parents=True, exist_ok=True)

    def work(b):
        try:
            done = _ask(b, spend)
        except Exception as e:                    # a failed batch is simply retried on the next run
            logger.warning("batch failed: %s", e)
            with _lock:
                spend["failed"] += 1
            return
        with _lock, CACHE.open("a", encoding="utf-8") as fh:
            for k, v in done:
                fh.write(json.dumps({"k": k, "v": v}) + "\n")
            if spend["calls"] % 50 == 0:
                logger.info("%d/%d calls", spend["calls"], len(batches))

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(work, batches))
    save_compiled_facts(list(facts))
    spend["usd"] = round(spend["in"] / 1e6 * PRICE_IN + spend["out"] / 1e6 * PRICE_OUT, 3)
    logger.info("spend (approx, chars/4): %s", spend)
    return spend


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    print(json.dumps(run(a.limit, a.workers)))


if __name__ == "__main__":
    main()
