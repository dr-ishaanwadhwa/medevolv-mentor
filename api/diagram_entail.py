"""Entailment check for answer-path flowcharts (PRD 4.1 R1; docs/wiki/problems/diagram-validator-lexical-limits.md).

The word rules in api.diagram_validate are a cheap first filter; they cannot tell "freeze initiation" from "accelerate
initiation". After validate() accepts a graph, ONE DeepSeek call (temperature 0, JSON) reads the numbered cited
sentences and every box and arrow, and returns for each item a verdict and a quote copied from one of the item's own
cited sentences. A deterministic post-check keeps an item only if the verdict is "supported" AND the quote is a
verbatim span (after whitespace/marker/case normalisation) of a sentence the item cites (or of its heading/lead-in, alone
or read together with the sentence).

This step can only REMOVE boxes and arrows, never add or relabel them. Dropping a box drops its arrows; then the
validator's own rules are re-applied (lone boxes left out under the V6 ceiling, V6, MIN_NODES, E4 connectivity), and a
graph that falls below them declines "too_few_supported_nodes". A model error, timeout or malformed reply raises
VerifierUnavailable: the caller declines "verifier_unavailable" (fail closed, never cached).
"""
from __future__ import annotations

import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field

from api import diagram_validate as V
from rag.backends import chat

VERIFY_TIMEOUT_S = 12.0          # the verifier's own limit; the caller also caps it by what is left of TOTAL_BUDGET_S
VERIFY_MIN_S = 2.0               # less time than this left in the budget: do not start the call, decline instead
MAX_QUOTE_WORDS = 40
_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="diagram-verify")


class VerifierUnavailable(RuntimeError):
    """The entailment call failed, timed out or returned something we cannot read."""


@dataclass
class Checked:
    ok: bool
    reason: str | None = None
    graph: dict | None = None
    dropped: int = 0                                # boxes left out, all steps (validate's count + this step's)
    notes: list = field(default_factory=list)       # what this step dropped and why (logs/eval only, never shown)


SYSTEM = """You check a revision flowchart against the textbook sentences it cites. Be strict.
For EACH item (a box or an arrow) decide whether one of ITS OWN cited sentences states it.
- A box is "supported" only if a span of one of its cited sentences says the same thing with the same meaning: same
  direction (increase/decrease, activates/inhibits, raises/lowers, before/after), same negation (not, no, without,
  absent, ineffective), same quantity and numbers, same scope words (only, all, some, most, mainly, also), and the same
  who-does-what (subject, verb and object not swapped; a verb on one object is not moved to another). Paraphrase is
  allowed. Adding, strengthening, weakening, reversing or narrowing meaning is NOT allowed.
- An arrow "A -> B" with a verb is supported only if a cited sentence states that A <verb> B, in that direction.
  An arrow with verb "" means: for a classification, B is a type, member or item of A; for a pathway, A passes,
  continues or branches to B; for a sequence, A leads to or comes before B (the text's own order of cause and effect).
  A sentence shown "under" a heading or lead-in is one of that heading's items: the heading includes what the sentence
  lists, also an item stated in the negative ("does not ...") or a division listed under it. This only links the
  heading to the item; the item's own box is still checked on its own. Two consecutive cited sentences may state a step when the second opens with a link back ("This causes",
  "then", "which"): quote that link.
- If the cited sentences do not state the item, or state something different, the verdict is "not_supported".
- "quote": copy character for character the shortest span (at most 25 words) of ONE of the item's cited sentences, or
  of its heading, that states the item. Never paraphrase in the quote and never join pieces of different sentences.
  For "not_supported", quote the closest span or "".
Output JSON: {"items": [{"id": "...", "verdict": "supported" or "not_supported", "quote": "..."}]}, one entry per item,
in the given order."""


# ---------------------------------------------------------------- normalisation for the verbatim check

