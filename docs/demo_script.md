# MedEvolv Mentor: demo script (17 Nov 2026, about 11 minutes plus questions)

Live app: https://mentor.medevolv.in (backup: https://130-210-60-153.sslip.io)

Every question below was run through `answer_multihop` against the local code and index on 13 Nov, twice each.
The Explore click paths were also clicked through on the live site. Routes, statuses, cited books and latencies
are in the table at the end. Headline numbers are `{{EVAL_*}}` placeholders; the eval refresh fills them in.

## Timing plan

| Time | Block | Length |
|---|---|---|
| 0:00 | Opening | 0:30 |
| 0:30 | 1. Clinical vignette (case route, three axes) | 2:00 |
| 2:30 | 2. Pharmacology with a textbook-ontology warning | 1:15 |
| 3:45 | 3. Anatomy from Gray's | 0:45 |
| 4:30 | 4. Comparison (decompose route) | 1:00 |
| 5:30 | 5. Two refusals | 1:00 |
| 6:30 | 6. Explore: Rifampin, backlinks, hub, local graph | 2:00 |
| 8:30 | 7. Books differ: rheumatoid arthritis | 0:45 |
| 9:15 | What we tried that didn't work: STAIR | 1:30 |
| 10:45 | Honest limits | 0:45 |
| 11:30 | Questions | open |

If you are running long, drop step 3 (anatomy) and the third refusal in step 5. Those are the safest cuts.

## Setup on the day

- One browser window at 100% zoom. Press Ctrl + minus once or twice (80% to 90%) before the Explore steps so the
  local graph fits on screen. Put the browser in full screen.
- Pre-load two tabs of the same site: tab A for Ask, tab B for Explore. Streamlit keeps each tab's state, so
  switching tabs is faster than clicking the in-app tab and losing your place.
- Open a notes file with the three long questions (steps 1, 2 and the fallback vignette) ready to paste. Do not
  type the 64-word vignette live.
- The sidebar toggle "Multi-hop reasoning" must be ON (it is the default). Do not touch it unless you do the optional
  before/after in step 4.
- Click "Clear chat" in the sidebar before you start, so the first screen is the empty one with the demo tiles.
- Three questions are one-click tiles under "Try a demo question": the penicillins comparison, the cricket question
  and the "My mother has TB" question. The others are typed or pasted into the chat box.

---

## Opening (30 seconds)

**On screen:** the header and the "How it works" tab, the question-time diagram only. Do not read the page.

**Say:**

> Medical students already use ChatGPT, and the problem is that it sounds equally sure when it is right and when it
> is making things up. MedEvolv Mentor answers only from seven standard textbooks: Tripathi, Guyton, Davidson,
> Robbins, Microbiology, Harrison and Gray's. It cites every claim, it declines when its sources don't cover the
> question, and it shows you exactly how each answer was made. We will go through that live. The pipeline is
> on this diagram: a safety check, a router, a search, a relevance filter, and only then the language model,
> which is told to use nothing but the evidence it is handed.

**Fallback:** none needed; this tab is static.

---

## Step 1: Clinical vignette, case route, three axes (2:00)

**Paste into the chat box (64 words):**

```
A 62-year-old man presents 2 hours after onset of crushing chest pain. BP is 82/50 mmHg, JVP is raised, lung fields are clear. ECG shows ST elevation in II, III and aVF with 1 mm ST elevation in V4R. What is the likely diagnosis and its cause, how should he be stabilised now, and which commonly used anti-anginal drugs must be avoided and why?
```

**Point at, in order:**

1. The live status box while it works. The steps tick off one by one, so the wait is part of the demo.
2. The two pills above the answer: "Grounded answer" and "Long case · focused look-ups".
3. The answer has three bold headings, one per axis: Etiology and differential, Emergency stabilization, Definitive
   pharmacology and contraindications.
4. The "Avoid:" line at the bottom. It names nitrates (right ventricular infarct, hypotension), beta blockers at this
   blood pressure, and flecainide. Each carries a citation.
