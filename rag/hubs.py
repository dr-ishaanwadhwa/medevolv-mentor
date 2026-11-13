"""Hub / map-of-content nodes (Stage 3 of docs/graph_networking_plan.md). Navigation only, never an answer source.

Built by scripts/build_hubs.py into data/graph/hubs.jsonl. Tiers: T1 certified fact, T2 derived (a rule over certified
facts), T3 inferred (LLM judgement, shown with evidence). Everything in this module is T2 or T3, so none of it may
reach an answer prompt, and a class or family edge must never carry TREATED_BY or CONTRAINDICATES down to a member.

    hubs_for("Ciprofloxacin")        -> [record, ...]   hubs this entity belongs to
    members("hub:organ:cardiovascular", k=20) -> [record, ...]
    all_hubs("drug_class")           -> [{"hub_id", "hub_type", "hub_label", "tier", "n_members"}, ...]

record = {"hub_id", "hub_type", "hub_label", "member_id", "member_label", "member_type", "tier", "method", "evidence"}
`evidence` is a section id (same id as rag.retrieve.search(section_ids=...)) or None. All functions return []
when data/graph/hubs.jsonl has not been built.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

PATH = Path("data/graph/hubs.jsonl")
KINDS = ("organ_system", "mechanism", "organism_genus", "organism_family", "drug_class", "condition_hierarchy")


@functools.cache
def _load() -> tuple[list[dict], dict, dict]:
    """(records, by_member_label: lowercase label -> [record], by_hub: hub_id -> [record])"""
    if not PATH.exists():
        return [], {}, {}
    rows, by_label, by_hub = [], {}, {}
    for line in PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append(r)
        by_label.setdefault(r["member_label"].lower(), []).append(r)
        by_hub.setdefault(r["hub_id"], []).append(r)
    return rows, by_label, by_hub


def hubs_for(entity_label: str) -> list[dict]:
    return [dict(r) for r in _load()[1].get(entity_label.strip().lower(), [])]


def members(hub_id: str, k: int = 50) -> list[dict]:
    rows = sorted(_load()[2].get(hub_id, []), key=lambda r: r["member_label"].lower())
    return [dict(r) for r in rows[:k]]


def all_hubs(kind: str | None = None) -> list[dict]:
    out = []
    for hid, rows in _load()[2].items():
        first = rows[0]
        if kind is None or first["hub_type"] == kind:
            out.append({"hub_id": hid, "hub_type": first["hub_type"], "hub_label": first["hub_label"],
                        "tier": first["tier"], "n_members": len(rows)})
    out.sort(key=lambda h: (-h["n_members"], h["hub_label"]))
    return out
