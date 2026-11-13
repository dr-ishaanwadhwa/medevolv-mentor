"""Assemble the private Hugging Face Space bundle (code + BODHI + a compacted Chroma index) in one folder.

    .venv/bin/python -m deploy.build_hf_bundle OUT_DIR
    hf upload <user>/<space> OUT_DIR . --repo-type space

Copies only what the running app reads. The textbooks and OKF bundle stay on this machine.
"""
import shutil
import sys
from pathlib import Path

import chromadb

from rag.index import collection_name

ROOT = Path(__file__).resolve().parent.parent


def main(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    for f in (ROOT / "deploy/hf").iterdir():
        shutil.copy(f, out / f.name)
    shutil.copy(ROOT / "app.py", out / "app.py")
    shutil.copytree(ROOT / ".streamlit", out / ".streamlit")
    shutil.copytree(ROOT / "rag", out / "rag", ignore=shutil.ignore_patterns("__pycache__"))
    for part in ("BODHI-S", "BODHI-M"):
        for name in ("triples.jsonl", "nl_facts.jsonl"):
            src = ROOT / "data/bodhi" / part / "data" / name
            (out / "data/bodhi" / part / "data").mkdir(parents=True, exist_ok=True)
            shutil.copy(src, out / "data/bodhi" / part / "data" / name)

    # Certified ontology facts (git-ignored: they carry short textbook quotes). Optional: the app runs without them.
    onto = ROOT / "data/ontology/clinical_ontology.jsonl"
    if onto.exists():
        (out / "data/ontology").mkdir(parents=True, exist_ok=True)
        shutil.copy(onto, out / "data/ontology/clinical_ontology.jsonl")

    # Entity <-> section mention index (git-ignored, labels and section ids only). Optional, like the ontology.
    graph = ROOT / "data/graph"
    if graph.exists():
        shutil.copytree(graph, out / "data/graph")

    # Copy the one live collection into a fresh store (drops segments left behind by deleted collections)
    name = collection_name()
    src = chromadb.PersistentClient(str(ROOT / "data/chroma")).get_collection(name)
    dst_client = chromadb.PersistentClient(str(out / "data/chroma"))
    dst = dst_client.create_collection(name, metadata=src.metadata)
    total = src.count()
    for off in range(0, total, 2000):
        b = src.get(include=["embeddings", "documents", "metadatas"], limit=2000, offset=off)
        dst.add(ids=b["ids"], embeddings=b["embeddings"], documents=b["documents"], metadatas=b["metadatas"])
    assert dst.count() == total, (dst.count(), total)
    print(f"bundle at {out}: {total} passages")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