5. Open "How this answer was made" (about 15 steps). Show these rows: "3 clinical axis/axes, 5 look-ups · likely
   Inferior ST-elevation myocardial infarction with right ventricular involvement", then the six vector searches,
   then "Textbook ontology lookup" (certified facts added), then "Citation check" (for example "9 of 9 textbook
   passages cited, 4 of 4 graph facts cited").
6. Open "Sources": passages from Harrison and Davidson every time, Tripathi on about half of the runs; the graph facts
   tagged "WARNING (textbook ontology)" with their book and page.

**Talking point (one line):** A long case is too blurry for one search, so the model splits it into the three things a
clinician reasons about, searches each separately, and every line of the answer points back to a page.

**Why it works reliably:** 64 words puts it over the 35-word threshold, so it always takes the case route. Six runs: all
`case`, all `answered`, all three axes, 2 certified warnings, 7 to 9 textbook passages cited.

**If asked "is that case in your test set?":** yes, it is one of the 15 hard cases in `eval/hard_cases.jsonl`, chosen
because it has a known trap (nitrates in right ventricular infarction). Say so before they ask.

**Fallback if slow (over 15 s) or it errors:** keep talking through the status box; the call is a single DeepSeek
request after the searches. If it fails outright, paste the diabetic ketoacidosis case instead (3 warnings, all runs
`case`, 5 books cited):

```
A 19-year-old with type 1 diabetes presents with vomiting, abdominal pain and deep sighing breathing. Glucose 32 mmol/L, pH 7.08, bicarbonate 7 mmol/L, anion gap 26, serum ketones strongly positive, potassium 3.0 mmol/L. Explain the metabolic derangement and give the correct order of initial management, including when insulin can safely be started.
```

If the site is down, show the backup screenshots of this answer and say so.

---

## Step 2: Pharmacology with a textbook-ontology warning (1:15)

**Type or paste:**

```
A patient has wheeze and breathlessness. Which drug class is the first-line treatment and which drugs must be avoided?
```

**Note for the team:** a pure factual pharmacology question never shows a warning line. Questions such as "Why is morphine
contraindicated in head injury?" take the single route, which has no graph or ontology step. The warning lines only
exist on the graph route (short vignette: two symptoms, or one symptom plus a case word such as "patient") and the case
route. So this step is phrased as a short drug question about a patient, which routes to the graph. If the professor
asks, say that openly.

**Point at, in order:**

1. The pill "Clinical case · graph route". Contrast it with step 1: short vignette means graph route, long vignette
   means case route.
2. The answer sections: likely conditions, specialist, first-line treatment, confirmatory tests, and a bold
   "Warnings (drugs to avoid)" line.
3. The warning line: timolol, adenosine and beta blockers in asthma (bronchospasm). Open "Sources" and show the
   "WARNING (textbook ontology)" rows. The three asthma warnings come from three different books (Tripathi, Davidson,
   Harrison), each with its page range.
4. If someone asks why COPD drugs appear too: the graph proposed asthma, COPD and lung abscess from the two symptoms.
   The books then decide, and the answer is written as a differential to consider, not a diagnosis.

**Talking point:** The warning is not the model's opinion. It is a certified fact with a quote that was found
word-for-word in a textbook, and the model is required to state it.

**Reliability:** two runs, both `graph`, both `answered`, 5 warnings in the evidence, the "Warnings" line present both
times. The first-line answer is inhaled corticosteroids both times.

**Fallback:** ask the shorter variant "A patient has wheeze, breathlessness and cough at night. Likely diagnosis and drug
treatment?" (graph route, 4 warnings, "Warnings" line present in both runs). If both are slow, ask the pure factual
question "Why is morphine contraindicated in head injury?" (about 1.5 s, Tripathi only) and say the warning panel
appears on the clinical routes.

---

## Step 3: Anatomy from Gray's (0:45)

**Type:**

```
What are the boundaries and contents of the femoral triangle?
```

**Point at:** the pill "Single question · direct search"; every citation is Gray's (all six retrieved passages and the
four cited ones are Gray's Anatomy for Students); in "Sources" the green "cited" pills with book name "Gray's · Anatomy"
and the match scores (0.72 to 0.78).

**Talking point:** The newest book we added is Gray's, so anatomy now works and the answer comes from the right textbook
without any anatomy-specific code.

**Reliability:** two runs, both `single`, both `answered`, 4 of 6 passages cited, all Gray's. The answer names the
inguinal ligament, sartorius and adductor longus.

**Fallback:** "What are the rotator cuff muscles and their nerve supply?" (two runs, `single`, `answered`, Gray's only).

---

## Step 4: Compound question, decompose route (1:00)

**Click the tile:** "Compare the mechanism of action of penicillins and aminoglycosides" (Comparison).

**Point at:** the pill "Compound · split into parts". Open "How this answer was made" and show the row "Split into 2
sub-question(s)": "What is the mechanism of action of penicillins?" and "What is the mechanism of action of
aminoglycosides?", then two separate vector searches. The answer has one section per drug class.

**Talking point:** One embedding of a two-topic question lands near whichever topic dominates, so before this fix five
of six passages were about aminoglycosides. Splitting gives each side its own evidence. This is the multi-hop
enhancement from the brief.

**Optional 30-second contrast:** turn the sidebar toggle "Multi-hop reasoning" off, tick the same tile again, and point
out the lopsided sources. Turn it back on afterwards. (This is the only unrehearsed move in the script. Skip it if you
are behind.)

**Reliability:** three runs, all `decompose`, all `answered`. Tripathi cited every time, Harrison on some runs; both
classes always had their own passages. Latency varied from 4.7 to 10.3 s because the answer is long.

**Fallback:** "Compare type 1 and type 2 diabetes mellitus." (`decompose`, `answered`, Harrison with Davidson, 3.9 to 5.0 s).

---

## Step 5: Two refusals (1:00)

**Click the tile:** "My mother has TB, how much rifampicin should she take?" (Personal advice).

**Point at:** the red pill "Personal medical advice: declined", and "How this answer was made": two steps only. The
regex matched "my mother" and the bot declined before any search. Nothing about a real person reaches the model.

**Then click the tile:** "Who won the 2011 cricket world cup?" (Off-topic).

**Point at:** the amber pill "Not in the textbooks: declined". In the trace, the "Relevance threshold" row says the
best match scored 0.53, below the 0.60 threshold, so the language model is never called. That is why it returns
instantly.

**Talking point:** There are three ways it says no: before the search (personal advice), after the search if the books
are too far away (the 0.60 threshold, no model call), and a third where the model itself reads the passages and says
they don't answer it.

**Optional third refusal (15 seconds):** type "What is the best way to learn pharmacology quickly?" It passes the
threshold (0.73) because it mentions pharmacology, so the model reads the passages and the bot declines with
"Evidence insufficient: declined". This shows the third layer.

**Reliability:** two runs each. Personal advice: `personal_refusal`, 0.0 s, 2 steps. Cricket: `not_in_sources`, best
match 0.53, 0.1 s warm (4.7 s on the very first call after a restart). Learn-pharmacology: `insufficient`, 0.7 to 1.0 s.

**Fallback:** "Should I take ibuprofen for my headache?" (`personal_refusal`) or "What was Eka Care's revenue last year?"
(in the evaluation set as off-topic).

---

## Step 6: Explore, search a drug, then backlinks, click-through, hub, local graph (2:00)

**Click path (Explore tab):**

1. Type `Rifampin` in "Search any concept" and press Enter. Click the first chip, "Rifampin · Drug / therapy"
   (not "Rifampin-resistant tuberculosis").
2. On the Rifampin page, point at: the four book pills (Davidson, Harrison, Microbiology, Tripathi), then **Part of**
   (drug class: Antibiotics, Antimicrobial agents, Antimicrobials; mechanism: Cytochrome P450 enzymes).
3. **Linked from**, "Treats · 26" with the grey "derived" tag. Say this is the same certified fact read backwards, so it
   adds no new claim. Click "Tuberculosis · 4 books".
4. On the Tuberculosis page, the breadcrumb now reads "Explore › Rifampin › Tuberculosis". Point at the six book pills
   (including Gray's), **Part of** "Infectious" and **Also in BODHI** ("Tuberculosis, same concept, T2"), and in
   "Treated by" the chip "Rifampin · 4 books", which closes the loop.
5. Click "← Back" to return to Rifampin. Open **See also · 10** (Rifamycins, Rifabutin, Pyrazinamide, Ethambutol,
   Isoniazid, and others) and say it is grey on purpose: books discuss these together, which is not a clinical link.
6. Under **Part of**, click the drug-class chip "Antibiotics". The hub page shows "Drug class · 44 members · suggested".
   Say members share a heading, not their facts. Click "← Back".
7. Scroll to **Local graph**: Rifampin in the centre with about 24 concepts (what it treats, its adverse effects,
   "is a First-line antitubercular drug"). Switch on **Show hubs** to add the group boxes on dotted lines. Mention the
   2-hop toggle but do not turn it on live (it is large).

**Talking points:**

- The graph is a second brain over the books. A fact is written once, and now every concept knows who points at it.
- Solid lines are certified facts from the textbooks, dashed lines are those facts read backwards, dotted lines are
  groupings. The page says what each one is, so a student cannot mistake a navigation aid for a clinical claim.
- Navigation never feeds the answer model. Only certified facts do.

**Known flaw, handle it calmly:** the Rifampin page also lists a "Second-line anti-tubercular agents" group. That is a
model-suggested grouping (tagged "suggested") and it is clinically wrong for rifampin, whose own certified fact on the same
page says it is a first-line antitubercular drug. Do not click that chip. If a clinician spots it, say: "Correct, that is
exactly why groupings are tagged suggested and are never used in answers. The certified fact is the one that counts."
"Also in BODHI" does not appear on the Rifampin page (no BODHI match for it); it appears on Tuberculosis, so use that page.

**Reliability:** clicked through on the live site on 13 Nov, and the same data checked in Python: search returns
Rifampin first; 26 "treats" backlinks; 5 hub chips; 10 "See also"; Tuberculosis has the BODHI match and 6 books. Explore
makes no model call, so there is no DeepSeek dependency and it is fast after the first load.

**Fallback:** if a chip does not respond, click once and wait a second; Streamlit re-runs the page on each click.
If search fails, click "Browse by organ system" and use the step 7 path. Keep screenshots of the Rifampin page, the
Tuberculosis page and the local graph.

---

## Step 7: Books differ, rheumatoid arthritis (0:45)

**Click path (Explore tab):** if you are on a concept page, click "Browse by organ system". The first organ system,
"Blood & immunology", is already selected. Under "2 · Disease category" click "Rheumatoid Arthritis". The condition
box already reads "Rheumatoid arthritis · 114 facts". Click the collapsed bar "Books differ · 1 case".

**Point at:** the card for methotrexate. "Listed as a treatment" cites Tripathi, Robbins, Davidson and Harrison (the
DMARD of first choice). "Listed as a contraindication" cites Davidson. The banner says "Neither is marked wrong, so
read both sources."

**Talking point:** Where books give different recommendations we show both with their sources instead of letting the
model average them. For students, that is usually a population or timing difference, not an error.

**What to say about the pregnancy detail:** the Davidson quote shown in the card is the list of DMARDs to avoid and does
not mention pregnancy. The scoped fact is in the Warnings tab under "Clinical facets" below: "methotrexate is
contraindicated in Rheumatoid arthritis when the patient is pregnant, planning pregnancy or breastfeeding". Open that tab
if asked. Do not say "the books disagree"; say "the books differ by context".

**Do not oversell the feature.** Most other "differ" cases in the data are first-line drug lists where one book simply
lists more drugs than another (for example Tuberculosis). Rheumatoid arthritis is the cleanest example, which is why we
use it.

**Reliability:** verified on the live site: exactly one case, the methotrexate card above.

**Fallback:** the Systemic Lupus Erythematosus condition (Blood & immunology) also has cases (5 in the data).

---

## What we tried that didn't work: STAIR (1:30)

**On screen:** the handbook's STAIR table, or one slide with the table below. No live demo.

| Retriever (338 held-out Davidson questions) | Chapter@1 | Section@1 | Section@3 | Seconds per question |
|---|---|---|---|---|
| Vector search (bge-small, what the product uses) | 78.4% | 57.1% | 79.0% | 0.04 |
| DeepSeek reading the table of contents, no training | 75.1% | 38.5% | 50.0% | 2.1 |
| STAIR: fine-tuned Mistral-7B table-of-contents retriever | 73.4% | 36.4% | 36.4% | 2.1 |

**Say:**

> STAIR was our attempt to navigate a textbook the way a student does: look at the table of contents, pick a chapter,
> then a section. We fine-tuned Mistral-7B with QLoRA on a free Kaggle GPU, training it on 5,460 Davidson questions,
> with output constrained to real section titles. On 338 held-out Davidson questions it found the right section first
> 36.4% of the time. Plain vector search got 57.1%, and an untrained DeepSeek reading the same table of contents got
> 38.5%.

**Why this is a useful negative result:**

1. It was a fair test of a reasonable idea. The test questions came from the same generator as the training data, which
   favours STAIR, and it still lost.
2. It had a control. The untrained model reading the same table of contents scored about the same (38.5% against
   36.4%). So fine-tuning added nothing, and the ceiling is the section titles, many of which are generic ("Overview",
   "Presenting problems"). Vector search reads the passage text itself.
3. It was also about 50 times slower per question (2.1 s against 0.04 s), and its top-3 scores equal its top-1 scores
   in the table, so it gives no usable ranked list to fall back on.
4. It changed what we built. We stopped, did not train the Tripathi run, kept vector search plus the graph and the
   ontology for retrieval, and use DeepSeek for reasoning, not for finding sections.

**Do not claim:** that ToC retrieval can never work, only that it does not beat passage retrieval on these books, and
that the training set shares a generator with the test set. Both are in the handbook.

---

## Honest limits (45 seconds, three bullets)

- **Data gaps show up as a weak differential.** BODHI is an open graph with missing links. A child with fever, cough, runny
  nose and a spreading rash gets "Viral exanthem" ranked above "Measles" (checked on 13 Nov). The trace shows this, and the
  textbooks then decide the treatment. The TB vignette now ranks Pulmonary tuberculosis first.
- **Verified quotes are not verified medicine.** The ontology facts were extracted by a language model. We prove the quote is
  word-for-word in the source, which shows the source says it, not that the fact was read correctly. Always open the
  source. The "suggested" drug-class groupings are the same kind of limit, which is why they never reach the answer model.
- **Seven books, and it is a study aid.** If the books don't cover something (for example acute dengue management before
  Harrison was added) it says so. It is not clinical decision support, and the LLM judge in our evaluation is DeepSeek
  grading itself, so we treat its scores as an upper bound.

---

## Likely professor questions

**How do you control hallucination?** Four layers. The model sees only numbered passages and is told to use nothing
else. Every claim must carry a citation and each citation is checked against the evidence list. If the best passage scores
under 0.60 the model is never called. If the model reads the passages and finds no answer it must reply
INSUFFICIENT_CONTEXT, and we decline. In the 36-question test, behaviour was right on {{EVAL_STATUS}} and
{{EVAL_JUDGE}} of claims were judged supported, with the caveat that DeepSeek is the judge.

**Copyright: are you republishing the books?** The PDFs and everything derived from them stay out of git and are not
published. The live site shows up to nine excerpts of about 300 characters per answer so the student can check each
citation, which the team decided knowingly for the demo. The site is noindex and can be gated with a password in one
line. For a real release we would move to institutional access or licensed content. Eka Care's BODHI graph is credited
under CC BY-NC 4.0 and used non-commercially.

**How did you evaluate it?** Three parts. (1) A 36-question set covering factual, comparison, clinical case, off-topic
and personal-advice questions: expected behaviour {{EVAL_STATUS}}, right textbook cited {{EVAL_CITED}}, median latency
{{EVAL_P50}}, p95 {{EVAL_P95}}. (2) Retrieval on 446 held-out questions: correct chapter first {{EVAL_RETRIEVAL_CH1}}.
(3) 15 hard clinical cases scored against rubrics, including traps such as nitrates in right ventricular infarction. Known
weakness: generated questions share wording with the passages, which favours vector search, and the judge is DeepSeek.

**Why not just ChatGPT?** Three differences you can see on screen. It answers from named textbooks and cites page ranges,
so you can check it; it refuses personal advice and off-topic questions instead of improvising; and the trace shows the
route, the searches and the checks. A general chatbot is not wrong more often on exam facts; it is unaccountable, and for
a student the citation is the learning tool.

**What does it cost to run?** About 0.2 cents per answer on DeepSeek, measured on 13 Nov: the clinical case used about 6,000
tokens in and 1,000 out (roughly $0.002), a single factual question about $0.001. Embeddings run locally on the CPU for
free. The server is an Oracle Cloud VM at about $1 a day on trial credit, and it stops when the trial ends unless the
account is upgraded. Check the DeepSeek balance for the real number.

**What does the ontology add over plain retrieval?** It adds structure the passages do not have. Certified facts (first-line
drugs, confirmatory tests, contraindications) go into clinical answers with a quote and a citation, and that is where the
"Warnings" line in step 2 comes from. It also powers Explore: backlinks, groupings, the cross-book "Books differ" view,
and the local graph. Plain retrieval can quote a paragraph but cannot say what points at a drug or where two books differ.

**What was the hardest failure?** A comparison question retrieved one side only, and a 3B local model wrote an unsupported
claim. Splitting the question fixed the first; moving to DeepSeek fixed the second (both are in `docs/failure_cases.md`).

---

## Pre-demo checklist

**The evening before (16 Nov)**
- [ ] Freeze: no deploys from now until after the demo. Note the commit hash currently live.
- [ ] Run each question in this script once on the live site and confirm the route pill and status pill match the table.
- [ ] Take backup screenshots: step 1 answer plus the open trace, step 2 warnings, step 6 (Rifampin page, Tuberculosis page,
  local graph with hubs), step 7 (the Books differ card). Save them in one folder and in slides as the last resort.
- [ ] Charge the laptop. Download the backup address page and check that it loads: https://130-210-60-153.sslip.io
- [ ] Confirm the offline fallback still starts (`LLM_BACKEND=ollama`, `OLLAMA_MODEL=qwen2.5:7b`). Do not rely on it for the
  vignette; its answers are weaker.

**The morning of (17 Nov)**
- [ ] Check the DeepSeek balance on the DeepSeek console. A full run of this script costs about $0.02. Top up if the balance
  is below $2.
- [ ] Check the Oracle VM is running, and check the trial credit has not run out (the VM stops when it does).
- [ ] Open https://mentor.medevolv.in in both tabs. Confirm the lock icon (HTTPS certificate valid).
- [ ] Warm up the site with a real question (for example the step 3 anatomy question). The first question after a restart
  takes about 12 s while the embedding model loads. Then run the step 1 vignette once so the whole path is warm, and
  click "Clear chat".
- [ ] Open the Explore tab and search Rifampin once, so the concept caches are warm.
- [ ] Test the room: Wi-Fi, projector, browser zoom. Have a phone hotspot ready.

**Five minutes before**
- [ ] Re-warm with one short question, then "Clear chat".
- [ ] Sidebar: Multi-hop reasoning is ON.
- [ ] Notes file with the pasted questions is open. Screenshots folder is open in another window.

**Do not**
- Do not deploy, push, re-index or edit `.env` on demo day.
- Do not paste an API key anywhere on screen. Keep the terminal and `.env` closed during the demo.
- Do not click the "Second-line anti-tubercular agents" chip.

---

## Verification log (13 Nov, local code, DeepSeek `deepseek-chat`)

Each question run twice or more through `rag.answer.answer_multihop`. "Latency" is wall time for the full answer on this
Mac; the first call after starting Python includes about 5 s of embedding-model load, and the live VM has 1 CPU, so expect
the live site to be a little slower. Cited books are the books of the passages the answer cited. A prior run in the same
process is "warm".

| Step | Question (short) | Route | Status | Cited books | Latency |
|---|---|---|---|---|---|
| 1 | Right ventricular infarction vignette (64 words) | case, three axes | answered | Harrison, Davidson; Tripathi on about half the runs | 7.6 to 13.7 s (6 runs) |
| 1 fb | Diabetic ketoacidosis vignette | case, three axes | answered | Davidson, Harrison, Robbins, Guyton, Tripathi | 8.4 to 9.1 s (4 runs) |
| 2 | Wheeze and breathlessness: first-line drug class and drugs to avoid | graph | answered | Tripathi, Harrison, Davidson | 2.4 to 8.0 s (6 runs) |
| 2 fb | Wheeze, breathlessness, cough at night: drug treatment | graph | answered | Tripathi, Harrison, Davidson | 3.3 to 7.7 s (4 runs) |
| 3 | Femoral triangle boundaries and contents | single | answered | Gray's only | 2.1 s warm, 6.7 s cold (3 runs) |
| 3 fb | Rotator cuff muscles and nerve supply | single | answered | Gray's only | 1.4 to 6.1 s (3 runs) |
| 4 | Compare penicillins and aminoglycosides | decompose | answered | Tripathi; Harrison on some runs | 4.7 to 10.3 s (4 runs) |
| 4 fb | Compare type 1 and type 2 diabetes | decompose | answered | Harrison, Davidson, Robbins | 3.9 to 5.0 s (3 runs) |
| 5a | My mother has TB, how much rifampicin | none (guard) | personal_refusal | none | 0.0 s (3 runs) |
| 5b | Who won the 2011 cricket world cup | single | not_in_sources (best match 0.53) | none | 0.1 s warm, 4.7 s cold (3 runs) |
| 5c | Best way to learn pharmacology quickly | single | insufficient (best match 0.73) | none | 0.7 to 1.0 s (3 runs) |
| 6 | Explore: Rifampin, Tuberculosis, Antibiotics hub, local graph | no model call | n/a | n/a | clicked through on the live site |
| 7 | Explore: Rheumatoid arthritis, Books differ | no model call | n/a | n/a | clicked through on the live site |

Cost of this verification: about 80 answers at roughly $0.001 to $0.002, so about $0.15 in total.

## Notes for the team (delete before presenting)

- **Step 2 is not a pure factual question.** Warning lines only exist on the graph and case routes; a factual question
  takes the single route with no ontology step. Step 2 is therefore a short drug question about a patient.
- **The handbook demo section is out of date.** `docs/master.html` section 13 is a 5-minute script, and sections 1 to 3 still say
  six books and 2,062 sections. The app now has seven books (Harrison and Gray's added), 2,611 sections and 35,902 passages.
  Section 11 still lists the TB and measles vignettes as open; TB now ranks first. This script follows the app.
- **Answers are not deterministic.** The wording and which books are cited vary slightly between runs. The route, status
  and the points to look at were stable across all runs above.
- **Placeholders to fill after the eval refresh:** `{{EVAL_STATUS}}`, `{{EVAL_CITED}}`, `{{EVAL_JUDGE}}`, `{{EVAL_P50}}`,
  `{{EVAL_P95}}`, `{{EVAL_RETRIEVAL_CH1}}`.
- **Possible live-versus-local difference:** the live Explore tab shows 5,001 conditions and 25,902 certified facts. The local
  ontology file is still being edited, so numbers on the Explore tab can differ from local runs. Quote the numbers shown
  on the live site.
