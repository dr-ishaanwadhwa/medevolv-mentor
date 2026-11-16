"""Deterministic validator for LLM-drawn flowcharts (PRD 4.1: V1-V6, E1-E5).

The LLM may only RESTRUCTURE the already-cited answer. This module decides, with no model and no network, which of
its boxes and arrows survive: every node and edge must cite markers ([n] passage, [G#] graph fact) that exist and
appear in the answer, and the words of the label (or of both endpoints, for an arrow) must be supported by the answer
sentences that carry those markers. Nothing is ever bridged: a dropped node drops its arrows, and a graph that falls
apart or shrinks below 3 nodes is declined, not repaired.

    validate(raw, answer_text=..., passage_ns={1, 2}, fact_ns={1}) -> Result
    raises SchemaError(message) for the retryable "not the JSON we asked for" cases (V1/V2 structure).

Tightening thresholds is allowed on the eval set; loosening V3 or E1 is not (PRD risks table).

Answer structure the validator reads (it never adds words, only keeps the answer's own words together):
- A list item belongs to the line that introduces it: a lead-in ending in ":" ("The facial nerve gives off the following
  branches:"), a bold or # heading ("**Cardioselective (β1)**") and a parent bullet ending in ":". Those words are the
  item's CONTEXT, read before the item's own words. An item with no marker of its own inherits the markers of a cited
  lead-in ("The superior orbital fissure transmits [1]:"). A plain paragraph line ends every list context.
- An arrow's evidence unit is the ";"-clause of one cited sentence that holds both boxes (plus the item's context), so
  a negation, verb or antonym in another clause neither blocks nor confirms it. With no such clause, the whole sentence.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import NamedTuple

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
RULES_VERSION = 3                                  # part of the diagram cache key: a rules change re-validates cached declines

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
# Direction verbs only: an antonym in the sentence (book says "decreases", arrow says "increases") drops the edge.
# "causes" / "leads to" are sequence verbs, not direction claims: pharmacology mechanisms are full of "blocking X
# destroys Y", so an inhibitory word there is not an antonym; an unconfirmed sequence verb is just not shown (E2).
POS_VERBS = ("activates", "increases")
NEG_VERBS = ("inhibits", "decreases")
POS_STEMS = ("activat", "stimulat", "increas", "rais", "elevat", "enhanc", "promot", "upregulat", "up-regulat", "caus",
             "lead", "produc", "induc", "trigger", "boost")
NEG_STEMS = ("inhibit", "decreas", "reduc", "lower", "suppress", "block", "antagonis", "prevent", "deplet",
             "downregulat", "down-regulat", "diminish", "impair")

NEGATION = frozenset({"not", "never", "no", "without", "unless", "neither", "nor", "cannot", "none"})
WARNING_CUES = ("never", "contraindicated", "avoid", "must not", "warning", "do not", "should not", "danger")
# "Y is a consequence of X", "Y because X": the words between the two boxes reverse the causal direction (E2 order).
BACKWARD = ("consequence of", "result of", "results from", "resulting from", "due to", "caused by", "secondary to",
            "because", "owing to", "induced by", "mediated by", "driven by", "stems from", "arises from")
# A later sentence that opens with one of these continues the previous step ("This causes ...", "Then it binds ...").
STEP_OPENERS = frozenset({"then", "next", "subsequently", "thereafter", "thereby", "thus", "hence", "therefore",
                          "consequently", "finally", "this", "these", "which", "so", "eventually", "later"})
STEP_OPENER_STEMS = ("lead", "result", "caus", "ensu", "trigger", "follow", "produc", "induc", "progress")

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
    notes: list = field(default_factory=list)       # why boxes/arrows failed (feedback for the one retry; never shown)


# ---------------------------------------------------------------- text helpers

def strip_numbers_of_dose(label: str) -> str:
    out = _PCT.sub(" ", _DOSE.sub(" ", label or ""))
    out = _FREQ.sub(" ", out)
    out = re.sub(r"\(\s*[,;/\- ]*\)", " ", out)
    out = re.sub(r"\s+", " ", out)
    out = out.strip(" ,;:-–/")
    while out and (out[-1] == "(" or (out[-1] == ")" and out.count(")") > out.count("("))):     # only unbalanced parens
        out = out[:-1].rstrip(" ,;:-–/")
    while out and (out[0] == ")" or (out[0] == "(" and out.count("(") > out.count(")"))):
        out = out[1:].lstrip(" ,;:-–/")
    return out


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


def node_supported(label: str, words: set[str]) -> bool:
    """V4. A label of one or two content words needs all of them (half of "Optic nerve" is just "nerve", which any
    list of nerves has); a longer label needs SUPPORT_MIN of them."""
    lw = content_words(label)
    if not lw:
        return False
    return support(label, words) >= (1.0 if len(lw) <= 2 else SUPPORT_MIN)


_MARK = re.compile(r"\[([^\[\]]{1,40})\]")
_CITE_MARK = re.compile(r"\[\s*G?\d+(?:\s*,\s*G?\d+)*\s*\]", re.I)     # only real citation markers, not "[VII]" or "[V1]"


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
    """Removes citation markers only; an anatomical label in brackets ("facial nerve [VII]") is answer text and stays."""
    return re.sub(r"\s+", " ", _CITE_MARK.sub(" ", text or "")).strip()


_ITEM = re.compile(r"^(\s*)(?:[*\-•+]+|\d+[.)])\s+")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+")
_HEADING = re.compile(r"^\s*(?:#{1,6}\s+(?P<h>[^\n]{1,80})|\*\*(?P<b>[^*\n]{1,80})\*\*\s*:?)\s*$")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\[(*\-•\d])")


@dataclass
class Sent:
    text: str                 # the sentence with its markers (its own, or those inherited from a cited lead-in)
    ctx: str = ""             # words of the lead-in / heading / parent bullet that introduce this list item ("" if none)
    block: int = 0            # the paragraph or bullet line it comes from
    numbered: bool = False    # an item of a numbered list (1. 2. 3.): the answer orders those steps itself
    mk: set = field(default_factory=set)
    words: set = field(default_factory=set)       # content words of ctx + sentence
    toks: list = field(default_factory=list)      # tokens of ctx + sentence, ctx first
    own: set = field(default_factory=set)         # content words of the sentence alone


def _sent(text: str, ctx: str, block: int, numbered: bool) -> Sent:
    full = f"{ctx} {strip_markers(text)}".strip()
    return Sent(text, ctx, block, numbered, markers_in(text), content_words(full), tokens(full),
                content_words(strip_markers(text)))


def parse_answer(answer_text: str) -> list[Sent]:
    """Answer sentences with their list context (see module docstring). A segment that is only markers joins the
    sentence before it. The context is the answer's own words, in the answer's own order; nothing is added."""
    lines = (answer_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[Sent] = []
    lead = lead_marks = head = ""
    sub: tuple[int, str, str] | None = None          # (indent, text, markers) of a parent bullet ending in ":"
    block = 0

    def emit(body: str, ctx: str, inherit: str, numbered: bool) -> None:
        for part in _SPLIT.split(body):
            part = re.sub(r"^\s*(?:[*\-•>#]+|\d+[.)])\s+", "", part.strip())
            if not part:
                continue
            if out and not strip_markers(part).strip(" .,;:*-"):
                out[-1] = _sent(out[-1].text + " " + part, out[-1].ctx, out[-1].block, out[-1].numbered)
                continue
            out.append(_sent(f"{part} {inherit}".strip(), ctx, block, numbered))

    for line in lines:
        if not line.strip():
            continue
        block += 1
        m = _ITEM.match(line)
        if m:
            indent, body = len(m.group(1).expandtabs(4)), line[m.end():].strip()
            if sub and indent <= sub[0]:
                sub = None
            ctx = " ".join(x for x in (lead, head, sub[1] if sub else "") if x)
            inherit = "" if markers_in(body) else (sub[2] if sub and sub[2] else lead_marks)
            emit(body, ctx, inherit, bool(_NUMBERED.match(line)))
            clean = strip_markers(body).strip()
            if clean.endswith(":"):
                own = " ".join(sorted({m.group(0) for m in _CITE_MARK.finditer(body)}))
                sub = (indent, clean.rstrip(": ").replace("*", ""), own or inherit)
            continue
        h = _HEADING.match(line)
        if h and not markers_in(line):
            head, sub = (h.group("h") or h.group("b")).strip(" :*#"), None
            emit(line.strip(), "", "", False)
            continue
        clean = strip_markers(line).strip()
        head, sub = "", None
        if clean.endswith(":"):
            lead = clean.rstrip(": ").replace("*", "")
            lead_marks = " ".join(m.group(0) for m in _CITE_MARK.finditer(line))
        else:
            lead = lead_marks = ""
        emit(line.strip(), "", "", False)
    return out


def sentences(answer_text: str) -> list[str]:
    """Answer sentences, each keeping its markers (list items under a cited lead-in carry the lead-in's markers)."""
    return [s.text for s in parse_answer(answer_text)]


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


def _carriers(cites: set, sents: list[Sent]) -> list[Sent]:
    """Sentences that carry at least one of `cites`."""
    return [s for s in sents if s.mk & cites]


# ---------------------------------------------------------------- the validator

def _shorten(label: str) -> str:
    """A label a little over MAX_LABEL is cut at a word boundary with an ellipsis (words removed, none added; the support
    check then runs on what is left). Labels far over the limit are left as they are, and validate() drops that box."""
    s = label.strip()
    if len(s) <= MAX_LABEL or len(s) > 2 * MAX_LABEL:
        return s
    cut = s[: MAX_LABEL - 1].rsplit(" ", 1)[0].rstrip(" ,;:-(")
    return cut + "…"


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
        n = {**n, "label": _shorten(n["label"])}
        if not n["label"].strip():
            raise SchemaError("node labels must not be empty.")
        # a label far over MAX_LABEL is one box we cannot draw, not a malformed reply: validate() drops it (V6 counts it)
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
    # Connectivity (E4) is NOT a structure error: a faithful drawing of a list of separate features is disconnected, and
    # asking the model to "connect it" only invites invented links. E4 is checked once, after validation, in validate().
    return {"kind": kind, "title": title, "nodes": nodes, "edges": edges}


MAX_STEP_GAP = 3     # E2 fallback: the target may sit up to 3 sentences after the source, in the same section
MAX_CHAINS = 3      # a comparison ("A vs B") is honestly drawn as separate chains, one per item; never bridged by an invented edge


def _components(ids: list[str], edges: list[dict]) -> list[set]:
    adj: dict[str, set] = {i: set() for i in ids}
    for e in edges:
        if e["from"] in adj and e["to"] in adj:
            adj[e["from"]].add(e["to"])
            adj[e["to"]].add(e["from"])
    seen: set = set()
    comps = []
    for start in ids:
        if start in seen:
            continue
        comp, todo = set(), [start]
        while todo:
            x = todo.pop()
            if x not in comp:
                comp.add(x)
                todo.extend(adj[x] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def _connected(ids: list[str], edges: list[dict]) -> bool:
    """Well-formed layout (E4): one connected graph, or up to MAX_CHAINS separate chains of at least 2 nodes each.
    A lone node is never allowed, so a box whose only supporting edge failed still declines rather than floating."""
    if not ids:
        return False
    comps = _components(ids, edges)
    return len(comps) == 1 or (len(comps) <= MAX_CHAINS and all(len(c) >= 2 for c in comps))


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


def _negated(low: str, toks: list[str], own: set[str]) -> bool:
    """E3: a negation in the evidence unit that the boxes and the arrow do not carry themselves."""
    return bool((NEGATION & set(toks) or "n't" in low) and not (NEGATION & own))


def _antonym(label: str, low: str, toks: list[str]) -> bool:
    if not label or _has_syn(label, low, toks):
        return False
    opposite = NEG_STEMS if label in POS_VERBS else POS_STEMS if label in NEG_VERBS else ()
    return bool(opposite and _has_stem(opposite, toks))


class Unit(NamedTuple):
    low: str                  # lowercase text: list context, then the clause
    toks: list                # its tokens, context first
    own: set                  # content words of the clause alone
    ctx: set                  # content words of the list context alone
    n_ctx: int                # how many leading tokens are context


def _sup(label: str, u: Unit) -> float:
    """A box is supported by the sentence's own words OR by its list context (a box that IS the heading or lead-in),
    never by a blend: context words never top up an item's box."""
    return max(support(label, u.own), support(label, u.ctx))


def _in_unit(label: str, u: Unit, strict: bool = False) -> bool:
    """E1 for one box: own words or list context, never a blend. `strict` (classification arrows, whose only evidence
    is that both boxes sit in one unit; directional arrows must also be found in order) applies the V4 standard, so a
    two-word box is not placed by one generic word ("effects", "nerve")."""
    if strict:
        return node_supported(label, u.own) or node_supported(label, u.ctx)
    return _sup(label, u) >= SUPPORT_MIN


def _units(s: Sent, labels: list[str], strict: bool = False) -> list[Unit]:
    """Evidence units of one cited sentence for these boxes: each ";"-clause (read after the item's list context) in
    which every label reaches SUPPORT_MIN; when no single clause holds them all, the whole sentence. A unit is always a
    piece of the answer's own text, so it can only lose words, never gain any."""
    body = strip_markers(s.text)
    ctx_w, n_ctx = content_words(s.ctx), len(tokens(s.ctx))
    clauses = [c for c in body.split(";") if c.strip()]
    out = []
    if len(clauses) > 1:
        for c in clauses:
            u = Unit(f"{s.ctx} {c}".strip().lower(), tokens(f"{s.ctx} {c}"), content_words(c), ctx_w, n_ctx)
            if all(_in_unit(lb, u, strict) for lb in labels):
                out.append(u)
    if not out:
        out.append(Unit(f"{s.ctx} {body}".strip().lower(), s.toks, s.own, ctx_w, n_ctx))
    return out


def _order(src_label: str, tgt_label: str, u: Unit) -> str:
    """E2 order inside one evidence unit: 'forward', 'reversed' or 'unknown'. Words order the boxes, except that a
    backward connective between them ("Y is a consequence of X", "Y because X") states the opposite direction. A box
    supported by its list context (the heading or lead-in) sits in the context, before the item's own words."""
    sw, tw = content_words(src_label), content_words(tgt_label)
    s_only, t_only = (sw - tw) or sw, (tw - sw) or tw

    def pos(label: str, words: set[str]) -> int | None:
        if support(label, u.own) >= SUPPORT_MIN:
            p = _first_pos(words, u.toks[u.n_ctx:])
            return None if p is None else u.n_ctx + p
        return _first_pos(words, u.toks[:u.n_ctx])

    ps, pt = pos(src_label, s_only), pos(tgt_label, t_only)
    if ps is None or pt is None or ps == pt:
        return "unknown"
    lo, hi = min(ps, pt), max(ps, pt)
    between = f" {' '.join(u.toks[lo + 1:hi])} "
    forward = ps < pt
    if any(f" {c} " in between for c in BACKWARD):
        forward = not forward
    return "forward" if forward else "reversed"


def _directional(label: str, kind: str) -> bool:
    return label in ORDER_VERBS or kind in DIRECTIONAL_KINDS


def _edge_ok(e: dict, src: dict, tgt: dict, carriers: list[Sent], kind: str) -> tuple[bool, str]:
    """E1-E3 on the evidence units of the sentences that carry the edge's cites. Returns (keep, label to show)."""
    label = e["label"]
    own = set(tokens(src["label"])) | set(tokens(tgt["label"])) | set(tokens(label))
    strict = kind == "classification"
    for s in carriers:
        for u in _units(s, [src["label"], tgt["label"]], strict):
            low, toks = u.low, u.toks
            if not (_in_unit(src["label"], u, strict) and _in_unit(tgt["label"], u, strict)):               # E1
                continue
            if _negated(low, toks, own):                                                                    # E3
                continue
            show = label
            if label and not _has_syn(label, low, toks):                                                   # E2 verb
                if _antonym(label, low, toks):
                    continue                                                                               # antonym: drop
                show = ""
            if _directional(label, kind) and _order(src["label"], tgt["label"], u) != "forward":                    # E2 order
                continue
            return True, show
    return False, ""


def _contradicted(label: str, src: dict, tgt: dict, carriers: list[Sent], kind: str) -> bool:
    """True when a cited unit that holds BOTH boxes says something the arrow would contradict: a negation the boxes
    don't carry (E3), the opposite direction verb (antonym), or, for a directional arrow, the target before the source
    (reversed order, backward connectives included). 'Order could not be confirmed' is not a contradiction."""
    own = set(tokens(src["label"])) | set(tokens(tgt["label"])) | set(tokens(label))
    for s in carriers:
        for u in _units(s, [src["label"], tgt["label"]]):
            low, toks = u.low, u.toks
            if _sup(src["label"], u) < SUPPORT_MIN or _sup(tgt["label"], u) < SUPPORT_MIN:
                continue
            if _negated(low, toks, own) or _antonym(label, low, toks):
                return True
            if _directional(label, kind) and _order(src["label"], tgt["label"], u) == "reversed":
                return True
    return False


_SEQ_LEAD = ("step", "stage", "sequen", "cascade", "phase", "chronolog", "event")


def _continues(prev: Sent, s: Sent) -> bool:
    """The answer itself says sentence `s` is the next step after `prev`: a numbered list (1. 2. 3.), a lead-in that
    announces steps ("The events occur in the following stages:"), or `s` opens with a step word ("This causes ...",
    "It then binds ...", "Thereafter ..."). Plain bullets under "features include:" are NOT steps."""
    if prev.numbered and s.numbered:
        return True
    if s.ctx and s.ctx == prev.ctx and _has_stem(_SEQ_LEAD, tokens(s.ctx)):
        return True
    head = tokens(strip_markers(s.text))[:4]
    if not head:
        return False
    return (head[0] in STEP_OPENERS - {"this", "these", "which", "so"} or "then" in head
            or any(t.startswith(st) for t in head for st in STEP_OPENER_STEMS))


def _adjacent_ok(e: dict, src: dict, tgt: dict, cites: set, sents: list[Sent]) -> bool:
    """E2 fallback for step-per-sentence answers: the source box is supported by cited sentence i and the target box by
    a later sentence j of the same section (at most MAX_STEP_GAP on) that the answer marks as the next step (see
    _continues), so the arrow only restates the order the answer gives. No verb, and not when the clause that supports
    either box carries a negation the boxes don't."""
    own = set(tokens(src["label"])) | set(tokens(tgt["label"]))

    def ok_at(i: int, label: str) -> bool:
        s = sents[i]
        if not (s.mk & cites):
            return False
        return any(_in_unit(label, u) and not _negated(u.low, u.toks, own) for u in _units(s, [label]))

    def same_section(i: int, j: int) -> bool:          # a sentence with no marker (a heading) ends a section
        return all(sents[k].mk for k in range(i + 1, j))

    return any(ok_at(i, src["label"]) and ok_at(j, tgt["label"]) and same_section(i, j) and _continues(sents[j - 1], sents[j])
               and all(_continues(sents[k - 1], sents[k]) for k in range(i + 1, j))
               for i in range(len(sents)) for j in range(i + 1, min(i + 1 + MAX_STEP_GAP, len(sents))))


def validate(raw, *, answer_text: str, passage_ns: set[int], fact_ns: set[int]) -> Result:
    g = parse_graph(raw)
    kind = g["kind"]
    _, verbs = KINDS[kind]
    sents = parse_answer(answer_text)
    present = set().union(*(s.mk for s in sents)) if sents else set()
    allowed = {("passage", n) for n in passage_ns} | {("fact", n) for n in fact_ns}
    usable = allowed & present                                   # V3: exists in the citations AND appears in the text
    notes: list[str] = []                                        # what failed, for the one retry's feedback

    def cites_of(raw_cites) -> set:
        norm = {_norm_cite(c) for c in raw_cites}
        return {c for c in norm if c is not None} & usable

    # ---- nodes: V3, V4
    kept: dict[str, dict] = {}
    for n in g["nodes"]:
        if len(n["label"]) > MAX_LABEL:
            notes.append(f'box "{n["label"][:60]}…" is longer than {MAX_LABEL} characters')
            continue
        cites = cites_of(n["cites"])
        label = strip_numbers_of_dose(n["label"])
        if not cites or not label:
            notes.append(f'box "{n["label"]}" cites no marker that appears in the answer')
            continue
        carry = _carriers(cites, sents)
        own_w = set().union(*(s.own for s in carry)) if carry else set()
        ctx_w = set().union(*(content_words(s.ctx) for s in carry)) if carry else set()
        text = " ".join(f"{s.ctx} {strip_markers(s.text)}" for s in carry)
        if not (node_supported(label, own_w) or node_supported(label, ctx_w)):    # own words or the heading, not a blend
            notes.append(f'box "{label}" is not worded as its cited sentence says it')
            continue
        if any(num not in numbers_in(text) for num in numbers_in(label)):                  # no new numbers
            notes.append(f'box "{label}" has a number its cited sentence does not')
            continue
        role = n["role"]
        if role == "warning" and not any(c in text.lower() for c in WARNING_CUES):          # E5
            role = "step"
        kept[n["id"]] = {"id": n["id"], "label": label[:MAX_LABEL], "role": role, "cites": cites}
    n_total = len(g["nodes"])
    failed = n_total - len(kept)
    if failed / n_total > FAIL_CEILING:                                                      # V6
        return Result(False, "too_few_supported_nodes", dropped=failed, notes=notes)

    # ---- edges: V3, V5, E1-E3 (an edge to a dropped node is dropped, never bridged)
    edges = []
    contradicted: set[str] = set()                   # boxes with an arrow the answer contradicts: never pruned below
    for e in g["edges"]:
        if e["from"] not in kept or e["to"] not in kept:
            continue
        src, tgt = kept[e["from"]], kept[e["to"]]
        cites = cites_of(e["cites"])
        label = e["label"] if e["label"] in verbs else ""                                    # V5
        carriers = _carriers(cites | src["cites"] | tgt["cites"], sents)
        ok, show = _edge_ok({**e, "label": label}, src, tgt, _carriers(cites, sents), kind) if cites else (False, "")
        if not ok and _contradicted(label, src, tgt, carriers, kind):     # boxes' own sentences count as evidence too
            contradicted |= {e["from"], e["to"]}
        elif not ok and cites and kind in DIRECTIONAL_KINDS:
            # the cross-sentence order fallback never overrides a contradiction found inside one sentence
            ok, show = _adjacent_ok(e, src, tgt, cites | src["cites"] | tgt["cites"], sents), ""
        if ok:
            edges.append({"from": e["from"], "to": e["to"], "label": show, "cites": cites})
        else:
            notes.append(f'arrow "{src["label"]}" -> "{tgt["label"]}" is not stated by a cited sentence')

    # ---- a supported box none of whose arrows the answer states (a separate feature in a list) is left out, like a box
    # that failed V4: never connected by an invented arrow, counted in `dropped`, under the same V6 ceiling. A box whose
    # arrow the answer contradicts is never left out this way: the whole diagram declines (E4) instead.
    lone = [next(iter(c)) for c in _components(list(kept), edges) if len(c) == 1]
    if lone and not (set(lone) & contradicted) and (failed + len(lone)) / n_total <= FAIL_CEILING:
        for i in lone:
            notes.append(f'box "{kept[i]["label"]}" has no arrow the answer states')
            del kept[i]
        failed += len(lone)
    ids = list(kept)
    if len(ids) < MIN_NODES or not _connected(ids, edges):                                   # E4
        for c in _components(ids, edges):
            if len(c) == 1:
                notes.append(f'box "{kept[next(iter(c))]["label"]}" has no arrow the answer states')
        return Result(False, "too_few_supported_nodes", dropped=failed, notes=notes)

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
        all_words = set().union(*(s.words for s in sents)) if sents else set()
        if support(strip_numbers_of_dose(t), all_words) >= SUPPORT_MIN and not numbers_in(strip_numbers_of_dose(t)):
            title = strip_numbers_of_dose(t)
    used_facts = {n for nd in nodes for c in nd["cites"] if c["kind"] == "fact" for n in [c["n"]]}
    used_facts |= {c["n"] for e in out_edges for c in e["cites"] if c["kind"] == "fact"}
    return Result(True, None, {"kind": kind, "title": title, "groups": [], "nodes": nodes, "edges": out_edges},
                  dropped=failed, fact_ns=used_facts)
