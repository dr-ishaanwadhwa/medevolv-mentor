# Presentation script: MedEvolv Mentor (v2 only) — 5-minute core + extensions to 15

Slot: officially 5:00. In practice the panel often lets presentations run to ~15 min. Plan for both:
**always land the 5-minute core first** (so a hard cut at 5:00 still leaves a complete story), then pull extension
modules (section below) in order while they keep listening. Stop at any module boundary.
One presenter drives; everything happens in the browser.
Live URL: **https://v2.130-210-60-153.sslip.io**. Streamlit (the minimum requirement) stays live at mentor.medevolv.in as the backup.

Timings below were measured on the live v2 host on 16 Nov (warm server):
- Comparison question: 4.0–4.1 s, decompose route, 4–5 citations.
- Off-topic decline: 0.3 s. Personal-dosing refusal: 0.3 s.
- Pheochromocytoma Why: about 3 s, verdict B, 6 citations, 3 viva questions.

## Pre-flight (T-10 min)
1. Open four tabs, in this order:
   - `/how`
   - `/` (Ask)
   - `/why`
   - `/c/MED%3AOKF%2Fanatomicalstructure%2Foptic-chiasm`
2. **Warm the server:** ask one question on the Ask tab. The first question after a restart takes ~11 s; after that ~3–4 s. Then press *Clear chat*.
3. **Warm the 3D view:** open the optic-chiasm tab once, so the models are cached in the browser.
4. Set browser zoom to 125% so the back row can read it. Light theme reads best on projectors.
5. Copy the comparison question to the clipboard: `Compare the mechanism of action of penicillins and aminoglycosides.`

## Run of show

### 0:00–0:50 · Problem, user, data (tab: `/how`)
> "MBBS students study from seven standard textbooks and increasingly ask chatbots that answer confidently with no source.
> MedEvolv Mentor answers only from the textbooks, shows the page for every claim, and says so when the books don't cover it."

- Scroll the *seven textbooks* card (the passage count is spoken; it is not on the page):
  - Tripathi, Guyton, Robbins, Davidson, Harrison, Microbiology, Gray's;
  - **36,725 passages**.
- **Pipeline, in one breath:** "~300-word passages split on paragraph boundaries (260 for Gray's), headings embedded with the text, bge-small embeddings in Chroma, top-6 retrieval with a 0.60 similarity floor, DeepSeek writes the answer, and a citation check verifies every [n]."
- **Data question?** One line: "Private research copies for this assignment; nothing from the books is published or committed."

### 0:50–1:50 · Grounded answer + the enhancement (tab: Ask)
1. Paste the comparison question and press Enter.
2. While it streams, point at the trace:
   > "It recognised two topics and split the question. That's our enhancement: query decomposition."
3. When the answer lands, tap citation **[1]**. The drawer shows book · chapter · pages and the passage.
   > "Every claim points at a page. And it tells you what it retrieved but didn't cite."
4. **Failure story** (say while the drawer is open):
   > "This exact question was our first failure. One embedding of a two-topic question retrieved 5 of 6 passages about aminoglycosides only. Splitting it fixed retrieval: both drug classes are now cited."

### 1:50–2:20 · Unsupported and unsafe (tab: Ask)
1. Tap the **cricket** demo card. It declines in under a second.
   > "Not in the books, so it won't guess."
2. Type `My mother has TB, what dose of rifampicin should she take?`. It refuses and redirects to a doctor.
   > "Study aid, not medical advice."

### 2:20–3:20 · Why was I wrong? (tab: `/why`)
1. Click **Try an example** (pheochromocytoma; you picked A, propranolol), then **Why was I wrong?**
2. Read the verdict:
   > "Correct is B, phenoxybenzamine. Why mine is wrong: a beta-blocker before alpha blockade causes unopposed vasoconstriction, cited to Davidson and Harrison."
3. Point at the three viva questions:
   > "It turns a wrong MCQ into a revision session. This is what students actually do: practise MCQs and fail them."

### 3:20–3:55 · Explore + 3D (tab: optic chiasm)
- Show *where the books discuss it*, the local graph, then **Open in 3D Atlas**.
  > "Textbook knowledge linked to a 3D model of the structure, labelled *navigation only*: it shows where it sits, not a clinical claim."

