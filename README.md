# MedEvolv Mentor: multi-hop medical study companion (repo: med-rag)

RAG chatbot for medical students, by MedEvolv. Eka Care's open BODHI clinical graphs plan the hops,
textbooks supply cited evidence. The demo runs on vector retrieval plus graph-planned hops; the ToC router and
STAIR (fine-tuned ToC retriever) are kept as experiments behind `EXPERIMENTAL=1` (see `docs/stair.md`).

## Setup
```bash
python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Day-1 checks
```bash
.venv/bin/python -m ingest.fetch_bodhi          # BODHI-S/M -> data/bodhi/
.venv/bin/python -m ingest.check_books data/books   # which PDFs have a usable ToC + text
```

## Build the corpus (PDFs in data/books/, named by ISBN)
Each book's bookmarks are organised differently, so each gets its own section level. Sections are cut at the
bookmark's exact position on the page, so text is neither duplicated nor split mid-heading.

```bash
P=.venv/bin/python
# Pharmacology: bookmarks are chapter-only -> rebuild headings from fonts
$P -m ingest.font_toc data/books/978-93-5025-937-5.pdf --book-id tripathi \
  --title "Essentials of Medical Pharmacology (7th ed.)" --subject Pharmacology --isbn 978-93-5025-937-5 \
  --parent-pattern '^(Section \d+:|Appendices$)'
# Physiology: L1 units, L2 chapters, L3 sections
$P -m ingest.pdf_to_okf data/books/978-0-443-11101-3.pdf --book-id guyton \
  --title "Guyton and Hall Textbook of Medical Physiology (14th ed.)" --subject Physiology \
  --isbn 978-0-443-11101-3 --level 3 --chapter-level 2 --also-skip '^Guyton and Hall'
# Pathology: L1 chapters, L2 sections
$P -m ingest.pdf_to_okf data/books/978-0-323790-185.pdf --book-id robbins \
  --title "Robbins, Cotran & Kumar Pathologic Basis of Disease" --subject Pathology --isbn 978-0-323-79018-5 \
  --level 2 --chapter-level 1 --also-skip '^(Robbins, Cotran|How to use|Front matter|Inside front cover)'
# Medicine: L1 parts, L2 chapters, L3 sections
$P -m ingest.pdf_to_okf data/books/978-0-702-08347-1.pdf --book-id davidson \
  --title "Davidson's Principles and Practice of Medicine (24th ed.)" --subject Medicine --isbn 978-0-702-08347-1 \
  --level 3 --chapter-level 2 \
  --also-skip '^(International Advisory Board|Acknowledgements|Introduction|Sir Stanley Davidson|Half title|Inside front cover|Davidson.s Principles|Further information)$'
# Microbiology: L1 parts, L2 sections, L3 chapters (no deeper bookmarks)
$P -m ingest.pdf_to_okf data/books/978-81-947090-1-5.pdf --book-id micro \
  --title "Essentials of Medical Microbiology" --subject Microbiology --isbn 978-81-947090-1-5 \
  --level 3 --chapter-level 3 --also-skip '^(Prelims|Annexures)'
# Internal Medicine: Parts and Sections as parents, chapters as sections
$P -m ingest.pdf_to_okf data/books/978-12-6597-952-2.pdf --book-id harrison \
  --title "Harrison's Principles of Internal Medicine (22nd ed.)" --subject Medicine \
  --isbn 978-12-6597-952-2 --level 1 --parent-pattern '^(PART|SECTION)\s+\d+' \
  --also-skip '^(Related Harrison.*|Index)'

$P -m rag.index                     # embed all books into Chroma (~6 min, local model)
.venv/bin/streamlit run app.py
```

| Book | Chapters | Sections | Median words/section |
|---|---|---|---|
| Tripathi (Pharmacology) | 78 | 447 | 816 |
| Guyton (Physiology) | 85 | 443 | 1,040 |
| Robbins (Pathology) | 29 | 195 | 2,601 |
| Davidson (Medicine) | 35 | 303 | 1,674 |
| Microbiology | 82 | 82 | 4,873 |
| Harrison (Internal Medicine) | 505 | 505 | 6,576 |

Known gap: text between a chapter title and its first section bookmark (chapter intros) is not captured
(~4% of Guyton's body text).

## Corpus rules
Textbooks in `data/books/` and everything derived from them (OKF bundle, Chroma index, STAIR pairs,
adapters, GGUF) are git-ignored and **never published**. Publish code, method and eval numbers only.
Move to institutionally licensed copies before any public release.
