"""Clinical graph for the visualizer: a pure function from (complaints, candidate conditions, drill depth) to
nodes + edges, built only from certified ontology facts (no LLM).

Five levels, disclosed in order:
    1 Chief complaints      symptoms from the vignette (or the condition's MANIFESTS_AS objects)
    2 Differential          candidate conditions (+ their DIFFERENTIAL_OF neighbours)
    3 Clinical phases       HAS_CLINICAL_STAGE          } shown for one condition once the user drills in;
    4 Workup / triage       CONFIRMED_BY                } each click on a condition opens the next level
    5 Therapeutics          TREATED_BY + CONTRAINDICATES}

Every edge backed by a fact carries that fact's id, so a click can show its textbook citation and quote.
"""
from __future__ import annotations

import re

from rag import ontology_facts as onto

LEVELS = ["Chief complaints", "Differential diagnosis", "Clinical phases", "Workup / triage",
          "Therapeutics / contraindications"]
MAX_DEPTH = len(LEVELS)
# Colours per semantic type (mid-tone fills that read on light and dark backgrounds)
KINDS = {
    "symptom": ("Symptom / complaint", "#3b82f6"),
    "condition": ("Condition", "#8b5cf6"),
    "stage": ("Clinical phase", "#c4b5fd"),
    "diagnostic": ("Investigation", "#f59e0b"),
    "drug": ("Drug", "#22a06b"),
    "contra": ("Contraindicated", "#e5484d"),
}
CAPS = {"symptoms": 8, "conditions": 6, "differentials": 3, "stages": 5, "diagnostics": 5, "drugs": 6, "contra": 4}
LINE_SHORT = {"FIRST_LINE": "1st line", "SECOND_LINE": "2nd line", "ADJUNCT": "adjunct",
              "REFRACTORY": "refractory", "SUPPORTIVE": "supportive"}


def _nid(kind: str, label: str) -> str:
    return f"{kind}:{label.strip().lower()}"


