"""Streamlit wrapper for the clinical graph component (index.html in this folder, vis-network, no build step).

    clinical_graph(graph, key="g1", on_change=cb)   -> last click {"kind": "node"|"edge", "id": ..., "nonce": ...}
"""
from pathlib import Path

import streamlit.components.v1 as components

from rag.clinical_graph import KINDS, LEVELS

_component = components.declare_component("clinical_graph", path=str(Path(__file__).parent))


def clinical_graph(graph: dict, key: str, height: int = 560, on_change=None):
    # Only nodes and edges go to the browser; the facts (with their quotes) stay in Python for the inspector.
    payload = {"nodes": graph["nodes"], "edges": graph["edges"]}
    return _component(graph=payload, kinds=KINDS, levels=LEVELS, height=height, key=key, default=None,
                      on_change=on_change)
