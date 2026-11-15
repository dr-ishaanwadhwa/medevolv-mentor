# 5-minute presentation script: MedEvolv Mentor (v2 only)

Slot: 5:00 hard stop. About 1:00 problem, 3:00 demo, 1:00 Q&A. One presenter drives, everything happens in the browser.
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
