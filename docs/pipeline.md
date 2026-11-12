# Pipeline: data → chunking → embeddings → vector store → retrieval → LLM → answer

**Product framing.** **MedEvolv Mentor**, a study companion for medical students by MedEvolv. It builds on **Eka Care**, the
Indian health-tech company that publishes the BODHI clinical knowledge graphs. Users ask exam-style questions,
including multi-step clinical vignettes ("fever + joint pain after a mosquito bite → likely condition → which
specialist → treatment?"). Every claim is cited to a textbook section or a graph fact, and the bot declines when its
sources don't cover the question.

```
 5 textbook PDFs ──► ToC recovery ──► OKF bundle (1 markdown file per section, YAML metadata)
                                          │
                                          ├─► ~250-word passages ──► bge-small embeddings ──► Chroma
                                          │
                                          └─► toc.json (section labels) ──► STAIR training pairs ──► fine-tuned STAIR

 BODHI-S + BODHI-M (Eka Care graph) ──► networkx graph (6,560 nodes) ──► entity linking

 question ─► guard (personal advice?) ─► route
               ├─ clinical vignette→ graph hops: symptoms→conditions→specialist ; textbook: treatment per condition
               ├─ compound question→ decomposition: ≤3 sub-questions, retrieved separately
               └─ simple question  → vector retrieval over all books (router / STAIR: experimental only)
           ─► evidence (graph facts [G#] + passages [#]) ─► LLM (answer only from evidence, cite) ─► answer + trace
```

## 1. Data
| Source | What | Role |
|---|---|---|
| KD Tripathi, *Essentials of Medical Pharmacology* 7e | 78 chapters → 447 sections | treatment, drugs |
| Davidson's *Principles and Practice of Medicine* 24e | 35 chapters → 338 sections | clinical medicine |
| Robbins & Cotran *Pathologic Basis of Disease* | 30 chapters → 212 sections | mechanisms of disease |
| Guyton & Hall *Medical Physiology* 14e | 85 chapters → 478 sections | normal function |
| *Essentials of Medical Microbiology* | 82 chapters | organisms, diagnosis |
| BODHI-S / BODHI-M (Eka Care, CC BY-NC 4.0) | 13,204 + 3,566 triples | symptom → condition → speciality; condition → drug |

Books are local study copies, never redistributed; only code and metrics are published.

## 2. Chunking — structure first, size second
* **Sections come from the author's table of contents.** For books with deep PDF bookmarks, each section is cut at
  the bookmark's exact position on the page (PDF bookmark points are measured from the page bottom; columns are read
  left then right). Text between a chapter title and its first section becomes an *Overview* section. Coverage check:
  99–101% of each book's body text lands in exactly one section.
* **Tripathi's bookmarks stop at chapter level**, so headings are rebuilt from typography: bold ALL-CAPS = major
  heading, bold mixed case = sub-heading, bold paragraph lead = run-in head. 78 chapter entries → 447 sections.
* Each section is stored in **Google's Open Knowledge Format (OKF)**: one markdown file, YAML frontmatter with book,
  chapter, section path, pages, licence.
* Inside a section, paragraphs are packed into **~250-word passages** (bge-small's limit is 512 tokens), never
  splitting a paragraph, repeating a short last paragraph as overlap, and starting a new passage at every heading so
  one passage never mixes two topics. The heading path is embedded with the passage
  ("Beta-Lactam Antibiotics › Cephalosporins › Adverse effects"), so a passage that never names its topic is still
  findable. Result: 15k+ passages across the five books.

## 3. Embeddings and vector store
`BAAI/bge-small-en-v1.5` locally (OCI Cohere embeddings are a drop-in swap via `EMBED_BACKEND=oci`), cosine
similarity, persisted in **Chroma** with every passage's book / chapter / section / pages as metadata for filtering.

## 4. Retrieval — vector in the demo; two experimental retrievers

The demo uses **vector** retrieval. We also built a prompt-only ToC router and the data and training code for STAIR.
On held-out Tripathi questions with the local 3B model the router reached 32% chapter@1 against 77% for vector
(failure case 8), so both are hidden from the UI unless `EXPERIMENTAL=1`. STAIR training is future work.

| Retriever | How it finds the section | Training |
|---|---|---|
| **Vector** | nearest passages by embedding similarity | none |
| **ToC router** | LLM reads the chapter list, then the chosen chapter's section list; output constrained to real titles (JSON-schema enum) | none |
| **STAIR** | Mistral-7B fine-tuned (QLoRA) to answer a question with the section title; same two stages, same constraint | ~10 generated questions per section |

Router and STAIR pick sections; vector search then runs **inside** those sections only.

## 5. Multi-hop (enhancement: query decomposition)
* **Graph route** (only for clinical vignettes: ≥2 linked symptoms, or one symptom plus a case cue such as
  "patient", "year old", "presents", "diagnosis" — so "drug of choice for absence seizures" stays a plain lookup):
  symptoms in the question are linked to BODHI nodes (exact names, lay-term mapping such as
  "rash" → "Skin rash", and a semantic fallback). Conditions are ranked by how many symptoms point to them,
  weighted by BODHI's likelihood labels. Each top condition gives a speciality (graph) and a treatment sub-question
  (textbook). A textbook passage is only accepted for that hop if it names the condition — otherwise the answer
  states the book does not cover it.
* **Decomposition route**: compound questions ("compare X and Y") are split by the LLM into ≤3 sub-questions, each
  retrieved separately, so one topic cannot crowd out the other.
* **Cross-check**: drugs BODHI links to a candidate condition that also appear in the textbook-grounded answer are
  flagged as agreement.

## 6. Grounded generation and refusals
The LLM sees numbered evidence only and must cite every claim. The bot declines in three ways:
1. personal clinical requests ("my mother has TB, what dose…") → study-aid refusal, before any retrieval;
2. weak retrieval (best similarity below 0.60; on-topic questions measured 0.71–0.81, off-topic ~0.50) → "not in my
   sources", the LLM is never called;
3. the LLM itself answers `INSUFFICIENT_CONTEXT` when the evidence does not contain the answer.

## 7. Interface
Streamlit chat: retriever selector, multi-hop toggle (off = baseline for before/after), status badge, reasoning-path
panel (each hop and its result), graph facts, evidence with citations and short excerpts.
