"""Vector retrieval over passage chunks, optionally restricted to chosen sections (for the router / STAIR)."""
from __future__ import annotations

from dataclasses import dataclass

from rag import config
from rag.backends import embed
from rag.index import get_collection


@dataclass
class Hit:
    id: str
    passage: str
    meta: dict
    similarity: float   # cosine similarity, 1 = identical

    def citation(self) -> str:
        m = self.meta
        path = m["section_path"].split(" › ")
        chapter = m.get("chapter", m["section_title"])
        # Everything from the chapter down (drops the book title and "Section N:" grouping)
        parts = path[path.index(chapter):] if chapter in path else [chapter, m["section_title"]]
        parts = [p for p in parts if p != "Overview"]
        if m.get("heading") and m["heading"] not in parts:
            parts.append(m["heading"])
        where = " › ".join(parts)
        return f"{m['book']}, {where} (pp. {m['pages']})"


def search(query: str, k: int = config.TOP_K, section_ids: list[str] | None = None) -> list[Hit]:
    where = {"section_id": {"$in": section_ids}} if section_ids else None
    res = get_collection().query(
        query_embeddings=embed([query], is_query=True), n_results=k, where=where,
        include=["documents", "metadatas", "distances"],
    )
    return [
        Hit(id=i, passage=d, meta=m, similarity=1 - dist)
        for i, d, m, dist in zip(res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]
