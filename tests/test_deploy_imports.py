"""The deploy bundle (deploy/build_hf_bundle.py) ships app.py, rag/ and only ontology/merge.py.
Any other import of the ontology package from served code breaks the live app (it did once: rag.hops failed)."""
import ast
from pathlib import Path

SHIPPED_ONTOLOGY = {"ontology.merge"}


def _imports(path: Path) -> set[str]:
    out = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
        elif isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
    return out


def test_served_code_imports_only_shipped_ontology_modules():
    served = [Path("app.py"), *Path("rag").glob("*.py")]
    bad = {f"{p}: {m}" for p in served for m in _imports(p)
           if (m == "ontology" or m.startswith("ontology.")) and m not in SHIPPED_ONTOLOGY}
    assert not bad, f"not in the deploy bundle: {sorted(bad)}"


def test_shipped_ontology_module_is_stdlib_only():
    allowed = {"__future__", "re", "unicodedata", "collections"}
    assert _imports(Path("ontology/merge.py")) <= allowed
