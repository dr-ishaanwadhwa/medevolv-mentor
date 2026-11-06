# med-rag: structure-aware multi-hop medical study companion

RAG chatbot for medical students (framed as an Eka Care extension): BODHI clinical graphs plan the hops,
textbooks supply cited evidence, STAIR (fine-tuned ToC retriever) finds the section.

## Setup
```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Day-1 checks
```bash
.venv/bin/python -m ingest.fetch_bodhi          # BODHI-S/M -> data/bodhi/
.venv/bin/python -m ingest.check_books data/books   # which PDFs have a usable ToC + text
```

## Corpus rules
Textbooks in `data/books/` and everything derived from them (OKF bundle, Chroma index, STAIR pairs,
adapters, GGUF) are git-ignored and **never published**. Publish code, method and eval numbers only.
Move to institutionally licensed copies before any public release.