_DASH = re.compile(r"[‐-―−]")
_QUOTE_CH = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def norm(text: str) -> str:
    """NFC, citation markers and markdown emphasis removed, dashes/quotes unified, whitespace collapsed, case folded."""
    s = unicodedata.normalize("NFC", text or "")
    s = V.strip_markers(s).replace("**", "").replace("__", "")
    s = _DASH.sub("-", s).translate(_QUOTE_CH)
    s = re.sub(r"\s+", " ", s).strip().casefold()
    return s


def _norm_quote(q: str) -> str:
    return norm(q).strip(" .,;:\"'()")


def quote_ok(quote: str, texts: list[str]) -> bool:
    """The quote is a real span of one of `texts`: non-trivial (a content word, at most MAX_QUOTE_WORDS words) and a
    verbatim substring after normalisation. Never a join of two texts."""
    q = _norm_quote(quote if isinstance(quote, str) else "")
    if not q or not V.content_words(q) or len(q.split()) > MAX_QUOTE_WORDS:
        return False
    return any(q in norm(t) for t in texts if t)


def sentence_texts(s: V.Sent) -> list[str]:
    """What a quote may be a span of: the sentence, its heading/lead-in, or the two read together ("Positive inotropy:
    Failing dilated ventricles empty ..."), which is how the prompt shows a list item under its heading."""
    if not s.ctx:
        return [s.text]
    return [s.text, s.ctx, f"{s.ctx} {s.text}", f"{s.ctx}: {s.text}"]


# ---------------------------------------------------------------- prompt

def _cite_set(cites: list[dict]) -> set:
    return {(c["kind"], c["n"]) for c in cites}


def build_items(graph: dict, answer_text: str) -> tuple[list[V.Sent], dict[str, list[int]], str]:
    """(cited sentences, item id -> indices into them, user prompt). Only sentences carrying a marker the graph uses."""
    sents = V.parse_answer(answer_text)
    used = set()
    for x in graph["nodes"] + graph["edges"]:
        used |= _cite_set(x["cites"])
    shown = [s for s in sents if s.mk & used]
    sid = {id(s): i for i, s in enumerate(shown)}
    label = {n["id"]: n["label"] for n in graph["nodes"]}

    def refs(cites: list[dict]) -> list[int]:
        return [sid[id(s)] for s in V._carriers(_cite_set(cites), shown)]

    lines = ["Sentences:"]
    for i, s in enumerate(shown):
        under = f' (under "{s.ctx}")' if s.ctx else ""
        lines.append(f"S{i + 1}{under}: {V.strip_markers(s.text)}")
    lines += ["", f"Flowchart kind: {graph['kind']}", "", "Items:"]
    item_refs: dict[str, list[int]] = {}
    for n in graph["nodes"]:
        r = item_refs[n["id"]] = refs(n["cites"])
        lines.append(json.dumps({"id": n["id"], "type": "box", "label": n["label"],
                                 "cited_sentences": [f"S{i + 1}" for i in r]}, ensure_ascii=False))
    for k, e in enumerate(graph["edges"]):
        eid = f"e{k + 1}"
        r = item_refs[eid] = refs(e["cites"])
        lines.append(json.dumps({"id": eid, "type": "arrow", "from": label[e["from"]], "to": label[e["to"]],
                                 "verb": e["label"], "cited_sentences": [f"S{i + 1}" for i in r]}, ensure_ascii=False))
    return shown, item_refs, "\n".join(lines)


def _parse(raw: str) -> dict[str, dict]:
    s = re.sub(r"^```(?:json)?\s*|\s*```$", "", (raw or "").strip())
    try:
        obj = json.loads(s)
    except ValueError as e:
        raise VerifierUnavailable("verifier reply was not valid JSON") from e
    items = obj.get("items") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        raise VerifierUnavailable("verifier reply has no items list")
    out: dict[str, dict] = {}
    for it in items:
        if isinstance(it, dict) and isinstance(it.get("id"), str) and it["id"] not in out:
            out[it["id"]] = it
    return out


