"""Build / open the Chroma vector store of passage chunks.

Usage: python -m rag.index            (rebuilds the collection for the current EMBED_BACKEND)
"""
from __future__ import annotations

import time

import chromadb

from rag import config
from rag.backends import embed


def collection_name() -> str:
    model = config.LOCAL_EMBED_MODEL if config.EMBED_BACKEND == "local" else config.OCI_EMBED_MODEL
    return "passages__" + "".join(ch if ch.isalnum() else "_" for ch in model)[:50]


def get_collection(create: bool = False):
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    name = collection_name()
    if create:
        if name in [c.name for c in client.list_collections()]:
            client.delete_collection(name)
        return client.create_collection(name, metadata={"hnsw:space": "cosine"})
    return client.get_collection(name)


def build(batch: int = 128) -> None:
    from rag.chunk import iter_chunks          # build-time only: keeps ingest/ (pymupdf) out of the server
    chunks = list(iter_chunks())
    col = get_collection(create=True)
    t0 = time.time()
    for i in range(0, len(chunks), batch):
        part = chunks[i:i + batch]
        col.add(
            ids=[c.id for c in part],
            documents=[c.passage for c in part],
            embeddings=embed([c.text for c in part]),
            metadatas=[c.meta for c in part],
        )
        print(f"  {min(i + batch, len(chunks))}/{len(chunks)}  ({time.time() - t0:.0f}s)", end="\r")
    print(f"\nIndexed {len(chunks)} chunks into '{col.name}' at {config.CHROMA_DIR}")


if __name__ == "__main__":
    build()
