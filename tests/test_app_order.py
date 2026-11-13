"""Streamlit runs app.py top to bottom, so a helper must be defined before the first module-level code path
that can call it. _safe was once defined below the chat render and crashed every Gray's answer (NameError)."""
import ast
from pathlib import Path


def test_shared_helpers_defined_before_render_functions():
    tree = ast.parse(Path("app.py").read_text())
    defs = {n.name: n.lineno for n in tree.body if isinstance(n, ast.FunctionDef)}
    # the Ask tab (the first top-level `with` that calls render_answer) is where answers are drawn
    ask_tab = next(n.lineno for n in tree.body if isinstance(n, ast.With)
                   and "render_answer" in ast.unparse(n))
    for name in ("_safe", "render_sources", "render_answer", "render_process", "tidy_path", "cite_text"):
        if name in defs:
            assert defs[name] < ask_tab, f"{name} defined at line {defs[name]}, after the Ask tab at {ask_tab}"