def ask(user: str, n_items: int, timeout: float) -> dict[str, dict]:
    """One verifier call on its own executor, bounded by `timeout`. Raises VerifierUnavailable on any failure."""
    if timeout < VERIFY_MIN_S:
        raise VerifierUnavailable("no time left in the budget for the verifier")
    max_tokens = min(4000, 200 + 90 * n_items)
    fut = _pool.submit(chat, SYSTEM, user, temperature=0, max_tokens=max_tokens, json_mode=True,
                       purpose="Flowchart entailment check")
    try:
        raw = fut.result(timeout=timeout)
    except FutureTimeout as e:
        fut.cancel()
        raise VerifierUnavailable("verifier timed out") from e
    except Exception as e:                                    # noqa: BLE001 - any model trouble fails closed
        raise VerifierUnavailable(f"verifier failed: {type(e).__name__}") from e
    return _parse(raw)


# ---------------------------------------------------------------- the check

def check(graph: dict, answer_text: str, *, prior_dropped: int = 0, timeout: float = VERIFY_TIMEOUT_S) -> Checked:
    """Verify every box and arrow of a validated graph ({kind, title, groups, nodes, edges} as validate() returns it).
    `prior_dropped` is validate()'s count of boxes already left out, so V6 is applied to the original reply's size."""
    shown, item_refs, user = build_items(graph, answer_text)
    verdicts = ask(user, len(item_refs), timeout)
    if not set(verdicts) & set(item_refs):
        raise VerifierUnavailable("verifier reply names none of the items")
    notes: list[str] = []

    def keep(item_id: str, what: str) -> str | None:
        v = verdicts.get(item_id)
        texts = []
        for i in item_refs[item_id]:
            texts += sentence_texts(shown[i])
        if not v or v.get("verdict") != "supported":
            notes.append(f"{what}: verifier said {v.get('verdict') if v else 'nothing'}")
            return None
        if not quote_ok(v.get("quote"), texts):
            notes.append(f"{what}: quote {str(v.get('quote'))[:80]!r} is not in a sentence it cites")
            return None
        return re.sub(r"\s+", " ", V.strip_markers(v["quote"])).strip()

    nodes = []
    for n in graph["nodes"]:
        q = keep(n["id"], f'box "{n["label"]}"')
        if q is not None:
            nodes.append({**n, "evidence": q})
    kept = {n["id"] for n in nodes}
    label = {n["id"]: n["label"] for n in graph["nodes"]}
    edges = []
    for k, e in enumerate(graph["edges"]):
        if e["from"] not in kept or e["to"] not in kept:
            continue                                          # never bridged
        q = keep(f"e{k + 1}", f'arrow "{label[e["from"]]}" -> "{label[e["to"]]}"')
        if q is not None:
            edges.append({**e, "evidence": q})

    # re-apply the validator's rules on what is left (same order as validate(): lone boxes, V6, MIN_NODES, E4)
    n_total = len(graph["nodes"]) + prior_dropped
    failed = prior_dropped + len(graph["nodes"]) - len(nodes)
    ids = [n["id"] for n in nodes]
    lone = [next(iter(c)) for c in V._components(ids, edges) if len(c) == 1]
    if lone and (failed + len(lone)) / n_total <= V.FAIL_CEILING:
        nodes = [n for n in nodes if n["id"] not in set(lone)]
        failed += len(lone)
        notes += [f'box "{label[i]}" lost all its arrows' for i in lone]
    ids = [n["id"] for n in nodes]
    if failed / n_total > V.FAIL_CEILING or len(ids) < V.MIN_NODES or not V._connected(ids, edges):
        return Checked(False, "too_few_supported_nodes", dropped=failed, notes=notes)
    return Checked(True, None, {**graph, "nodes": nodes, "edges": edges}, dropped=failed, notes=notes)


def fact_ns(graph: dict) -> set[int]:
    """[G#] numbers the graph still cites (for the fact_sources list)."""
    return {c["n"] for x in graph["nodes"] + graph["edges"] for c in x["cites"] if c["kind"] == "fact"}
