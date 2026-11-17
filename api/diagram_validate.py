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
- An inline bold lead ("- **Rate slowing:** ...") is the context of every sentence of its bullet.
- An arrow's evidence unit is the independent clause (";", ", while", ", whereas", ", but") of one cited sentence that
  holds both boxes (plus the item's context), so a negation, verb or antonym in another clause neither blocks nor
  confirms it. With no such clause, the whole sentence.

Grounding rules added after red-team round 1 (each only removes boxes or arrows):
- A box is supported by ONE cited sentence (never a blend of several), and its numbers must be in that sentence.
- A box keeps the answer's negation words ("Without ISA" is not placed by "With ISA"), and a direction word in a box
  must not be the opposite of the one the answer puts on that object ("Increased" vs "reduced end-diastolic volume").
- Negations are counted: a box carrying one "not" does not excuse a second "not" in the unit.
- A direction verb on an arrow is checked against the word on the target itself ("lowering ATP and raising AMP").
- "A vs B" / "unlike B" / "whereas B": an arrow across a contrast is never stated. "X is based on Y" reverses order.
- A passive step verb ("is caused by") does not mark the next sentence as the next step.

Round 2/3 (red team round 2; each rule removes boxes or arrows, except the four marked +, which read answer structure):
- A box is worded as ONE independent clause says it; box numbers (also spelled: "five", "third-") and Greek letters
  must be in its sentence; a box word whose opposite is in the text instead ("posterior" for "anterior") fails.
- Inside an arrow's unit a box is a PHRASE (its words within len(label)+2 tokens), never words scattered over the clause.
- A directional arrow inside one clause needs a linking word between the boxes; items of one comma/"and" list are
  siblings. A lead that names a place ("After X:") is not a source. A bracketed child belongs to the phrase before it.
- A direction-verb arrow needs the unit to put that direction on the target; a direction word after an object never
  crosses "and"/"or". The clause check runs for every kind.
- (+) A lead-in's clause that does not introduce the list ("X is not fully defined, but the key features are:") is
  context, not a negation of the items. (+) A negation inside a bracket that no box touches is about that bracket.
  (+) A clause that announces a sequence ("a proposed sequence includes A, B, C", "a two-step entry: A and B") orders
  its list. (+) "**X** — ..." is a bold lead like "**X:**".

Round 4 (red team round 3; each rule only removes boxes or arrows):
- A box's direction word (increased, raised, decline, rises, falls, more, less, fewer, ...) must be one the text puts
  on the same object (read per clause, also from the head of a list: "decreasing A, B and possibly C"); the text naming
  the object with no direction, or the opposite one, does not place the box. "two or more" is a count, not a direction.
- A box may not drop a negation: a word the sentence only says as the head of a "not"/"no"/"without" ("(not reversed
  by atropine)") does not place a box without that negation.
- Each number of a box stands in its sentence next to the same word as in the box ("stage 1" does not license "one
  islet autoantibody").
- A box word its sentence lacks but another answer sentence has is borrowed: the sentence does not support the box.
- A box word whose opposite the text has instead also covers negating prefixes ("active"/"inactive",
  "AMPK-dependent"/"AMPK-independent", "sensitization"/"desensitization") and hyper-/hypo-.
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
RULES_VERSION = 6                                  # part of the diagram cache key: a rules change re-validates cached declines

# Order-sensitive verbs (E2): the source's words must appear before the target's in the cited sentence.
ORDER_VERBS = ("causes", "leads to", "passes to", "branches to")

# verb -> stems of the verb and its accepted synonyms (E2). A stem matches the start of any sentence word.
SYNONYMS: dict[str, tuple[str, ...]] = {
    "includes": ("includ", "such as", "consist", "compris", "divided into", "classif", "types", "e.g", "categor"),
    "subtype of": ("type", "subtype", "class", "variant", "form", "kind", "categor", "group"),
    "is a": (" is a", " are ", "type", "form of", "class", "kind of", "example"),
    "passes to": ("pass", "transmit", "convey", "run", "travel", "course", "continu", "extend", "project", "relay", "synaps", "proceed",
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
             "downregulat", "down-regulat", "diminish", "impair", "declin", "diminu", "attenuat")

NEGATION = frozenset({"not", "never", "no", "without", "unless", "neither", "nor", "cannot", "none"})
WARNING_CUES = ("never", "contraindicated", "avoid", "must not", "warning", "do not", "should not", "danger")
# "Y is a consequence of X", "Y because X": the words between the two boxes reverse the causal direction (E2 order).
BACKWARD = ("consequence of", "result of", "results from", "resulting from", "due to", "caused by", "secondary to",
            "because", "owing to", "induced by", "mediated by", "driven by", "stems from", "arises from", "based on",
            "depends on", "dependent on", "attributed to", "explained by", "follows from", "produced by",
            "brought about by", "triggered by", "results of")
# "A vs B", "unlike B", "whereas B": from the contrast word to the end of its ";"-clause the answer is setting B APART
# from what came before, so an arrow from one side of that boundary to the other is never stated (and is contradicted).
CONTRAST = ("vs", "versus", "unlike", "whereas", "in contrast", "compared with", "compared to", "rather than",
            "instead of", "as opposed to", "contrary to")
# Direction of change, bound to the object it modifies ("increased cardiac output and reduced end-diastolic volume").
UP_STEMS = ("increas", "rais", "elevat", "enhanc", "promot", "upregulat", "up-regulat", "boost", "activat", "stimulat",
            "augment")
DOWN_STEMS = ("decreas", "reduc", "lower", "suppress", "diminish", "inhibit", "block", "deplet", "downregulat",
              "down-regulat", "impair", "attenuat", "slow", "retard", "declin", "diminu", "prevent")
# Whole words only (a stem would catch "risk", "fallopian", "mortality"): rise/fall verbs and the comparatives that say
# which way a quantity goes ("more complete emptying" is not "less complete emptying"). "two or more" is a count, not a
# direction (see _dir_at).
UP_WORDS = frozenset({"rise", "rises", "rising", "rose", "risen", "more", "greater", "higher", "larger"})
DOWN_WORDS = frozenset({"fall", "falls", "falling", "fell", "fallen", "drop", "drops", "dropped", "dropping", "less",
                        "fewer", "lesser", "smaller", "lose", "loses", "losing", "lost", "loss"})
DIR_WINDOW = 3                                     # a direction word modifies an object at most 3 tokens away
LIST_WINDOW = 8                                    # ... or the head of a list it governs ("decreasing A, B and possibly C")
NEAR = 6                                           # a box's own direction word this close to its object grounds it
_COORD = frozenset({"and", "or", "but", "which", "while", "whereas", "nor"})
# A directional arrow between two boxes in one clause needs one of these BETWEEN them (plus the kind's verb synonyms):
# boxes separated only by commas, "and", "or" or a parenthesis are items of one list, not a step or a branch.
LINK_WORDS = frozenset({"then", "next", "thereby", "thus", "hence", "therefore", "consequently", "which", "that", "via", "into",
                        "so", "subsequently", "thereafter", "eventually", "finally"})
LINK_STEMS = ("lead", "result", "caus", "ensu", "initiat", "trigger", "follow", "produc", "induc", "progress", "affect", "allow",
              "enabl", "permit", "bind", "act", "form", "transmit", "convey", "carr")
# A list lead that says WHERE ("After the posterior auricular nerve:", "Within the parotid gland:") is not the source
# of the items under it.
LOCATORS = frozenset({"after", "within", "at", "beyond", "before", "inside", "near", "below", "above", "behind",
                      "beneath", "distal", "proximal"})
# A later sentence that opens with one of these continues the previous step ("This causes ...", "Then it binds ...").
STEP_OPENERS = frozenset({"then", "next", "subsequently", "thereafter", "thereby", "thus", "hence", "therefore",
                          "consequently", "finally", "this", "these", "which", "so", "eventually", "later"})
STEP_OPENER_STEMS = ("lead", "result", "caus", "ensu", "trigger", "follow", "produc", "induc", "progress")
_SUBJECT_OPENERS = frozenset({"this", "these", "which", "it", "that", "they"})
_PASSIVE_AUX = frozenset({"is", "are", "was", "were", "be", "been", "being"})

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


_TOK = re.compile(r"[a-z0-9][a-z0-9'\-]*")


def _tok_text(text: str) -> str:
    # an arrow in the answer ("distorts codon recognition → misreading") is the answer's own "then"
    return re.sub(r"→|⟶|->", " then ", (text or "").lower())


def tokens(text: str) -> list[str]:
    return _TOK.findall(_tok_text(text))


def content_words(text: str) -> set[str]:
    return {_stem(t) for t in tokens(text) if t not in STOP and not t.isdigit() and len(t) > 1}


def numbers_in(text: str) -> list[str]:
    return re.findall(r"\d+(?:\.\d+)?", text or "")


_NUM_WORDS = {w: str(i) for i, ws in enumerate((
    (), ("one", "first", "single"), ("two", "second", "both", "twice", "double"), ("three", "third", "thrice"),
    ("four", "fourth"), ("five", "fifth"), ("six", "sixth"), ("seven", "seventh"), ("eight", "eighth"),
    ("nine", "ninth"), ("ten", "tenth"), ("eleven", "eleventh"), ("twelve", "twelfth")), 0) for w in ws}
_NUM_WORDS.pop("both", None)
_NUM_WORDS.pop("single", None)
_GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "κ": "kappa", "μ": "mu", "ε": "epsilon",
          "θ": "theta", "σ": "sigma", "ω": "omega"}
_GREEK_WORD = re.compile(r"(?<![a-z])(alpha|beta|gamma|delta|kappa|epsilon|theta|sigma|omega)(?![a-z])")


def exact_marks(text: str) -> set[str]:
    """What a box may only show when its supporting sentence shows it too: numbers (digits or spelled: "Five", "third-
    generation", "two-thirds") and Greek letters ("β cells" is not "α cells"; "beta" and "β" are the same mark)."""
    low = (text or "").lower()
    out = set(numbers_in(low))
    for part in re.findall(r"[a-z]+", low):
        if part in _NUM_WORDS:
            out.add(_NUM_WORDS[part])
    out |= {f"g:{name}" for ch, name in _GREEK.items() if ch in low}
    out |= {f"g:{m}" for m in _GREEK_WORD.findall(low)}
    return out


def _tok_marks(t: str) -> set[str]:
    """Number marks of one token: digits ("30s" -> 30) and spelled numbers ("two-thirds" -> 2)."""
    out = set(numbers_in(t))
    out |= {_NUM_WORDS[x] for x in re.findall(r"[a-z]+", t) if x in _NUM_WORDS}
    return out


def _num_neighbours(toks: list[str], i: int) -> set[str]:
    """The nearest content word on each side of the number toks[i], not across another number ("stage 1 one islet":
    "one" has only "islet")."""
    out = set()
    for rng in (range(i - 1, -1, -1), range(i + 1, len(toks))):
        for k in rng:
            if _tok_marks(toks[k]):
                break
            if toks[k] not in STOP and len(toks[k]) > 1:
                out.add(_stem(toks[k]))
                break
    return out


def numbers_bound(label: str, text: str) -> bool:
    """Every number of a box stands in the text where the box's own words are:
    - next to the same word as in the box ("stage 1" and "stage 3" in the sentence do not license "one islet
      autoantibody" or "Three or more ... autoantibodies" where the text says "two or more islet cell autoantibodies");
    - in a comma/semicolon part of the sentence that also holds another word of the box ("stage 1 is defined by two or
      more islet cell autoantibodies with normoglycemia, stage 2 by continued autoimmunity ..." does not license "Stage 2
      = islet autoantibodies with normoglycemia");
    - several numbers in the box's order ("Stage 2: two or more ..." is not "stage 1 ... two or more ..., stage 2");
    - a digit where the text writes that digit, a spelled number where it spells it, when the text has that form.
    A number with no word beside it in the box is only checked by exact_marks."""
    lt = tokens(label)
    tt, seg = [], []
    for n, part in enumerate(re.split(r"[,;:]", _tok_text(text))):
        found = _TOK.findall(part)
        tt += found
        seg += [n] * len(found)
    words = content_words(label)
    last = -1
    for i, t in enumerate(lt):
        marks, nb = _tok_marks(t), _num_neighbours(lt, i)
        if not marks or not nb:
            continue
        others = words - nb
        same = [k for k, x in enumerate(tt) if marks & _tok_marks(x)]
        # a digit is read where the text writes that digit, a spelled number where it spells it ("Stage 2" is not
        # licensed by "two" when the text has its own "stage 2")
        form = [k for k in same if bool(re.search(r"\d", tt[k])) == bool(re.search(r"\d", t))]
        ok = [k for k in (form or same) if nb & _num_neighbours(tt, k)
              and (not others or any(_stem(tt[j]) in others for j in range(len(tt)) if seg[j] == seg[k]))]
        later = [k for k in ok if k > last]
        if not later:
            return False
        last = later[0]
    return True


# Words whose opposite in the text means the box says the opposite of the answer (V4 and arrow units): a box word that
# is not in the text, while its opposite is, is a reworded claim ("posterior two-thirds" for "anterior two-thirds").
_ANTONYM_PAIRS = (("anterior", "posterior"), ("superior", "inferior"), ("upper", "lower"), ("strong", "weak"),
                  ("strong", "mild"), ("major", "minor"), ("medial", "lateral"), ("proximal", "distal"),
                  ("left", "right"), ("afferent", "efferent"), ("internal", "external"), ("deep", "superficial"),
                  ("acute", "chronic"), ("direct", "indirect"), ("positive", "negative"), ("present", "absent"),
                  ("agonist", "antagonist"), ("excitatory", "inhibitory"), ("sympathetic", "parasympathetic"),
                  ("preganglionic", "postganglionic"), ("presynaptic", "postsynaptic"), ("ascending", "descending"),
                  ("selective", "nonselective"), ("selective", "non-selective"), ("cardioselective", "nonselective"),
                  ("retained", "lost"), ("retained", "loss"), ("preserved", "lost"), ("preserved", "loss"),
                  ("maintained", "lost"), ("proven", "unproven"), ("effective", "ineffective"), ("high", "low"),
                  ("early", "late"), ("reversible", "irreversible"), ("hyperglycemia", "hypoglycemia"),
                  ("hyperglycaemia", "hypoglycaemia"), ("hyperkalemia", "hypokalemia"), ("mild", "marked"),
                  ("mild", "severe"), ("mild", "potent"), ("weak", "potent"), ("short", "long"), ("childhood", "adulthood"),
                  ("rapid", "slow"), ("fast", "slow"), ("presence", "absence"), ("excess", "deficiency"))
# A box word that is the text's word with a negating prefix added or removed ("active" / "inactive", "dependent" /
# "independent", "sensitization" / "desensitization") or hyper-/hypo- swapped says the opposite of the text.
_NEG_PREFIXES = ("in", "un", "non", "non-", "de", "dis", "ir", "im", "il", "a")
ANTONYMS: dict[str, set[str]] = {}
for _a, _b in _ANTONYM_PAIRS:
    ANTONYMS.setdefault(_stem(_a), set()).add(_stem(_b))
    ANTONYMS.setdefault(_stem(_b), set()).add(_stem(_a))


def _opposed(label: str, words: set[str]) -> bool:
    """A box word missing from `words` whose opposite IS in `words`."""
    lw = content_words(label)
    return any((ANTONYMS.get(w, set()) | _prefix_opposites(w)) & words for w in lw - words)


def _prefix_opposites(w: str) -> set[str]:
    if "-" in w:                                    # "AMPK-dependent" / "AMPK-independent"
        head, tail = w.rsplit("-", 1)
        return {f"{head}-{x}" for x in _prefix_opposites(tail)} if tail else set()
    out = {p + w for p in _NEG_PREFIXES}
    out |= {w[len(p):] for p in _NEG_PREFIXES if w.startswith(p) and len(w) - len(p) >= 4}
    for a, b in (("hyper", "hypo"), ("hypo", "hyper")):
        if w.startswith(a):
            out.add(b + w[len(a):])
    return out


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


def _dir(tok: str) -> int:
    if tok in UP_WORDS:
        return 1
    if tok in DOWN_WORDS:
        return -1
    if any(tok.startswith(st) for st in UP_STEMS):
        return 1
    if any(tok.startswith(st) for st in DOWN_STEMS):
        return -1
    return 0


def _dir_at(toks: list[str], k: int) -> int:
    """_dir of toks[k] in its place: "or more" / "or less" ("two or more autoantibodies") is a count, not a direction."""
    if toks[k] in UP_WORDS | DOWN_WORDS and k and toks[k - 1] in ("or", "no", "any"):
        return 0
    return _dir(toks[k])


def _polarity_at(toks: list[str], pos: int, ext: bool = False) -> int:
    """The direction word that modifies toks[pos]: the nearest one before it (within DIR_WINDOW, not across a
    coordinator: "shortened and diastole"), else after it. With `ext`, when neither is found, the head of a list the
    object is an item of ("decreasing serum norepinephrine, plasma renin and possibly aldosterone": up to LIST_WINDOW
    tokens back, across "and"/"or" only) or a predicate further on ("velocity of tension development increases")."""
    for d in range(1, DIR_WINDOW + 1):
        if pos - d < 0 or toks[pos - d] in _COORD:
            break
        if _dir_at(toks, pos - d):
            return _dir_at(toks, pos - d)
    for d in range(1, DIR_WINDOW + 1):          # after the object: never across a coordinator ("flux ... and activates")
        if pos + d >= len(toks) or toks[pos + d] in _COORD:
            break
        if _dir_at(toks, pos + d):
            return _dir_at(toks, pos + d)
    if not ext:
        return 0
    for d in range(1, LIST_WINDOW + 1):
        if pos - d < 0 or toks[pos - d] in _COORD - {"and", "or"} or toks[pos - d] in NEGATION:
            break
        if _dir_at(toks, pos - d):
            return _dir_at(toks, pos - d)
    for d in range(1, LIST_WINDOW - 2):
        if pos + d >= len(toks) or toks[pos + d] in _COORD:
            break
        if _dir_at(toks, pos + d):
            return _dir_at(toks, pos + d)
    return 0


def _box_directions(label: str) -> list[tuple[int, str]]:
    """(direction, object stem) for each direction word of a box. The object is the next content word ("Raised
    aldosterone levels" -> aldosterone); for a predicate ("Heart rate is decreased", "Velocity ... increases") or a word
    with nothing after it, the content word before it. A direction word followed by another one does not govern
    ("Cell-wall inhibitors enhance aminoglycoside entry": "enhance" governs "aminoglycoside")."""
    lt = tokens(label)
    out = []
    for i in range(len(lt)):
        p = _dir_at(lt, i)
        if not p:
            continue
        after = [w for w in lt[i + 1:] if w not in STOP and not w.isdigit()]
        before = [w for w in lt[:i] if w not in STOP and not w.isdigit() and not _dir(w)]
        if after and _dir(after[0]):
            continue
        # "Heart rate is decreased", "cardiac output rises": the object comes first. A trailing participle
        # ("..., increasing…") governs what follows it, which the box left out.
        # (only a verb form says that: "... cell wall inhibitors" names an agent, it does not lower "wall")
        verb = lt[i] in ("lost", "fell", "rose", "rise", "fall", "drop") or (
            lt[i].endswith(("ed", "es", "s", "en")) and not lt[i].endswith(("ors", "ions", "ers", "ss", "ents")))
        predicate = i and lt[i - 1] in _PASSIVE_AUX or (not after and verb)
        obj = before[-1] if predicate and before else after[0] if after else None
        if obj:
            out.append((p, _stem(obj)))
    return out


def _direction_contradicted(label: str, toks: list[str], *more: list[str]) -> bool:
    """A box that says which way something changes ("Increased end-diastolic volume", "Less complete emptying") must be
    told so by the text: the text puts that direction on the same object somewhere. It is contradicted when the text
    puts only the opposite word on it ("reduced end-diastolic volume", "more complete emptying"), and unsupported when
    the text names the object with no direction, or another one ("decreasing ... possibly aldosterone levels" does not
    place "Raised aldosterone levels"), unless the box's own direction word stands near the object in the same clause
    ("Cardioselectivity is only relative and is lost at high doses"). A box whose object the text does not name is left
    to the word-support check.
    Each token list in `toks, *more` (a list lead, then each clause) is read on its own: a direction word never reaches
    across from a heading into its item ("Rate slowing: Vagal tone is increased")."""
    segs = (toks,) + more
    words = {_stem(t) for t in tokens(label) if _dir(t)}       # the box's own direction words, as the text may say them
    for p, obj in _box_directions(label):
        occ = [(t, k) for t in segs for k, w in enumerate(t) if _stem(w) == obj]
        if not occ:
            continue
        seen = {_polarity_at(t, k) for t, k in occ}
        if -p in seen and p not in seen:
            return True
        if p not in seen and p not in {_polarity_at(t, k, ext=True) for t, k in occ} \
                and not any(_stem(x) in words for t, k in occ for x in t[max(0, k - NEAR):k + NEAR + 1]):
            return True
    return False


def _neg_count(toks) -> int:
    return sum(t in NEGATION for t in toks)


_NEG_SCOPE_END = re.compile(r"[,;:.()\[\]—–]")
_NEG_ADVERBS = frozenset({"longer", "fully", "always", "necessarily", "yet", "directly", "significantly", "usually",
                          "completely", "entirely", "clearly", "well", "been", "be"})


def _negated_heads(text: str) -> tuple[set[str], set[str]]:
    """(stems the text only says right after a negation, stems it says elsewhere). The head of a negation is the first
    content word after it, within its clause ("(not reversed by atropine)" -> reversed, "can no longer be sustained" ->
    sustained, "does not raise blood volume" -> raise; "blood volume" itself is not negated; "does not stimulate β cells
    or cause insulin release" -> stimulate, cause)."""
    heads, other = set(), set()
    for seg in _NEG_SCOPE_END.split(_tok_text(text)):
        want = scope = False                  # scope: inside a negated phrase, where "or"/"nor" negates the next verb too
        for t in _TOK.findall(seg):
            if t in NEGATION or t.endswith("n't"):
                want = scope = True
                continue
            if t in ("or", "nor") and scope:
                want = True
                continue
            if t in _COORD:
                want = scope = False
            if t in STOP or t in _NEG_ADVERBS or t.isdigit():
                continue
            (heads if want else other).add(_stem(t))
            want = False
    return heads, other


def _negation_dropped(label: str, s: "Sent") -> bool:
    """A box with no negation of its own that holds a word the sentence only ever says as the head of a negation: "an
    extravagal depressant action (not reversed by atropine)" does not place "... action reversed by atropine"."""
    if set(tokens(label)) & NEGATION or "n't" in label.lower():
        return False
    heads, other = _negated_heads(f"{s.ctx}. {strip_markers(s.text)}")
    return bool(content_words(label) & (heads - other))


def _negations_kept(label: str, toks: list[str]) -> bool:
    """A negation in a box ("Without intrinsic sympathomimetic activity", "Does not stimulate β cells") is part of what
    it claims: the text that places the box must carry the same negation word."""
    return set(tokens(label)) & NEGATION <= set(toks)


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
_CLAUSE = re.compile(r";|,\s+(?=(?:while|whereas|but)\b)")         # independent clauses of one sentence
# "**Rate slowing:** ...", "**X**: ...", "**Penicillins (β-lactams)** — inhibit ...": a bold lead that heads its bullet
_INLINE_HEAD = re.compile(r"^\*\*([^*\n]{1,80}?(?::\*\*|\*\*\s*(?::|—|–|-\s)))\s*")
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
    skip: int = 0             # leading ctx tokens from a lead-in clause that does not introduce the list (see _intro)


def _sent(text: str, ctx: str, block: int, numbered: bool, skip: int = 0) -> Sent:
    full = f"{ctx} {strip_markers(text)}".strip()
    return Sent(text, ctx, block, numbered, markers_in(text), content_words(full), tokens(full),
                content_words(strip_markers(text)), skip)


def _intro_skip(lead: str) -> int:
    """How many leading tokens of a lead-in come before the clause that introduces its list: "Metformin's mechanism is
    not fully defined, but the key features are:" introduces the list with "the key features are"; the first clause's
    "not" is about something else, so E3 does not read it for the items' arrows (the words stay context). A one-clause
    lead keeps everything, its negation included ("does not give off the following branches:")."""
    parts = [c for c in _CLAUSE.split(lead) if c.strip()]
    return len(tokens(lead)) - len(tokens(parts[-1])) if len(parts) > 1 else 0


def parse_answer(answer_text: str) -> list[Sent]:
    """Answer sentences with their list context (see module docstring). A segment that is only markers joins the
    sentence before it. The context is the answer's own words, in the answer's own order; nothing is added."""
    lines = (answer_text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[Sent] = []
    lead = lead_marks = head = ""
    sub: tuple[int, str, str] | None = None          # (indent, text, markers) of a parent bullet ending in ":"
    block = 0

    def emit(body: str, ctx: str, inherit: str, numbered: bool, skip: int = 0) -> None:
        for part in _SPLIT.split(body):
            part = re.sub(r"^\s*(?:[*\-•>#]+|\d+[.)])\s+", "", part.strip())
            if not part:
                continue
            if out and not strip_markers(part).strip(" .,;:*-"):
                out[-1] = _sent(out[-1].text + " " + part, out[-1].ctx, out[-1].block, out[-1].numbered, out[-1].skip)
                continue
            out.append(_sent(f"{part} {inherit}".strip(), ctx, block, numbered, skip))

    for line in lines:
        if not line.strip():
            continue
        block += 1
        m = _ITEM.match(line)
        if m:
            indent, body = len(m.group(1).expandtabs(4)), line[m.end():].strip()
            if sub and indent <= sub[0]:
                sub = None
            # "- **Rate slowing:** Heart rate is decreased [1]. Vagal tone is increased reflexly ... [1]": the bold lead
            # heads every sentence of its bullet, not only the first (whose own text keeps it too).
            il = _INLINE_HEAD.match(body)
            ctx = " ".join(x for x in (lead, head, sub[1] if sub else "", il.group(1).strip(" :*") if il else "") if x)
            inherit = "" if markers_in(body) else (sub[2] if sub and sub[2] else lead_marks)
            emit(body, ctx, inherit, bool(_NUMBERED.match(line)), _intro_skip(lead) if lead else 0)
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


def _negated(low: str, toks: list[str], own: list[str]) -> bool:
    """E3: a negation in the evidence unit that the boxes and the arrow do not carry themselves. Counted, not
    set-tested: "does not stimulate β cells and does not cause insulin release" has two, and a box carrying one
    ("Does not stimulate β cells") does not excuse the other ("Insulin release")."""
    return _neg_count(toks) + low.count("n't") > _neg_count(own)


def _target_polarity(tgt_label: str, u: Unit) -> int:
    """The direction word the unit puts on the target's object ("lowering intracellular ATP" -> -1)."""
    words = {_stem(t) for t in tokens(tgt_label) if t not in STOP and not _dir(t)}
    pols = {_polarity_at(u.toks, k) for k, w in enumerate(u.toks) if _stem(w) in words} - {0}
    return pols.pop() if len(pols) == 1 else 0


def _antonym(label: str, low: str, toks: list[str], tgt_label: str = "", u: Unit | None = None) -> bool:
    """The arrow's direction verb against the unit. When the unit puts one direction word on the target itself, that
    word decides ("lowering ATP and raising AMP": "increases" onto ATP is an antonym though "raising" is in the unit)."""
    want = 1 if label in POS_VERBS else -1 if label in NEG_VERBS else 0
    if want and u is not None and tgt_label:
        got = _target_polarity(tgt_label, u)
        if got:
            return got != want
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
    cuts: tuple = ()          # token index where each ";"-clause of the unit ends
    skip: int = 0             # leading context tokens E3 does not read (a lead-in clause that does not introduce the list)


def _sup(label: str, u: Unit) -> float:
    """A box is supported by the sentence's own words OR by its list context (a box that IS the heading or lead-in),
    never by a blend: context words never top up an item's box."""
    return max(support(label, u.own), support(label, u.ctx))


def _in_unit(label: str, u: Unit, strict: bool = False) -> bool:
    """E1 for one box: own words or list context, never a blend. `strict` (classification arrows, whose only evidence
    is that both boxes sit in one unit; directional arrows must also be found in order) applies the V4 standard, so a
    two-word box is not placed by one generic word ("effects", "nerve")."""
    if not _negations_kept(label, u.toks):
        return False
    lw = content_words(label)
    if not lw:
        return False
    if (node_supported(label, u.ctx) if strict else support(label, u.ctx) >= SUPPORT_MIN):
        return True
    w = _window(lw, label, u.toks, u.n_ctx, len(u.toks))
    need = 1.0 if strict and len(lw) <= 2 else SUPPORT_MIN
    return w is not None and w[2] / len(lw) >= need


def _cited_part(text: str, cites: set | None) -> str:
    """The part of a sentence that the given markers cite. "X is shown at the inferior orbital fissure [3], and Y may
    pass through the superior orbital fissure [4]" is two cited claims: [3] cites only the first. Text after the last
    marker belongs to that marker's part. With no `cites`, or when no part matches, the whole sentence."""
    groups = list(re.finditer(r"(?:\s*\[\s*G?\d+(?:\s*,\s*G?\d+)*\s*\])+", text, re.I))
    cuts = [m.end() for m in groups if re.search(r"[A-Za-z]", text[m.end():])]
    if not cites or not cuts:
        return strip_markers(text)
    parts, last = [], 0
    for c in cuts + [len(text)]:
        parts.append(text[last:c])
        last = c
    keep = [p for p in parts if markers_in(p) & cites]
    return strip_markers(" ".join(keep)) if keep else strip_markers(text)


def _units(s: Sent, labels: list[str], strict: bool = False, cites: set | None = None) -> list[Unit]:
    """Evidence units of one cited sentence for these boxes: each ";"-clause (read after the item's list context) in
    which every label reaches SUPPORT_MIN; when no single clause holds them all, the whole sentence. Only the part of
    the sentence that `cites` cite is read (see _cited_part). A unit is always a piece of the answer's own text, so it
    can only lose words, never gain any."""
    body = _cited_part(s.text, cites)
    ctx_w, n_ctx = content_words(s.ctx), len(tokens(s.ctx))
    clauses = [c for c in _CLAUSE.split(body) if c.strip()]
    out = []
    if len(clauses) > 1:
        # a clause is a box's unit only where the box is best supported: "Stage 2 = continued autoimmunity" is not
        # placed in "... initiating autoimmunity: Stage 1 = ..." by two generic words when its own clause names it
        best = {lb: max(support(lb, content_words(c)) for c in clauses) for lb in labels}
        for c in clauses:
            ut = tokens(f"{s.ctx} {c}")
            u = Unit(f"{s.ctx} {c}".strip().lower(), ut, content_words(c), ctx_w, n_ctx, (len(ut),), s.skip)
            if all(_in_unit(lb, u, strict) and (support(lb, u.ctx) >= SUPPORT_MIN or support(lb, u.own) >= best[lb])
                   for lb in labels):
                out.append(u)
    if not out:
        cuts, n = [], n_ctx
        for c in clauses or [body]:
            n += len(tokens(c))
            cuts.append(n)
        out.append(Unit(f"{s.ctx} {body}".strip().lower(), tokens(f"{s.ctx} {body}".strip()), content_words(body), ctx_w,
                        n_ctx, tuple(cuts), s.skip))
    return out


def _window(words: set[str], label: str, toks: list[str], lo: int, hi: int) -> tuple[int, int, int] | None:
    """Where a box sits as a PHRASE in toks[lo:hi]: the tightest span of at most len(label)+2 tokens holding the most
    of `words` (earliest on a tie). (start, end inclusive, words matched). A span with (or right after) the opposite of
    a box word is not the box ("inferior ophthalmic vein" is not "Superior ophthalmic vein"), and words scattered over
    the sentence never make up a box."""
    lw = content_words(label)
    opp = set().union(*(ANTONYMS.get(w, set()) for w in lw)) - lw
    cap = len(tokens(label)) + 2
    stems = [_stem(t) for t in toks]
    best = None
    for i in range(lo, hi):
        if stems[i] not in words:
            continue
        seen: set = set()
        for j in range(i, min(hi, i + cap)):
            if stems[j] not in words:
                continue
            seen.add(stems[j])
            key = (len(seen), -(j - i), -i)
            if (best is None or key > best[0]) and not (opp & set(stems[max(lo, i - 1):j + 1])):
                best = (key, i, j)
    return None if best is None else (best[1], best[2], best[0][0])


def _spans(src_label: str, tgt_label: str, u: Unit) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
    """Where each box sits in the unit, as a phrase (start, end). A box placed by its list context (the heading or
    lead-in) sits in the context, before the item's own words. Words both boxes share do not place either."""
    sw, tw = content_words(src_label), content_words(tgt_label)
    s_only, t_only = (sw - tw) or sw, (tw - sw) or tw

    def span(label: str, words: set[str]) -> tuple[int, int] | None:
        lw = content_words(label)
        full = _window(lw, label, u.toks, u.n_ctx, len(u.toks))
        # a box that IS the item's heading or lead-in sits there, ahead of the item's words, even when the bullet's
        # own text repeats its bold lead ("- **Hepatic gluconeogenesis suppression** — ...; it reduces ...")
        if full and full[2] / len(lw) >= SUPPORT_MIN and support(label, u.ctx) < full[2] / len(lw):
            lo, hi = full[0], full[1]
            hits = [k for k in range(lo, hi + 1) if _stem(u.toks[k]) in words]
            return (hits[0], hits[-1]) if hits else None        # placed only by words the other box shares: not placed
        w = _window(words, label, u.toks, 0, u.n_ctx)
        return (w[0], w[1]) if w else None

    return span(src_label, s_only), span(tgt_label, t_only)


def _positions(src_label: str, tgt_label: str, u: Unit) -> tuple[int | None, int | None]:
    sp, tp = _spans(src_label, tgt_label, u)
    return (sp[0] if sp else None), (tp[0] if tp else None)


def _paren_owner(u: Unit) -> list[int | None]:
    """For each token of the unit: the index of the token right before the "(" that encloses it, or None."""
    out, stack, last, idx = [], [], 0, 0
    text = _tok_text(u.low)
    for m in _TOK.finditer(text):
        for ch in text[last:m.start()]:
            if ch == "(":
                stack.append(idx - 1)
            elif ch == ")" and stack:
                stack.pop()
        out.append(stack[-1] if stack else None)
        idx, last = idx + 1, m.end()
    return out


def _asides(src_label: str, tgt_label: str, u: Unit) -> set[int]:
    """Token positions inside a bracket that neither box is in nor is the phrase right before ("Heart rate is decreased
    ..., partly by extravagal actions (direct depressant action on SA and A-V nodes, not reversed by atropine)"): the
    bracket qualifies its own phrase, so its negation is not about this arrow (E3 reads it only for arrows that touch it)."""
    sp, tp = _spans(src_label, tgt_label, u)
    if sp is None or tp is None:
        return set()
    owner = _paren_owner(u)
    boxes = set(range(sp[0], sp[1] + 1)) | set(range(tp[0], tp[1] + 1))
    touched = {owner[k] for k in boxes if k < len(owner) and owner[k] is not None} | (boxes & set(owner))
    return {k for k, o in enumerate(owner) if o is not None and o not in touched}


def _clause_of(p: int, u: Unit) -> int:
    return -1 if p < u.n_ctx else next((i for i, b in enumerate(u.cuts) if p < b), len(u.cuts))


def _numbered_pair(src_label: str, tgt_label: str) -> bool:
    """"Stage 1 ..." -> "Stage 2 ...": both boxes carry the same numbered word, the target's number the next one."""
    def tag(label: str) -> tuple[str, int] | None:
        t = tokens(label)
        hits = [(t[i], int(t[i + 1])) for i in range(len(t) - 1) if t[i].isalpha() and t[i + 1].isdigit()]
        return hits[0] if hits else None
    a, b = tag(src_label), tag(tgt_label)
    return bool(a and b and a[0] == b[0] and b[1] == a[1] + 1)


def _arrow_shape_ok(label: str, src_label: str, tgt_label: str, u: Unit, kind: str) -> bool:
    """What the answer's phrasing says about two boxes found in one unit (both in the item's own words):
    - directional: a linking word sits BETWEEN them (the verb's synonym, "which", "into", "then", a step or direction
      verb); items of one list ("A, B and C", "leading to A, B and C") are siblings, not a chain;
    - directional: the source is not a place the list lead names ("After the posterior auricular nerve:");
    - classification: a child in brackets belongs to the phrase right before its bracket ("vasodilatory properties
      (nebivolol) or combined α-blockade (carvedilol)")."""
    sp, tp = _spans(src_label, tgt_label, u)
    if sp is None or tp is None:
        return True
    if _directional(label, kind):
        if any(t in LOCATORS for t in u.toks[max(0, sp[0] - 2):sp[0]]):
            return False
        if sp[0] >= u.n_ctx and tp[0] >= u.n_ctx and sp[1] < tp[0] and _clause_of(sp[1], u) == _clause_of(tp[0], u):
            # (across ";"-clauses _clauses_linked decides: the later clause must point back)
            between = u.toks[sp[1] + 1:tp[0]]
            stems = tuple(x for v in KINDS[kind][1] for x in SYNONYMS.get(v, ()) if " " not in x) + LINK_STEMS \
                + UP_STEMS + DOWN_STEMS
            linked = any(t in LINK_WORDS or t.startswith(stems) for t in between)
            # "interferes with the respiratory chain, lowering ATP": a participle opening the target right after the
            # source states the consequence; after "and"/"or" it is one more item of a list ("..., and reducing ATP")
            head = u.toks[tp[0]]
            linked = linked or (head.endswith("ing") and head.startswith(stems) and not (set(between) & _COORD))
            # "secondary changes in membrane integrity (leakage of ions ...)": the bracket spells out the source itself
            owner = _paren_owner(u)
            linked = linked or (tp[0] < len(owner) and owner[tp[0]] == sp[1])
            linked = linked or _numbered_pair(src_label, tgt_label)
            # "A proposed sequence includes A, B, C and D": the clause itself announces its items as ordered steps
            lo = max([u.n_ctx] + [c for c in u.cuts if c <= sp[0]])
            linked = linked or any(x.startswith(_SEQ_LEAD) for t in u.toks[lo:sp[0]] for x in t.split("-"))
            if not linked:
                return False
    elif kind == "classification" and sp[0] >= u.n_ctx and tp[0] >= u.n_ctx:
        owner = _paren_owner(u)
        o = owner[tp[0]] if tp[0] < len(owner) else None
        # the bracket that holds the child belongs to the phrase that ends right before it, not to this parent
        if o is not None and not (sp[0] <= o <= sp[1] or owner[sp[0]] == o):
            return False
    return True


def _clauses_linked(src_label: str, tgt_label: str, u: Unit) -> bool:
    """Two boxes in different independent clauses of one sentence are linked only when the later clause opens by pointing
    back ("...; this augments ...", "...; which ...", "...; thus ..."). "Freeze initiation ...; binding at the 30S-50S
    juncture distorts ..." lists two parallel facts: no order or cause between them is stated."""
    ps, pt = _positions(src_label, tgt_label, u)
    if ps is None or pt is None or len(u.cuts) < 2:
        return True
    starts = (u.n_ctx,) + u.cuts[:-1]

    def clause(p: int) -> int:
        return 0 if p < u.n_ctx else next(i for i, b in enumerate(u.cuts) if p < b)
    cs, ct = clause(ps), clause(pt)
    if cs == ct or min(ps, pt) < u.n_ctx:          # same clause, or one box is the list context heading the sentence
        return True
    later = starts[max(cs, ct)]
    def numbered(c: int, p: int) -> tuple[str, int] | None:     # last "<word> <n>" in the box's clause, up to the box
        hits = [(u.toks[i], int(u.toks[i + 1])) for i in range(starts[c], p)
                if u.toks[i + 1].isdigit() and u.toks[i].isalpha()]
        return hits[-1] if hits else None
    ns, nt = numbered(cs, ps), numbered(ct, pt)
    if ns and nt and ns[0] == nt[0] and ns[1] < nt[1]:   # "Stage 1 = ...; Stage 2 = ...": the answer numbers the steps
        return True
    return _opens_step(u.toks[later:later + 4], u.toks[later:], clause_level=True)


def _contrasted(src_label: str, tgt_label: str, u: Unit) -> bool:
    """The two boxes sit on opposite sides of a contrast ("A vs B", "..., unlike B"; see CONTRAST)."""
    ps, pt = _positions(src_label, tgt_label, u)
    if ps is None or pt is None:
        return False
    for i in range(len(u.toks)):
        for c in CONTRAST:
            cw = c.split()
            if u.toks[i:i + len(cw)] == cw:
                end = next((b for b in u.cuts if b > i), len(u.toks))
                if (i <= ps < end) != (i <= pt < end):
                    return True
    return False


def _order(src_label: str, tgt_label: str, u: Unit) -> str:
    """E2 order inside one evidence unit: 'forward', 'reversed' or 'unknown'. Words order the boxes, except that a
    backward connective between them ("Y is a consequence of X", "Y because X") states the opposite direction."""
    ps, pt = _positions(src_label, tgt_label, u)
    if ps is None or pt is None or ps == pt:
        return "unknown"
    lo, hi = min(ps, pt), max(ps, pt)
    between = f" {' '.join(u.toks[lo + 1:hi])} "
    forward = ps < pt
    # a connective a box states itself ("Cidal action is attributed to membrane changes") is part of that box's claim,
    # not the direction between the two boxes
    boxes = f" {' '.join(tokens(src_label))} | {' '.join(tokens(tgt_label))} "
    if any(f" {c} " in between and f" {c} " not in boxes for c in BACKWARD):
        forward = not forward
    return "forward" if forward else "reversed"


def _directional(label: str, kind: str) -> bool:
    return label in ORDER_VERBS or kind in DIRECTIONAL_KINDS


def _edge_ok(e: dict, src: dict, tgt: dict, carriers: list[Sent], kind: str, cites: set | None = None) -> tuple[bool, str]:
    """E1-E3 on the evidence units of the sentences that carry the edge's cites. Returns (keep, label to show)."""
    label = e["label"]
    own = tokens(src["label"]) + tokens(tgt["label"]) + tokens(label)
    strict = kind == "classification"
    for s in carriers:
        for u in _units(s, [src["label"], tgt["label"]], strict, cites):
            low, toks = u.low, u.toks
            if not (_in_unit(src["label"], u, strict) and _in_unit(tgt["label"], u, strict)):               # E1
                continue
            if None in _spans(src["label"], tgt["label"], u):       # a box placed only by words the other box shares
                continue
            if _negated(low, [t for k, t in enumerate(toks)
                              if k >= u.skip and k not in _asides(src["label"], tgt["label"], u)], own):   # E3
                continue
            if _contrasted(src["label"], tgt["label"], u):                                                  # "A vs B"
                continue
            if _antonym(label, low, toks, tgt["label"], u):                                                 # E2 antonym
                continue
            want = 1 if label in POS_VERBS else -1 if label in NEG_VERBS else 0
            if want and _target_polarity(tgt["label"], u) != want:      # a direction arrow: the unit says it on the target
                continue
            show = label if label and _has_syn(label, low, toks) else ""                                    # E2 verb
            if _directional(label, kind) and _order(src["label"], tgt["label"], u) != "forward":                    # E2 order
                continue
            if not _clauses_linked(src["label"], tgt["label"], u):                                          # E2 clauses
                continue
            if not _arrow_shape_ok(label, src["label"], tgt["label"], u, kind):                             # list shape
                continue
            if show and _directional(label, kind):
                sp, tp = _spans(src["label"], tgt["label"], u)
                if sp and tp and sp[0] >= u.n_ctx and tp[0] >= u.n_ctx and sp[1] < tp[0]:
                    btw = u.toks[sp[1] + 1:tp[0]]               # the verb shown must be the answer's, between the boxes
                    show = label if _has_syn(label, " ".join(btw), btw) else ""
            return True, show
    return False, ""


def _contradicted(label: str, src: dict, tgt: dict, carriers: list[Sent], kind: str) -> bool:
    """True when a cited unit that holds BOTH boxes says something the arrow would contradict: a negation the boxes
    don't carry (E3), the opposite direction verb (antonym), or, for a directional arrow, the target before the source
    (reversed order, backward connectives included). 'Order could not be confirmed' is not a contradiction."""
    own = tokens(src["label"]) + tokens(tgt["label"]) + tokens(label)
    for s in carriers:
        for u in _units(s, [src["label"], tgt["label"]]):
            low, toks = u.low, u.toks
            if _sup(src["label"], u) < SUPPORT_MIN or _sup(tgt["label"], u) < SUPPORT_MIN:
                continue
            if _negated(low, toks, own) or _antonym(label, low, toks, tgt["label"], u):
                return True
            if _contrasted(src["label"], tgt["label"], u):
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
    full = tokens(strip_markers(s.text))
    return _opens_step(full[:4], full)


def _opens_step(head: list[str], full: list[str], clause_level: bool = False) -> bool:
    """`head` (the first words of a sentence or clause) says it continues from what came before. Across sentences a
    bare "This"/"Which"/"So" is too weak; inside one sentence, after ";", it refers back to the clause before."""
    if not head:
        return False
    bare = STEP_OPENERS if clause_level else STEP_OPENERS - {"this", "these", "which", "so"}
    if head[0] in bare or "then" in head:
        return True
    if clause_level and any(t in ("this", "these", "such", "thereby") for t in head[:3]):    # "; blocking this cross-link"
        return True
    # "Leading to ...", "This causes ...": a step verb opening the sentence or right after a pronoun subject. Not a
    # passive or backward form ("Islet destruction is caused by ..." states the cause of what came before).
    for i in (0, 1):
        if i == 1 and head[0] not in _SUBJECT_OPENERS:
            break
        if i < len(head) and any(head[i].startswith(st) for st in STEP_OPENER_STEMS):
            return not ((i and head[i - 1] in _PASSIVE_AUX) or "by" in full[i + 1:i + 3])
    return False


def _adjacent_ok(e: dict, src: dict, tgt: dict, cites: set, sents: list[Sent]) -> bool:
    """E2 fallback for step-per-sentence answers: the source box is supported by cited sentence i and the target box by
    a later sentence j of the same section (at most MAX_STEP_GAP on) that the answer marks as the next step (see
    _continues), so the arrow only restates the order the answer gives. No verb, and not when the clause that supports
    either box carries a negation the boxes don't."""
    def ok_at(i: int, label: str) -> bool:
        s = sents[i]
        if not (s.mk & cites):
            return False
        return any(_in_unit(label, u) and not _negated(u.low, u.toks, tokens(label)) for u in _units(s, [label], cites=cites))

    def same_section(i: int, j: int) -> bool:          # a sentence with no marker (a heading) ends a section
        return all(sents[k].mk for k in range(i + 1, j))

    return any(ok_at(i, src["label"]) and ok_at(j, tgt["label"]) and same_section(i, j) and _continues(sents[j - 1], sents[j])
               and all(_continues(sents[k - 1], sents[k]) for k in range(i + 1, j))
               for i in range(len(sents)) for j in range(i + 1, min(i + 1 + MAX_STEP_GAP, len(sents))))


def _box_worded(label: str, s: Sent) -> bool:
    """V4 for one cited sentence. The box is the sentence's heading/lead-in, or is worded as ONE independent clause of
    the sentence says it: every box word the sentence has sits in that clause (a box never blends "X has proven benefit;
    Y has not shown benefit" into "Y has proven benefit"), the clause keeps the box's negations, no box word is the
    opposite of the text's ("posterior" for "anterior"), and no direction word is flipped."""
    clauses = [c for c in _CLAUSE.split(strip_markers(s.text)) if c.strip()]
    if not _negations_kept(label, s.toks) or _negation_dropped(label, s) \
            or _direction_contradicted(label, tokens(s.ctx), *(tokens(c) for c in clauses)):
        return False
    ctx_w = content_words(s.ctx)
    if node_supported(label, ctx_w) and not _opposed(label, ctx_w):
        return True
    if not node_supported(label, s.own) or _opposed(label, s.words):
        return False
    if len(clauses) < 2:
        return True
    matched = content_words(label) & s.own
    return any(matched <= content_words(c) | ctx_w and _negations_kept(label, tokens(f"{s.ctx} {c}"))
               for c in clauses)


def _borrowed(label: str, s: Sent, sents: list[Sent]) -> bool:
    """A box word its sentence does not have but another sentence of the answer does is borrowed from there: a blend of
    two places, not one sentence's claim ("Aminoglycosides inhibit cell wall synthesis" = the aminoglycoside sentence's
    "inhibit protein synthesis" + the penicillin section's "cell wall")."""
    missing = content_words(label) - s.words
    return bool(missing) and any(missing & t.words for t in sents if t is not s)


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
        # V4: ONE cited sentence supports the box, by its own words or by its heading/lead-in (never a blend of several
        # sentences), keeps the box's negation words, does not put the opposite direction on its object, and holds
        # every number the box shows.
        carry = _carriers(cites, sents)
        worded = [s for s in carry if _box_worded(label, s) and not _borrowed(label, s, sents)]
        if not worded:
            notes.append(f'box "{label}" is not worded as its cited sentence says it')
            continue
        worded = [s for s in worded if exact_marks(label) <= exact_marks(f"{s.ctx} {strip_markers(s.text)}")
                  and numbers_bound(label, f"{s.ctx} {strip_markers(s.text)}")]
        if not worded:
            notes.append(f'box "{label}" has a number or Greek letter its cited sentence does not')
            continue
        text = " ".join(f"{s.ctx} {strip_markers(s.text)}" for s in worded)
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
        ok, show = _edge_ok({**e, "label": label}, src, tgt, _carriers(cites, sents), kind, cites) if cites else (False, "")
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