### 3:55–4:10 · Evidence (tab: `/how`, evals card)
> "On our 39-question test set it behaved correctly 39 out of 39: answer, decline or refuse.
> All 30 answers carried citations, and the right chapter is in the top 3 search results 90.8% of the time on 446 pharmacology questions.
> Those are our own test sets, not a clinical-safety claim."

### 4:10–5:00 · Q&A

## Extension modules (if they give you more time)

Take these in order; each is self-contained and ends cleanly. All questions were timed on the live v2 host on 16 Nov.
Rule of thumb: if they're asking questions, answer them. Questions beat modules, because questions are what they score.

| # | +Time | Module | Why it's next |
|---|---|---|---|
| E1 | 1:30 | **Clinical vignette (graph route):** paste the malaria demo card (Odisha, ring forms, banana-shaped gametocytes). It takes 4.5 s and gives 4 citations. Open *How this answer was made*: symptom linking to the clinical graph, the condition ranked, then per-hop retrieval. | Shows the third route (graph) and multi-hop retrieval, the deepest part of the 50% pipeline criterion |
| E2 | 1:00 | **Anatomy + 3D chip:** click the *superior orbital fissure* card. It takes 1.5 s, cites Gray's, and shows a "View in 3D" chip tagged navigation-only. Click the chip and the atlas opens on that structure. | Ties Ask to 3D in one motion |
| E3 | 1:00 | **Knowledge graph:** Explore, then *pheochromocytoma* (the richest page: 8 sections, 58 outgoing links). Show the tier tags (certified / derived / suggested). Click a graph node, then press Back. | Shows the quote-verified ontology (~25.9k facts) behind the answers |
| E4 | 1:00 | **3D exploration:** on `/atlas`, tap any structure. The side panel lists where the books discuss it. Use *Isolate* and *Layers*. | The wow moment, if the room responds to it |
| E5 | 0:45 | **Share + feedback:** *Share* on an answer copies an `/a/...` link (open it: a read-only card that keeps citation pointers, not textbook text). *Report a problem* sends a wrong-citation flag. | Shows it's a product, with a quality loop |
| E6 | 0:30 | **Mobile:** open the URL on a phone (bottom tabs Ask · Why · Explore · 3D). | Students study on phones |
| E7 | 1:30 | **Where it goes next** (talk, no clicks): direct-to-student is small; distribution through colleges or publishers is the route. The moat is the verification layer, not the model. Two gates before selling: content rights, and the clinician review getting to zero "major" (12/18 today). | Answers "is this a business?" without overclaiming. Source: docs/strategy_review_2026-11-14.md |
| E8 | 1:00 | **Failure analysis, deeper:** docs/failure_cases.md, cases 3–4. A graph data gap ranked lung abscess over TB, and a treatment hop borrowed an unrelated passage; fixed by requiring the passage to name the condition. | The rubric asks for failures *and fixes*; the room likes honesty |

Core 5:00, plus E1–E4 ≈ 9:30, plus E5–E8 ≈ 13:15, leaving ~1:45 for Q&A inside 15 minutes.

## Prepared answers (≤20 s each)
- **"Why not just ChatGPT?"** It can't show the page, and it doesn't decline. Ours does both, and the citation check is code, not a prompt.
- **"Where's the Streamlit UI?"** Streamlit was the minimum requirement and is live as our first version (mentor.medevolv.in). v2 is the same RAG engine behind a faster web front end.
- **"What still fails?"**
  - Hard clinical vignettes. In an 18-case clinician-style review, 12 had a major issue.
  - So we demo study questions, and selling waits on a clinician review.
  - Another example: two medicine books cover the same topic, and it sometimes cites the other one (23/25 right-book).
- **"Data rights?"** Private research copies. Before any release: college e-library licence, a narrow publisher licence, or open texts.
- **"Latency?"** About 3 s median answer time on the 39-question set (p95 4.6 s), and the steps stream live while it works.

## If something breaks on stage
- **An answer hangs past 15 s:** press Stop, then click the cricket card (it is instant) and continue. Mention that the trace shows each step.
- **v2 is down:** switch to mentor.medevolv.in and run the same three questions there (same engine).
- **The 3D view is slow:** skip it and say "3D atlas, linked from every anatomy concept" over the concept-page graph.
