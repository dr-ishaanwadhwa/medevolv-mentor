"""Concept page payload: a thin composition of rag.concepts / hubs / comention / mentions / crosswalk / atlas.
Every link keeps its tier so the UI can tag certified / derived / suggested / navigation."""
from __future__ import annotations

from api.schemas import (BodhiRef, ConceptAtlas, ConceptGraph, ConceptHub, ConceptLink, ConceptPage, ConceptSection,
                         GraphEdge, GraphNode, SeeAlso)
from rag import atlas, comention, concepts, crosswalk, hubs, mentions

MAX_LINKS = 100
MAX_GRAPH_NODES = 40


def _guard(fn, default):
    try:                                            # optional layers: a missing data/graph file must not break the page
        return fn()
    except Exception:                               # noqa: BLE001
        return default


def _links(groups: dict[str, list[dict]]) -> list[ConceptLink]:
    out, seen = [], set()
    for pred, links in groups.items():
        for lk in links:
            key = (lk["other_id"], lk["predicate"], pred)
            if key not in seen:
                seen.add(key)
                out.append(ConceptLink(id=lk["other_id"], label=lk["other_label"], type=lk["other_type"],
                                       predicate=pred, tier=lk["tier"]))
    return out


def _sections(c: dict) -> list[ConceptSection]:
    out: dict[str, ConceptSection] = {}
    for t in c["topic_sections"]:
        if t.get("section_id"):
            out[t["section_id"]] = ConceptSection(section_id=t["section_id"], book_id=t["book_id"], title=t["heading"],
                                                  path=" › ".join(t["path"]), primary=True, tier="navigation")
    for r in _guard(lambda: mentions.sections_for(c["label"], k=8), []):
        if r["section_id"] in out:
            continue
        path = r.get("path") or ""
        out[r["section_id"]] = ConceptSection(section_id=r["section_id"], book_id=r["book_id"], title=r.get("title", ""),
                                              path=" › ".join(path) if isinstance(path, list) else path,
                                              primary=bool(r.get("primary")), tier="navigation")
    return sorted(out.values(), key=lambda s: not s.primary)


def _graph(c: dict) -> ConceptGraph:
    nodes = {c["id"]: GraphNode(id=c["id"], label=c["label"], type=c["type"], center=True)}
    for r in concepts.related(c["id"], k=MAX_GRAPH_NODES - 1):
        nodes.setdefault(r["id"], GraphNode(id=r["id"], label=r["label"], type=r["type"]))
    edges, seen = [], set()
    for lk_pred, links, outgoing in [(p, ls, True) for p, ls in c["outgoing"].items()] + \
                                     [(p, ls, False) for p, ls in c["backlinks"].items()]:
        for lk in links:
            if lk["other_id"] not in nodes:
                continue
            src, dst = (c["id"], lk["other_id"]) if outgoing else (lk["other_id"], c["id"])
            key = (src, dst, lk["predicate"])
            if key not in seen:
                seen.add(key)
                edges.append(GraphEdge(source=src, target=dst, predicate=lk["predicate"], tier=lk["tier"]))
    return ConceptGraph(nodes=list(nodes.values()), edges=edges)


def build(label_or_id: str) -> ConceptPage | None:
    c = concepts.concept(label_or_id)
    if not c:
        return None
    out, back = _links(c["outgoing"]), _links(c["backlinks"])
    see = []
    for r in _guard(lambda: comention.see_also(c["label"], k=8), []):
        hit = concepts.concept(r["label"])
        see.append(SeeAlso(id=hit.get("id"), label=r["label"], score=r["score"], books=r["books"], section_id=r["section_id"]))
    return ConceptPage(
        id=c["id"], label=c["label"], type=c["type"], aliases=c["aliases"], books=c["books"], degree=c["degree"],
        sections=_sections(c),
        links_out=out[:MAX_LINKS], links_in=back[:MAX_LINKS], links_out_total=len(out), links_in_total=len(back),
        hubs=[ConceptHub(hub_id=h["hub_id"], label=h["hub_label"], type=h["hub_type"], tier=h["tier"])
              for h in _guard(lambda: hubs.hubs_for(c["label"]), [])],
        see_also=see,
        bodhi=[BodhiRef(bodhi_id=b["bodhi_id"], name=b["bodhi_name"], type=b.get("bodhi_type", ""), relation=b["relation"],
                        tier=b["tier"]) for b in _guard(lambda: crosswalk.bodhi_for(c["label"]), [])],
        atlas=ConceptAtlas(link=_guard(lambda: atlas.atlas_link(c["label"]), None),
                           structures=_guard(lambda: atlas.structures_for(c["label"]), [])),
        graph=_graph(c),
    )
