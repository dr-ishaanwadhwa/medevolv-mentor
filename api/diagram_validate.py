"""Deterministic validator for LLM-drawn flowcharts (PRD 4.1: V1-V6, E1-E5).

The LLM may only RESTRUCTURE the already-cited answer. This module decides, with no model and no network, which of
its boxes and arrows survive: every node and edge must cite markers ([n] passage, [G#] graph fact) that exist and
appear in the answer, and the words of the label (or of both endpoints, for an arrow) must be supported by the answer
sentences that carry those markers. Nothing is ever bridged: a dropped node drops its arrows, and a graph that falls
apart or shrinks below 3 nodes is declined, not repaired.

    validate(raw, answer_text=..., passage_ns={1, 2}, fact_ns={1}) -> Result
    raises SchemaError(message) for the retryable "not the JSON we asked for" cases (V1/V2 structure).

Tightening thresholds is allowed on the eval set; loosening V3 or E1 is not (PRD risks table).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

KINDS: dict[str, tuple[int, tuple[str, ...]]] = {
    "classification": (24, ("includes", "subtype of", "is a")),
    "pathway": (18, ("passes to", "branches to", "supplies", "drains to", "joins")),
    "sequence": (14, ("causes", "leads to", "activates", "inhibits", "increases", "decreases", "then",
                      "investigate with", "treats")),
}
DIRECTIONAL_KINDS = ("pathway", "sequence")        # an arrow in these kinds claims "source comes first"
ROLES = ("start", "step", "branch", "end", "warning")
MIN_NODES = 3
MAX_LABEL = 80
SUPPORT_MIN = 0.5                                  # V4/E1: share of a label's content words found in the cited sentences
FAIL_CEILING = 0.30                                # V6: more than this share of failed nodes declines the whole diagram

# Order-sensitive verbs (E2): the source's words must appear before the target's in the cited sentence.
ORDER_VERBS = ("causes", "leads to", "passes to", "branches to")

# verb -> stems of the verb and its accepted synonyms (E2). A stem matches the start of any sentence word.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "includes": ("includ", "such as", "consist", "compris", "divided into", "classif", "types", "e.g", "categor"),
    "subtype of": ("type", "subtype", "class", "variant", "form", "kind", "categor", "group"),
    "is a": (" is a", " are ", "type", "form of", "class", "kind of", "example"),
    "passes to": ("pass", "run", "travel", "course", "continu", "extend", "project", "relay", "synaps", "proceed",
                  "go ", "goes", "enter", "reach", "terminat", "end "),
    "branches to": ("branch", "give", "gives", "divid", "split", "aris", "emerg", "bifurc", "tributar"),
    "supplies": ("suppl", "innervat", "perfus", "nourish", "vascular"),
    "drains to": ("drain", "empt", "return"),
    "joins": ("join", "unit", "merg", "form", "converg", "combin", "fus"),
    "causes": ("caus", "result", "produc", "lead", "trigger", "induc", "due to", "give rise", "manifest"),
    "leads to": ("lead", "result", "caus", "progress", "culminat", "produc", "give rise", "follow", "then"),
    "activates": ("activat", "stimulat", "trigger", "induc", "turn", "convert", "increas", "enhanc"),
    "inhibits": ("inhibit", "block", "suppress", "antagonis", "prevent", "impair", "reduc", "decreas"),
    "increases": ("increas", "rais", "elevat", "enhanc", "promot", "up-regulat", "upregulat", "boost", "rise"),
    "decreases": ("decreas", "reduc", "lower", "fall", "declin", "down-regulat", "downregulat", "diminish", "drop"),
    "then": ("then", "follow", "next", "after", "subsequent", "later", "finally", "step", "thereafter"),
    "investigate with": ("investigat", "confirm", "diagnos", "test", "imaging", "biops", "measur", "cultur", "order",
                         "scan", "assay", "screen", "xray", "x-ray"),
    "treats": ("treat", "therap", "first-line", "first line", "drug of choice", "manag", "given", "use", "indicat"),
}
POS_VERBS = ("activates", "increases", "causes", "leads to")
NEG_VERBS = ("inhibits", "decreases")
POS_STEMS = ("activat", "stimulat", "increas", "rais", "elevat", "enhanc", "promot", "upregulat", "up-regulat", "caus",
             "lead", "produc", "induc", "trigger", "boost")
NEG_STEMS = ("inhibit", "decreas", "reduc", "lower", "suppress", "block", "antagonis", "prevent", "deplet",
             "downregulat", "down-regulat", "diminish", "impair")

NEGATION = frozenset({"not", "never", "no", "without", "unless", "neither", "nor", "cannot", "none"})
WARNING_CUES = ("never", "contraindicated", "avoid", "must not", "warning", "do not", "should not", "danger")

STOP = frozenset("""a an the of in on at to for from by with and or but is are was were be been being as it its this that
these those which who whom whose into onto than then there their they them he she his her we you your i our not no nor
so such if when while after before during also can may might will would should could has have had do does did done
via per vs etc e g i e other others each both either any all some most more less than very about over under between
among within through""".split())

# Dose, duration and frequency are never drawn (PRD 4.1 V4): a flowchart must not look like a prescription.
_DOSE = re.compile(
    r"\b\d+(?:[.,]\d+)?(?:\s*(?:-|–|to)\s*\d+(?:[.,]\d+)?)?\s*"
    r"(?:mg|mcg|µg|ug|g|kg|ml|l|iu|units?|u|meq|mmol|hours?|hrs?|h|days?|weeks?|wks?|months?|mins?|minutes?|seconds?|"
    r"times|x)\b(?:\s*/\s*(?:kg|day|d|hr|h|dose|min|m2))?", re.I)
_PCT = re.compile(r"\b\d+(?:[.,]\d+)?\s*%")
_FREQ = re.compile(r"\b(?:once|twice|thrice)\s+(?:a\s+|per\s+)?(?:daily|day|week|weekly)\b|"
                   r"\b(?:every|q)\s*\d+\s*(?:h|hrs?|hours?|days?|weeks?)\b|"
                   r"\b(?:bd|bid|tid|tds|qid|qds|od|qd|prn|stat)\b|\b(?:daily|weekly|monthly)\b", re.I)


class SchemaError(ValueError):
    """The reply is not a graph we can validate (V1/V2 structure). The caller retries once with this message."""


@dataclass
class Result:
    ok: bool
    reason: str | None = None
    graph: dict | None = None                       # {kind, title, groups: [], nodes, edges}
    dropped: int = 0
    fact_ns: set = field(default_factory=set)       # [G#] numbers the surviving graph cites


# ---------------------------------------------------------------- text helpers

def strip_numbers_of_dose(label: str) -> str:
    out = _PCT.sub(" ", _DOSE.sub(" ", label or ""))
    out = _FREQ.sub(" ", out)
    out = re.sub(r"\(\s*[,;/\- ]*\)", " ", out)
    out = re.sub(r"\s+", " ", out)
    return out.strip(" ,;:-–/()")


def _stem(w: str) -> str:
    w = w.lower()
    for suf in ("ations", "ation", "ities", "ing", "ies", "ed", "es", "ly", "al", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf == "ies" else "")
    return w


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'\-]*", (text or "").lower())


def content_words(text: str) -> set[str]:
    return {_stem(t) for t in tokens(text) if t not in STOP and not t.isdigit() and len(t) > 1}


def numbers_in(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


def support(label: str, sentence_words: set[str]) -> float:
    lw = content_words(label)
    return len(lw & sentence_words) / len(lw) if lw else 0.0


_MARK = re.compile(r"\[([^\[\]]{1,40})\]")


def markers_in(text: str) -> set[tuple[str, int]]:
    """{('passage', n) | ('fact', n)} for every [n], [n, m], [G1], [G1, G2] in the text."""
    out: set[tuple[str, int]] = set()
    for m in _MARK.finditer(text):
        body = m.group(1)
        if not re.fullmatch(r"\s*G?\d+(?:\s*,\s*G?\d+)*\s*", body):
            continue
        toks = [t.strip() for t in body.split(",")]
        fact = toks[0].upper().startswith("G")
        for t in toks:
            out.add(("fact" if fact or t.upper().startswith("G") else "passage", int(t.lstrip("Gg"))))
    return out


def strip_markers(text: str) -> str:
    return re.sub(r"\s+", " ", _MARK.sub(" ", text or "")).strip()


def sentences(answer_text: str) -> list[str]:
    """Answer sentences, each keeping its markers. A segment that is only markers joins the sentence before it."""
    text = (answer_text or "").replace("\r\n", "\n")
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\[(*\-•\d])|\n+", text)
    out: list[str] = []
    for p in parts:
        p = re.sub(r"^\s*(?:[*\-•>#]+|\d+[.)])\s+", "", p.strip())
        if not p:
            continue
        if out and not strip_markers(p).strip(" .,;:*-"):
            out[-1] += " " + p
        else:
            out.append(p)
    return out


# ---------------------------------------------------------------- cites

def _norm_cite(c) -> tuple[str, int] | None:
    if isinstance(c, dict):
        kind, n = c.get("kind"), c.get("n")
        if kind in ("passage", "fact") and isinstance(n, int) and not isinstance(n, bool):
            return (kind, n)
        return None
    if isinstance(c, str):
        m = re.fullmatch(r"\s*\[?\s*(G?)(\d+)\s*\]?\s*", c, re.I)
        if m:
            return ("fact" if m.group(1) else "passage", int(m.group(2)))
    if isinstance(c, int) and not isinstance(c, bool):
        return ("passage", c)
    return None


def _carriers(cites: set, sents: list[tuple[str, set, set, list[str]]]) -> list[tuple[str, set, list[str]]]:
    """Sentences (text, content words, tokens) that carry at least one of `cites`."""
    return [(t, w, tk) for t, mk, w, tk in sents if mk & cites]


# ---------------------------------------------------------------- the validator

def parse_graph(raw) -> dict:
    """V1/V2 structure. Returns {kind, title, nodes: [{id,label,role,cites}], edges: [{from,to,label,cites}]} or raises."""
    if not isinstance(raw, dict):
        raise SchemaError("The reply must be one JSON object.")
    kind = raw.get("kind")
    if kind not in KINDS:
        raise SchemaError(f"kind must be one of {sorted(KINDS)}.")
    cap, _verbs = KINDS[kind]
    nodes_in, edges_in = raw.get("nodes"), raw.get("edges")
    if not isinstance(nodes_in, list) or not isinstance(edges_in, list):
        raise SchemaError("nodes and edges must be lists.")
    nodes, ids = [], set()
    for n in nodes_in:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or not isinstance(n.get("label"), str):
            raise SchemaError("every node needs a string id and a string label.")
        if n["id"] in ids:
            raise SchemaError(f"duplicate node id {n['id']}.")
        if not n["label"].strip() or len(n["label"]) > MAX_LABEL:
            raise SchemaError(f"node labels must be 1 to {MAX_LABEL} characters.")
        ids.add(n["id"])
        role = n.get("role") if n.get("role") in ROLES else "step"
        cites = n.get("cites") if isinstance(n.get("cites"), list) else []
        nodes.append({"id": n["id"], "label": n["label"].strip(), "role": role, "cites": cites})
    if not MIN_NODES <= len(nodes) <= cap:
        raise SchemaError(f"a {kind} diagram needs {MIN_NODES} to {cap} nodes, you gave {len(nodes)}.")
    edges = []
    for e in edges_in:
        if not isinstance(e, dict) or e.get("from") not in ids or e.get("to") not in ids:
            raise SchemaError("every edge must reference existing node ids in from and to.")
        if e["from"] == e["to"]:
            raise SchemaError("self-loops are not allowed.")
        label = e.get("label") if isinstance(e.get("label"), str) else ""
        cites = e.get("cites") if isinstance(e.get("cites"), list) else []
        edges.append({"from": e["from"], "to": e["to"], "label": label.strip().lower(), "cites": cites})
    title = raw.get("title") if isinstance(raw.get("title"), str) else None
    g = {"kind": kind, "title": title, "nodes": nodes, "edges": edges}
    if not _connected([n["id"] for n in nodes], edges):
        raise SchemaError("the graph must be connected.")
    return g


def _connected(ids: list[str], edges: list[dict]) -> bool:
    if not ids:
        return False
    adj: dict[str, set] = {i: set() for i in ids}
    for e in edges:
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].add(e["to"])
            adj[e["to"]].add(e["from"])
    seen, todo = set(), [ids[0]]
    while todo:
        x = todo.pop()
        if x not in seen:
            seen.add(x)
            todo.extend(adj[x] - seen)
    return len(seen) == len(ids)


def _first_pos(label_words: set[str], toks: list[str]) -> int | None:
    for i, t in enumerate(toks):
        if _stem(t) in label_words:
            return i
    return None


def _has_syn(verb: str, text_low: str, toks: list[str]) -> bool:
    for s in SYNONYMS.get(verb, ()):
        if " " in s or s.startswith(" "):
            if s in f" {text_low} ":
                return True
        elif any(t.startswith(s) for t in toks):
            return True
    return False


def _has_stem(stems: tuple[str, ...], toks: list[str]) -> bool:
    return any(t.startswith(s) for s in stems for t in toks)


def _edge_ok(e: dict, src: dict, tgt: dict, carriers: list, kind: str) -> tuple[bool, str]:
    """E1-E3 on the sentences that carry the edge's cites. Returns (keep, label to show)."""
    label = e["label"]
    sw, tw = content_words(src["label"]), content_words(tgt["label"])
    for text, words, toks in carriers:
        if support(src["label"], words) < SUPPORT_MIN or support(tgt["label"], words) < SUPPORT_MIN:       # E1
            continue
        clean = strip_markers(text)
        low = clean.lower()
        # E3: a negation in the supporting sentence that the boxes and the arrow do not carry fails this sentence
        own = set(tokens(src["label"])) | set(tokens(tgt["label"])) | set(tokens(label))
        if (NEGATION & set(toks) or "n't" in low) and not (NEGATION & own):
            continue
        show = label
        if label:
            if _has_syn(label, low, toks):                                                                 # E2 verb
                pass
            else:
                opposite = NEG_STEMS if label in POS_VERBS else POS_STEMS if label in NEG_VERBS else ()
                if opposite and _has_stem(opposite, toks):
                    continue                                                                               # antonym: drop
                show = ""
        if label in ORDER_VERBS or kind in DIRECTIONAL_KINDS:                                              # E2 order
            s_only, t_only = (sw - tw) or sw, (tw - sw) or tw
            ps, pt = _first_pos(s_only, toks), _first_pos(t_only, toks)
            if ps is None or pt is None or ps >= pt:
                continue
        return True, show
    return False, ""