def _words(s: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", s.lower()) if len(w) >= 4}


def _same(a: str, b: str) -> bool:
    """Loose match between a vignette symptom and a fact's object label ('chest pain' ~ 'Severe chest pain')."""
    wa, wb = _words(a), _words(b)
    return bool(wa and wb) and (wa <= wb or wb <= wa)


def _dedupe(fs: list[dict]) -> list[dict]:
    seen, out = set(), []
    for f in fs:
        k = f["object_label"].strip().lower()
        if k not in seen:
            seen.add(k)
            out.append(f)
    return out


def symptoms_in_text(text: str, conditions: list[str], cap: int = CAPS["symptoms"]) -> list[str]:
    """Presentation facts of the conditions whose object is named in the text (for long vignettes)."""
    low = text.lower()
    out = []
    for c in conditions:
        for f in onto._about(onto.match_conditions(c), "MANIFESTS_AS"):
            lab = f["object_label"]
            if lab.lower() in low and lab not in out:
                out.append(lab)
    return out[:cap]


def build(symptoms: list[str], conditions: list[str], depth: dict[str, int] | None = None) -> dict:
    """Graph for the visualizer.

    symptoms    complaints from the vignette (may be empty: the conditions' MANIFESTS_AS objects are used)
    conditions  candidate condition names (any wording; matched to ontology labels)
    depth       {condition name: deepest level shown (2..5)}; missing = 2 (only the differential)

    Returns {"nodes": [...], "edges": [...], "facts": {fact id: fact}, "levels": {condition: [available levels]}}.
    Node: id, label, kind, level, title (hover), tag (short qualifier, e.g. "1st line"). Edge: id, from, to, label, fact (id or None), dashes.
    """
    depth = depth or {}
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}
    facts: dict[str, dict] = {}
    available: dict[str, list[int]] = {}

    def node(kind, label, level, title="", group=None, tag=""):
        i = _nid(kind, label)
        if i not in nodes:
            nodes[i] = {"id": i, "label": label, "kind": kind, "level": level, "title": title or KINDS[kind][0],
                        "group": group, "tag": tag}
        return i

    def edge(a, b, label, f=None, dashes=False):
        i = f"{a}->{b}"
        if i not in edges:
            edges[i] = {"id": i, "from": a, "to": b, "label": label, "fact": f["id"] if f else None, "dashes": dashes}
            if f:
                facts[f["id"]] = f
        return i

    # Level 1: complaints
    sym_ids = [node("symptom", s, 1) for s in list(dict.fromkeys(symptoms))[:CAPS["symptoms"]]]

    for cond in list(dict.fromkeys(conditions))[:CAPS["conditions"]]:
        labels = onto.match_conditions(cond)
        about = onto._about(labels) if labels else []
        by: dict[str, list[dict]] = {}
        for f in about:
            by.setdefault(f["predicate"], []).append(f)
        c = node("condition", cond, 2, f"Condition · {len(about)} certified facts"
                 + (f" ({', '.join(labels[:3])})" if labels else " · not in the ontology"), group=cond)
        levels = [lv for lv, key in ((3, "HAS_CLINICAL_STAGE"), (4, "CONFIRMED_BY"),
                                     (5, ("TREATED_BY", "CONTRAINDICATES")))
                  if any(by.get(k) for k in ((key,) if isinstance(key, str) else key))]
        available[cond] = levels

        # Level 1 <-> 2: complaints that the condition manifests as (cited); otherwise a dashed graph-match link
        pres = _dedupe(by.get("MANIFESTS_AS", []))
        if sym_ids:
            for sid in sym_ids:
                hit = next((f for f in pres if _same(nodes[sid]["label"], f["object_label"])), None)
                if hit:
                    edge(sid, c, "manifestation of", hit)
        else:
            for f in pres[:4]:
                edge(node("symptom", f["object_label"], 1), c, "manifestation of", f)
        if sym_ids and not any(e["to"] == c for e in edges.values()):
            for sid in sym_ids:
                edge(sid, c, "graph match", dashes=True)

        # Level 2: differentials named in the textbook
        for f in _dedupe(by.get("DIFFERENTIAL_OF", []))[:CAPS["differentials"]]:
            edge(c, node("condition", f["object_label"], 2, "Differential (textbook)", group=cond), "differential", f,
                 dashes=True)

        d = depth.get(cond, 2)
        if d >= 3:
            for f in _dedupe(by.get("HAS_CLINICAL_STAGE", []))[:CAPS["stages"]]:
                edge(c, node("stage", f["object_label"], 3, group=cond), "phase", f)
        if d >= 4:
            for f in _dedupe(by.get("CONFIRMED_BY", []))[:CAPS["diagnostics"]]:
                edge(c, node("diagnostic", f["object_label"], 4, group=cond), "confirmed by", f)
        if d >= 5:
            order = list(LINE_SHORT) + [None]
            tx = sorted(_dedupe(by.get("TREATED_BY", [])),
                        key=lambda f: order.index(f["clinical_facets"].get("line_of_therapy")
                                                  if f["clinical_facets"].get("line_of_therapy") in order else None))
            for f in tx[:CAPS["drugs"]]:
                line = LINE_SHORT.get(f["clinical_facets"].get("line_of_therapy"), "")
                edge(c, node("drug", f["object_label"], 5, f"Drug{' · ' + line if line else ''}", group=cond, tag=line),
                     f"treated by{' · ' + line if line else ''}", f)
            sev_order = {"STRICT": 0, "CAUTIONARY": 1}
            cx = sorted(_dedupe(by.get("CONTRAINDICATES", [])),
                        key=lambda f: sev_order.get(f["clinical_facets"].get("contraindication_severity"), 2))
            for f in cx[:CAPS["contra"]]:
                sev = (f["clinical_facets"].get("contraindication_severity") or "").lower()
                edge(c, node("contra", f["object_label"], 5, f"Contraindicated{' · ' + sev if sev else ''}",
                             group=cond, tag=f"avoid{' · ' + sev if sev else ''}"),
                     f"contraindicated{' · ' + sev if sev else ''}", f)

    return {"nodes": list(nodes.values()), "edges": list(edges.values()), "facts": facts, "levels": available}


def next_depth(current: int, available: list[int]) -> int:
    """Depth after one more drill-in click: the next level that has facts, or back to 2 (collapse) after the last."""
    nxt = [lv for lv in available if lv > current]
    return nxt[0] if nxt else 2
