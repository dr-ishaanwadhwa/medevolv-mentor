"""Section-level Ontology Extraction Worker with Disk Caching.

Extracts structured clinical facts from OKF markdown sections using DeepSeek / LLM backends
with fault-tolerant disk caching for resumable processing.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Any

from ontology.prompt import CLINICAL_SYSTEM_PROMPT, build_extraction_prompt
from ontology.schema import ExtractionItem, SectionExtractionResult
from rag.backends import chat

logger = logging.getLogger(__name__)

CACHE_DIR = Path("data/ontology/cache")


def parse_okf_section(path: Path) -> tuple[dict[str, Any], str]:
    """Parse OKF section file into frontmatter dict and body text."""
    content = path.read_text(encoding="utf-8", errors="replace")
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    raw_yaml, body = parts[1], parts[2].strip()
    meta: dict[str, Any] = {}
    for line in raw_yaml.splitlines():
        line = line.strip()
        if ":" in line and not line.startswith("#"):
            k, v = line.split(":", 1)
            k, v = k.strip(), v.strip()
            # Basic parsing for string, int, list
            if v.startswith('"') and v.endswith('"'):
                meta[k] = v[1:-1]
            elif v.startswith("[") and v.endswith("]"):
                try:
                    meta[k] = json.loads(v)
                except Exception:
                    meta[k] = v
            elif v.isdigit():
                meta[k] = int(v)
            else:
                meta[k] = v
    return meta, body


def _chunk_body(body: str, max_words: int = 2500) -> list[str]:
    """Chunk body into readable windows along paragraph boundaries if too long."""
    words = body.split()
    if len(words) <= max_words:
        return [body]

    paragraphs = body.split("\n\n")
    chunks: list[str] = []
    current_paras: list[str] = []
    current_count = 0

    for p in paragraphs:
        p_words = len(p.split())
        if current_count + p_words > max_words and current_paras:
            chunks.append("\n\n".join(current_paras))
            current_paras = [p]
            current_count = p_words
        else:
            current_paras.append(p)
            current_count += p_words

    if current_paras:
        chunks.append("\n\n".join(current_paras))
    return chunks


def extract_from_section(path: Path, force: bool = False) -> SectionExtractionResult:
    """Extract clinical ontology triples from an OKF section with disk caching."""
    meta, body = parse_okf_section(path)
    section_id = meta.get("id", path.stem)
    book_id = meta.get("book_id", path.parent.parent.name)
    chapter = meta.get("chapter", "Unknown Chapter")
    title = meta.get("title", path.stem)
    book_title = meta.get("book", book_id.capitalize())

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.md5(f"{section_id}:{path.stat().st_mtime}".encode()).hexdigest()
    cache_file = CACHE_DIR / f"{book_id}_{cache_key}.json"

    if not force and cache_file.exists():
        try:
            cached_data = json.loads(cache_file.read_text(encoding="utf-8"))
            return SectionExtractionResult(**cached_data)
        except Exception as e:
            logger.warning("Cache read failed for %s, re-extracting: %s", path, e)

    chunks = _chunk_body(body, max_words=2500)
    # Cap at first 4 chunks (up to 10,000 words per section) to manage execution time & budget
    all_triples: list[ExtractionItem] = []
    failed_chunks = 0

    for idx, chunk_text in enumerate(chunks[:4]):
        prompt = build_extraction_prompt(
            section_title=f"{title} (Part {idx + 1})" if len(chunks) > 1 else title,
            book_title=book_title,
            chapter=chapter,
            text=chunk_text,
        )

        try:
            response_text = chat(
                system=CLINICAL_SYSTEM_PROMPT,
                user=prompt,
                temperature=0.0,
                max_tokens=4000,
                json_mode=True,
                purpose=f"ontology extraction: {section_id} (chunk {idx + 1}/{min(len(chunks), 4)})",
            )
            try:
                data = json.loads(response_text)
            except json.JSONDecodeError:
                trimmed = response_text.strip()
                last_brace = trimmed.rfind("}")
                if last_brace > 0 and '"triples"' in trimmed:
                    repaired = trimmed[:last_brace + 1] + "\n]}"
                    data = json.loads(repaired)
                else:
                    raise
            raw_triples = data.get("triples", [])
            for item in raw_triples:
                try:
                    all_triples.append(ExtractionItem(**item))
                except Exception as e:
                    logger.debug("Skipping invalid triple in %s: %s", section_id, e)
        except Exception as e:
            failed_chunks += 1
            logger.error("LLM extraction failed for %s chunk %d: %s", section_id, idx, e)

    result = SectionExtractionResult(
        section_id=section_id,
        book_id=book_id,
        chapter=chapter,
        triples=all_triples,
    )

    # Save to disk cache, but never cache a section where any LLM call failed: a transient outage would
    # otherwise be remembered forever as "this section has no facts".
    if failed_chunks:
        logger.warning("Not caching %s: %d chunk(s) failed; rerun to retry", section_id, failed_chunks)
        return result
    try:
        cache_file.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("Failed to write cache for %s: %s", section_id, e)

    return result