def validate(raw, *, answer_text: str, passage_ns: set[int], fact_ns: set[int]) -> Result:
    g = parse_graph(raw)
    kind = g["kind"]
    _, verbs = KINDS[kind]
    sents = [(s, markers_in(s), content_words(strip_markers(s)), tokens(strip_markers(s))) for s in sentences(answer_text)]
    present = set().union(*(mk for _, mk, _, _ in sents)) if sents else set()
    allowed = {("passage", n) for n in passage_ns} | {("fact", n) for n in fact_ns}
    usable = allowed & present                                   # V3: exists in the citations AND appears in the text

    def cites_of(raw_cites) -> set:
        norm = {_norm_cite(c) for c in raw_cites}
        return {c for c in norm if c is not None} & usable

    # ---- nodes: V3, V4
    kept: dict[str, dict] = {}
    for n in g["nodes"]:
        cites = cites_of(n["cites"])
        label = strip_numbers_of_dose(n["label"])
        if not cites or not label:
            continue
        carry = _carriers(cites, sents)
        words = set().union(*(w for _, w, _ in carry)) if carry else set()
        text = " ".join(t for t, _, _ in carry)
        if support(label, words) < SUPPORT_MIN:
            continue
        if any(num not in numbers_in(strip_markers(text)) for num in numbers_in(label)):    # no new numbers
            continue
        role = n["role"]
        if role == "warning" and not any(c in strip_markers(text).lower() for c in WARNING_CUES):   # E5
            role = "step"
        kept[n["id"]] = {"id": n["id"], "label": label[:MAX_LABEL], "role": role, "cites": cites}
    n_total = len(g["nodes"])
    failed = n_total - len(kept)
    if failed / n_total > FAIL_CEILING:                                                      # V6
        return Result(False, "too_few_supported_nodes", dropped=failed)

    # ---- edges: V3, V5, E1-E4 (an edge to a dropped node is dropped, never bridged)
    edges = []
    for e in g["edges"]:
        if e["from"] not in kept or e["to"] not in kept:
            continue
        cites = cites_of(e["cites"])
        if not cites:
            continue
        label = e["label"] if e["label"] in verbs else ""                                    # V5
        ok, show = _edge_ok({**e, "label": label}, kept[e["from"]], kept[e["to"]], _carriers(cites, sents), kind)
        if ok:
            edges.append({"from": e["from"], "to": e["to"], "label": show, "cites": cites})
    ids = list(kept)
    if len(ids) < MIN_NODES or not _connected(ids, edges):                                   # E4
        return Result(False, "too_few_supported_nodes", dropped=failed)

    out_ids = {old: f"n{i}" for i, old in enumerate(ids, 1)}

    def cj(cs: set) -> list[dict]:
        return [{"kind": k, "n": n} for k, n in sorted(cs)]
    nodes = [{"id": out_ids[i], "label": kept[i]["label"], "role": kept[i]["role"], "group": None,
              "cites": cj(kept[i]["cites"])} for i in ids]
    out_edges = [{"from": out_ids[e["from"]], "to": out_ids[e["to"]], "label": e["label"], "cites": cj(e["cites"])}
                 for e in edges]
    title = None
    t = (g["title"] or "").strip()
    if t and len(t) <= MAX_LABEL:
        all_words = set().union(*(w for _, _, w, _ in sents)) if sents else set()
        if support(strip_numbers_of_dose(t), all_words) >= SUPPORT_MIN and not numbers_in(strip_numbers_of_dose(t)):
            title = strip_numbers_of_dose(t)
    used_facts = {n for nd in nodes for c in nd["cites"] if c["kind"] == "fact" for n in [c["n"]]}
    used_facts |= {c["n"] for e in out_edges for c in e["cites"] if c["kind"] == "fact"}
    return Result(True, None, {"kind": kind, "title": title, "groups": [], "nodes": nodes, "edges": out_edges},
                  dropped=failed, fact_ns=used_facts)
