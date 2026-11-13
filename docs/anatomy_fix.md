# Anatomy misses: diagnosis and fix (2026-11-13)

Scope: the misses in `docs/eval_2026-11-13.md` section 6 (`eval/anatomy_smoke.jsonl`, Gray's Anatomy for Students 5e, `book_id` "grays").
Nothing committed or deployed. Raw outputs: `reports/anatomy_smoke_before_anatomyfix.json`, `reports/anatomy_smoke_after_anatomyfix.json`.

## Root cause per miss

| Q | Does Gray's cover it? | Retrieval | Chunking / route | Root cause |
|---|---|---|---|---|
| a05 Erb's palsy | **Not by name.** "Erb" never appears in the Gray's PDF (checked the whole file, not only the sections). It has the superior trunk (C5 + C6) and a general "Injuries to the brachial plexus" box, but no arm position or waiter's-tip description. | bge-small has no notion of the eponym; top 10 is cranial-nerve palsies and EBV. With "upper trunk brachial plexus injury C5 C6" the right Gray's box is rank 1. | Route is `decompose` (the question has "and"); each sub-question takes top 3, mostly unrelated, so the model says INSUFFICIENT_CONTEXT. MIN_SIMILARITY (0.60) did not block anything: best hit was 0.71. | Content gap in the book plus an embedding vocabulary gap. **Not fixed**; see "Still open". |
| a02 inguinal canal | Yes: separate sub-sections for deep ring, superficial ring, anterior wall, posterior wall, roof, floor, contents. | All seven canal passages are in the top 10, but the anterior wall is rank 7 and `answer()` sends only TOP_K = 6. | Every `###` sub-heading forced a new passage, so the canal was split into 10 pieces of about 100 words. | Over-fragmentation: one structure spread over more passages than the top-6 window. The answer said "the sources do not describe an anterior wall". |
| a03 wrist drop | Yes: the radial nerve injury boxes (arm and hand) name it and give the site. | The arm box was rank 8, below median and ulnar injury boxes, so it was not sent. | Boxes were already separate passages, but the embedded text only had `chapter > section > box title`, with no region (arm vs hand). | Weak heading context in the embedded text. |
| a09 rectal veins | Yes, in the pelvic "Veins" passage (a 266-word mixed passage) and the portal-system section. | Both retrieved (ranks 2 and 3). | The pelvic passage mixes pelvic veins, rectal plexus, haemorrhoids and the clitoral vein, and the model skipped the middle/inferior rectal sentence. Also a missing sub-heading (see below) merged the text under it into the previous box. | Diluted passage; partly model variance. |
| a10 segments | **Only in the figure.** The text says "ten segments per lung"; the segment names exist only as artwork labels (Fig. 3.49, Helvetica font), which `grays_toc.py` dropped. | Gray's passage ranked first but contained no names; Davidson ranked next and supplied them. | n/a | Ingest threw away figure labels. |

Also found while checking the PDF: `grays_toc.py` did not recognise a fifth heading style (Sense-Regular 10.5 pt, e.g. "Cardiac veins", "Rib II"; about 146 in the book). Text under those headings was glued to whatever came before, including "In the clinic" boxes.

## Fixes

`ingest/grays_toc.py`
- New heading level 5 (Sense-Regular 10.5 pt short label without a full stop), written as `#####`.
- Figure artwork labels are collected per figure caption into one paragraph `Figure labels: Fig. N.N <caption>: label; label; ...` placed where the caption sits in reading order. A figure needs at least 6 labels (fewer made noisy passages), 60 labels max. That gives 835 figure passages in the index.
- Re-run output: 549 to 614 sections. `data/okf/grays/toc.json` and `index.md` were regenerated (titles only changed where h5 headings split sections).

`rag/chunk.py` (Gray's only, `book_id == "grays"`; the other six books take the old code path)
- Sub-headings no longer force a new passage while the current one is under 120 words; the heading stays in the text as its own line, so sibling parts (walls, roof, floor) share a passage. Boxes always start a passage, and a heading after a box always ends it.
- `Figure labels:` paragraphs are always passages of their own and exempt from tiny-passage merging.
- Embedded text carries the whole heading path (chapter, region, section, sub-heading), dropping part labels such as "Regional anatomy".
- Target passage size 260 words (was 300 for all books). The `kind: figure` metadata key is set on figure passages only.

`rag/retrieve.py`, `rag/hops.py`, `rag/answer.py`, `config.py`: untouched. MIN_SIMILARITY unchanged.

## Reindex

Yes. Backup: `data/chroma.bak-anatomyfix` (copy of the previous index). Rebuilt with `python -m rag.index` (log `reports/index_build_anatomyfix.log`).

| | before | after |
|---|---|---|
| total passages | 35,902 | 36,725 |
| grays | 2,072 | 2,895 (835 figure-label passages; text passages 22 / 188 / 316 words min / median / max) |
| harrison, robbins, davidson, guyton, tripathi, micro | 17,798 / 4,185 / 3,837 / 3,701 / 2,472 / 1,837 | identical |

The other six books were verified unchanged by comparing chunk ids and embedded-text lengths before and after (all equal), and the Chroma total equals the expected total.

## Anatomy smoke, before vs after

Same 14 questions (the original 10 plus 4 new generalisation checks a11 to a14), `answer_multihop`, DeepSeek. Key points were judged by DeepSeek against `key_points` (same judge both sides, so only relative numbers matter). Each side was run twice; "before" repeated exactly, "after" differed by one point (a09).

| a01 to a10 | before | after (run 1 / run 2) |
|---|---|---|
| answered | 9 / 10 | 9 / 10 |
| Gray's passage cited | 9 / 10 | 8 / 10 |
| Gray's passage in evidence | 10 / 10 | 10 / 10 |
| key points | 25 / 34 | 29 / 34 and 30 / 34 |

Per question (key points before, then after run 1 / run 2):

| Q | before | after |
|---|---|---|
| a02 inguinal canal | 3/5 | **5/5, 5/5** (anterior wall now present) |
| a03 wrist drop | 2/3 | **3/3, 3/3** (radial box is now rank 1 in Gray's; the model cited Harrison, so "Gray's cited" is false even though Gray's was in the evidence) |
| a09 rectal veins | 1/3 | **2/3, 3/3** |
| a10 segments | 3/3 | 3/3, now from Gray's figure labels only (earlier runs cited Davidson; one fresh before-run happened to cite both) |
| a05 Erb's palsy | 0/3 | 0/3, still "couldn't find this" |
| a04 femoral head | 2/3 | 2/3 |
| others (a01, a06, a07, a08) | full | full |
| new a11, a12, a14 | 4/4, 3/3, 3/3 | 4/4, 3/3, 3/3 |
| new a13 foot drop | 3/3 | 2/3 in both runs (the judge says the eversion point is missing; the answer is otherwise right and cites Gray's) |

a05 is the one real remaining miss.

## Retrieval regression check

`.venv/bin/python -m eval.run_eval retrieval --book <book> --retrievers vector`, generated sets:

| Book | n | chapter@1 | chapter@3 | baseline |
|---|---|---|---|---|
| Tripathi | 446 | 76.7% | 91.3% | 76.5% / 90.8% |
| Davidson | 338 | 78.4% | 94.7% | 78.4% / 94.7% |

No regression. Full `pytest`: 143 passed.

Cost: DeepSeek roughly 4 smoke runs of 14 questions plus judge calls, well under $0.50.

## Still open

- **a05 Erb's palsy.** Gray's does not name it, and the embedding model cannot link the eponym to "upper trunk (C5, C6)". A general remedy sits in `rag/hops.py` / query handling, which I did not touch: an alias or query-expansion step for eponyms (Erb, Klumpke, Colles, ...), or a fall-back that re-searches without the eponym when the decomposed sub-questions all return weak matches. The other books may cover it (Harrison has a plexopathy section) but were not retrieved either.
- Figure-label passages are 29% of Gray's passages; they win a10 but occasionally sit in the top 6 for a nearby topic (for example a muscle diagram for a muscle question). If that proves noisy, raise `MIN_LABELS` in `grays_toc.py` or stop indexing them for questions that name no figure.
- Gray's section ids and numbering changed (549 to 614 sections). Anything keyed on old Gray's section ids breaks; I found none in this repo. `scripts/build_atlas_crosswalk.py` reads titles from `toc.json`, which was regenerated while the atlas work was in progress, so it should re-run that script.
- The index was rebuilt in place while the app may have been running; restart any live server so it opens the new collection.
- To roll back: stop using `data/chroma` by restoring `data/chroma.bak-anatomyfix`, and regenerate sections from the previous `grays_toc.py`/`chunk.py` (no git here; a copy of the previous section files is in the session scratchpad, `.../scratchpad/grays_before`).
