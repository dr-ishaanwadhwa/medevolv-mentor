# MedEvolv Mentor: strategy review

*Date: 14 Nov 2026 (written 15 Nov). Audience: the founding team first, then the professor and any investor. Status: internal draft, not committed.*

This review combines three independent reviews ("lenses") with a market model that went through four rounds of hostile checking:

- **ask-matt**: an engineering-process and product-design lens.
- **chief-of-staff**: an operations, environment and accountability lens.
- **SuperMe**: answers from 13 real practitioners in edtech, growth and health. This lens **was available and worked**. None of the practitioners has sold to Indian medical students, and every one of them said they had no real Indian conversion or customer-acquisition numbers.

All rupee figures are estimates built from the sources in Section 8 unless marked as reported. "Cr" means crore (10 million). "Lakh" means 100,000.

---

## Decision brief (one page; read this first)

**Recommendation: GO, as a research pilot. NO-GO on selling to anyone until two gates pass.** The engine is worth
continuing; the business is not yet proven, and nothing below claims it is.

**The two gates (both must pass before any paid or public offer)**
| Gate | Passes when | Today |
|---|---|---|
| Content rights | A licence, a college e-library route or an open corpus is chosen and started | Not started; textbooks are private copies |
| Answer safety | The 18-case clinician review shows **no "major"** case | 12 of 18 "major" |

**What is measured vs what is assumed**
| Kind | Numbers | Status |
|---|---|---|
| Measured by us (internal) | 39/39 right behaviour, 30/30 answers fully grounded, ~3 s per answer, 12/18 hard cases "major", cost of cents a day | Measured, not externally audited |
| Measured by others (sourced) | Seats and exam headcounts, Marrow and PrepLadder revenue, competitor prices, free-AI offers, AI use among MBBS students | Sourced; see "Source check" in Section 8 |
| **Assumed, never measured** | Reach-to-install 25%, install-to-paid 1.0%, ambassadors per college, colleges reached | **These decide the SOM.** The year-1 and year-3 payer counts (about 19 and 71) are what the funnel gives *if* those guesses hold; the plausible band is about 10 to 600 payers in year 3 (Section 5.4). Treat them as a hypothesis the pilot will test, not a forecast. |

**What would change the decision:** the pilot's measured funnel (Section 5.4, "measure these"), and whether any
publisher or college conversation reaches a second meeting (Section 7 kill criteria).

**Decision rules after the demo (what each answer triggers)**
| If the professor... | Then | If not |
|---|---|---|
| names a reviewer | Send the faculty sheet the same day; the 9 gold questions get verified and the gold numbers stop being provisional | Ask two PG residents directly; keep the gold numbers labelled provisional |
| allows a one-batch pilot | Week 2: password-gated build, accounts, daily caps, consented logs; start 4-6 weeks before that batch's exam | Run the pilot with 20-30 friends in our own batch, unpaid; report the same funnel metrics |
| introduces the librarian | Ask which textbooks the college already licenses digitally; that list decides the content-rights path (run over licensed content) | Default rights path: open/government corpus (STGs, NLEM, ICMR, WHO, OpenStax) for anything public |

Rights path rule: pick the first that is available by 23 Nov, in this order: (1) the college's licensed e-library,
(2) a narrow licence for one book from a non-Elsevier publisher, (3) the open corpus. Whatever is chosen, nothing is
sold until the safety gate also passes.

**First week (17-23 Nov)**
| Owner | Action | By | Ready-to-use material |
|---|---|---|---|
| Founder | Run the demo unchanged; make the three asks (reviewer, one-batch pilot, librarian intro) | 17 Nov | `docs/demo_script.md`; asks in `docs/gtm/01_demo_followup_email.md` |
| Founder | Send the follow-up email to the professor | 18 Nov | `docs/gtm/01_demo_followup_email.md` |
| Team | Send the student questionnaire to 15-20 students; the faculty sheet to the reviewer | 20 Nov | `docs/gtm/02_student_questionnaire.md`, `docs/gtm/03_faculty_questionnaire.md` |
| Founder (decision) | Put the public site behind a password, after the demo | 18 Nov | `docs/gtm/04_regate_site.md` (exact steps) |
| Team | Write the one-page content-rights memo and pick a path | 23 Nov | Section 4, "Textbook licensing path" |

---

## 1. Executive summary

**The short version.** On our own internal tests (not externally reviewed), the engine behaves well: 39/39 right behaviour on a 39-question set of factual, comparison, off-topic and personal-advice questions, 30/30 answers fully grounded in their citations, about 3 seconds an answer, at a cost of cents a day. Those tests do not cover patient-specific safety, which is the second problem below. There are three problems:

- **Content rights.** We have no licence for the seven textbooks.
- **Safety.** In 12 of 18 hard cases, general drug advice still leaks into answers about a specific patient.
- **Selling direct to students is small.** On benchmark conversion rates, selling straight to students earns tens of thousands of rupees a year by year 3, not lakhs.

The one route to a real business that we found is to **borrow distribution**: a publisher licence or a college/consortium deal. That same deal also solves the rights problem. What we can actually sell is the **verification layer** (cite or decline, quote-verified facts, the adversarial safety harness). The chatbot is not the asset.

### Next 30 days (to mid-December 2026)

1. **17 Nov demo: change nothing.** The freeze holds. Treat the demo as the first sales call. Ask for three things: (a) a faculty or clinician reviewer for the 9 unverified gold questions, (b) permission to pilot with one batch, and (c) an introduction to the college librarian or e-library committee.
2. **Put the public site back behind a password** (APP_PASSWORD is already wired up; it was removed on 12 Nov). Stop showing textbook excerpts publicly. This takes minutes and lowers the biggest risk straight away.
3. **Turn discipline into checks.** Add a CI job and a pre-commit hook that run pytest (including `test_deploy_imports.py` and `test_headings_leak.py`). Make `make deploy` the only way to reach the VM, and have it require a clean tree, no `data/` staged, and a 39-question eval gate (about $0.10). Write ADRs for decisions already made: STAIR dropped, DRUG_CHECK off, two trust tiers. Add a GLOSSARY.md. *(Checked: the repo has no `.github/`, no CI, no hooks, no ADRs.)*
4. **Write the content-rights decision as a one-page memo** with three options: a publisher licence (non-Elsevier first), running over a college's already-licensed e-library, or an open/government corpus (STGs, NLEM, ICMR, WHO, OpenStax A&P). Pick one path to pursue first.
5. **Send two questionnaires.** One goes to faculty, to settle the 9 gold items and rate h01, h05, h08 and h10. The other goes to 15-20 MBBS students, from 2nd year to interns, about what they study from, what they pay for, and whether they would pay Rs 199-499 for cited answers.

### Next 90 days (to mid-February 2027)

1. **Fix the patient-specific drug-advice leak as a redesign, not a prompt patch.** Build one `review(answer, patient_findings) -> SafetyNotes` module that *flags* problems in a separate block and never rewrites the answer. Make the 18-case clinician A/B a release gate: no case rated "major" and no regression in pharmacology recall.
2. **Run a gated pilot at one college with 150-500 students**, timed to that university's professional exam. Add accounts, daily caps, consented and anonymised logs, and a one-tap "wrong citation" flag. Measure reach per ambassador post, reach-to-install, install-to-paid, weekly active use and 4-week retention.
3. **Open one publisher conversation** (Thieme, CBS or McGraw Hill India) and one college e-library conversation, using the eval evidence. Offer the verification layer, not the app.
4. **Freeze v2, the 3D atlas and graph expansion** until pilot data shows repeat use.
5. **At the 90-day mark, decide go/no-go on hard numbers** (Section 7).

---

## 2. How to improve the system

All three lenses' lists are merged, duplicates removed, and the result ordered by priority. Lens tags: **[M]** ask-matt, **[C]** chief-of-staff, **[S]** SuperMe.

### A. Quality and safety (do first)

| # | Improvement | Lenses | Effort |
|---|---|---|---|
| A1 | **Redesign the patient-specific safety check.** Use one deep module, `review(answer, patient_findings) -> SafetyNotes`, which holds drug recognition, negation scope, contraindication-only rules, an indication allow-list and a damage gate. It *flags* problems and never edits the answer text. Each failure example in `docs/drug_check_ab.md` becomes a failing unit test first: "Stop digoxin" is not a recommendation; insulin is never ruled out in DKA; "urea" in "urea breath test" is not a drug. Write wrong doses, invented findings and omissions into the spec as **out of scope** for the checker. | M, C, S | 1-2 weeks |
| A2 | **Make the 18-case clinician review a release gate.** Block a deploy if any case is "major" or pharmacology-axis recall drops below the 72% baseline. Codify the A/B rule: no env flag (DRUG_CHECK, GRAPH_WALK, FIRST_LINE_CAVEAT, EXPERIMENTAL) is switched on unless its A/B shows no severity regression and groundedness of at least 0.975. | M, C | 1 day once A1 exists |
| A3 | **Finish verifying the 9 of 15 gold questions** and recruit 2-3 faculty or PG residents as a standing review panel, so the product can say "reviewed by Dept of X". | M, C | 1 day to ask; 1-2 weeks to get answers |
| A4 | **Audit real answers, not demo answers.** Two senior students check 50 real wrong-answer reviews and shared answer cards. They check that the edition and page support each claim and that refusals fire when they should. Log the error rate next to the payment funnel. | S | ongoing |
| A5 | **Measure retrieval for every book we claim.** Today only Tripathi (76.5% chapter@1) and Davidson (78.4%) have retrieval sets. Build validation sets for Gray's, Guyton, Robbins, Harrison and micro, and fix the Erb's-palsy-type anatomy gaps. | M | 2-4 days |

### B. Product

| # | Improvement | Lenses | Effort |
|---|---|---|---|
| B1 | **A "Why was my answer wrong?" flow as the main feature.** The student pastes a question and the option they chose. They get a short verdict with the exact edition and page, or an honest "the books don't settle this". | S (with C's exam-workflow point) | S-M |
| B2 | **A study loop built on citations.** Long-answer and short-note drafts in professional-exam format, viva questions generated from the cited page, MCQs and spaced-repetition cards from cited passages, and a Hinglish toggle. | C, M (viva drills) | M |
| B3 | **Accounts, metering and cost tracking.** 5-10 free answers a day, then a capped paid tier. Log AI cost per active student and ask for the exam date at sign-up. At about $0.0025 an answer, an uncapped user asking 300 answers a month costs about $0.75, or about Rs 65 a month at about Rs 88/$. | C, S | S-M |
| B4 | **Shareable answer cards with a trackable link** that show edition and page and contain no copied textbook or QBank text. Add a free, searchable library of audited topics, each with a "submit your question" prompt. | S | M |
| B5 | **The ability to drop a source.** Keep a rights record per source (ingest / retrieve / quote / display), tag every answer with its source version, never train on the books, and prove that one book can be removed cleanly from the index, cache and logs. Log unanswered questions by book as evidence to show a publisher. | S, C | M |
| B6 | **Keep the 3D atlas and concept graph browse-only and frozen.** All three lenses agree they make a good demo but do not drive purchases. Atlas stage 1 waits as a decision ticket. | M, C, S | decision |

### C. Engineering environment

| # | Improvement | Lenses | Effort |
|---|---|---|---|
| C1 | **Guardrails:** CI plus a pre-commit hook running pytest; `make deploy` as the only way to deploy (clean tree, no `data/`, eval gate). Add CODING_STANDARDS.md ("every answer path goes through the citation/decline schema; no raw LLM text reaches the UI") with a lint check for it. | M, C | 1 day |
| C2 | **Write down how we work:** run `/retro`, then `/setup-matt-pocock-skills`. Add ADRs for STAIR, DRUG_CHECK, the two trust tiers and the demo freeze. Add GLOSSARY.md, built with `/grill-with-docs`, for "patient-scoped recommendation", "general list", "contraindication (certified)", "Avoid line" and "trap". | M | 0.5-1 day |
| C3 | **A team wiki and schedules** (proposed: `~/Projects/med-rag-wiki`, kept separate from the Sensorium wiki). Schedules: a weekly eval regression run (about $0.35), a nightly uptime and DeepSeek-spend check, a monthly refresh of market data and prices, and an exam-calendar reminder 6 weeks before each target college's exams. | C | S |
| C4 | **Simplify the hot spots** with `/improve-codebase-architecture`: `app.py` (1,284 lines), `rag/hops.py` (650), `rag/headings.py` (765), and about 30 `getenv` flags. Collapse the flags into one config seam. For each flag that is always off, either ship it or delete it. | M | 3-5 days |
| C5 | **Sustainable hosting.** Move off the OCI E5.Flex trial credit to Always-Free A1 or a budgeted small VM. Add uptime and cost alerts, and keep the qwen2.5:7b/Ollama fallback tested. Note that DeepSeek is a China-based provider, which colleges' procurement reviews will ask about. | C | S |
| C6 | **Use `/wayfinder` to plan after the demo.** Blocking decision tickets, in order: content rights, then wedge, then channel, then pricing, then clinical-safety scope. Hand off to `/to-spec` only once the decisions are clear. | M | 3-6 sessions |

---

## 3. Positioning

**One-line positioning statement**

> **Your MBBS textbooks, answering back: every answer cites the book, chapter and page you're examined on, and it says "the books don't settle this" when they don't.**

*Use this line only once the content rights are settled (licence, college e-library or open corpus). Until then, the external framing is "a cite-or-decline research pilot" (see What NOT to claim).*

**Target user.** Indian MBBS students in phases 1-3 (years 1 to 4.5) and interns who study for **university professional exams and vivas** from the standard texts: Tripathi, Guyton, Robbins, Davidson/Harrison and Gray's. A later segment is NEET-PG aspirants who want a textbook verdict on QBank answers they got wrong.

**Where it sits.**
- *Next to* Marrow, PrepLadder and DigiONE, not against them. Marrow takes about Rs 564 cr a year in subscriptions, has Rs 1,756 cr in cash and dominates PG exam prep.
- *Better than* free general AI (ChatGPT Go, and Google AI Pro free through Jio) on **verifiability**. It gives page citations, refuses when evidence is weak, and has a measured internal eval (39/39 right behaviour, 30/30 fully grounded; not yet externally published or audited). A free chatbot cannot make that measured claim.

**The defensible wedge.** The wedge is the **verification discipline**, not answering from retrieved text, which anyone can build. It consists of:
- cite-or-decline;
- a quote-verified ontology (about 26k facts at about 95% precision; internal figure, not re-audited for this review);
- an adversarial clinician A/B with a written failure taxonomy;
- fit to Indian university curricula.

This layer does not depend on a particular corpus. It can run over any library a college or publisher is entitled to use. Elsevier, Jaypee and Marrow have content and cash, but none of them has published a grounding harness like this.

**What NOT to claim**
- **Not "the world's first AI-native 3D clinical reasoning companion."** That phrase comes from the Gemini document (`med-rag-v2/docs/research/market_competitor_analysis.md`, lines 20 and 390), and it is false:
  - Elsevier's Osmosis AI (Mar 2026) gives cited answers from Elsevier sources.
  - ClinicalKey Student has StudyFinder AI (Jun 2026).
  - Jaypee's DigiNerve runs the "Dr. Wise" chatbot (Jan 2025).
  - Complete Anatomy and Kenhub already offer 3D.
- **Not the "~$50M" Complete Anatomy acquisition price.** The Gemini document gives no source for it.
- **Not clinical decision support.** Until the patient-scoped safety gate passes, frame vignettes as exam practice ("how Harrison approaches this case"), not advice about a patient.
- **Not "trusted textbook answers" in public or paid channels** until the content rights are settled. Until then, describe it as a research or institutional pilot.
- **No quality claims beyond what we have measured.** Only 2 of the 7 books have retrieval metrics, and the 15/15 gold result is provisional.
- **Not the Gemini document's USD pricing grid.** It has nothing to do with what Indian students will pay.

---

## 4. Go-to-market strategy

### Channels, in order of use

1. **The faculty sponsor at our own college** (from the demo), leading to a single-batch pilot.
2. **Campus ambassadors**: 1-2 per college, paid in credits or a small stipend, posting in batch WhatsApp and Telegram groups. An ambassador realistically reaches their own batch and one neighbouring batch (about 140-170 students each), not the whole college.
3. **Shareable cited-answer cards** plus a free audited topic library (an organic loop; SuperMe). Test the loop by pausing ambassador invites for one week and counting the sign-ups and payments that still arrive.
4. **Publisher track, running in parallel.** Approach Thieme (already licensed through NML-ERMED to 58 institutions), CBS and McGraw Hill India first. Treat Elsevier (which owns 4 of our 7 books) and Jaypee (>50% of Indian UG textbooks, unsourced; running DigiNerve) as **competitors first**. Approach them only with a verification-layer or white-label offer.
5. **Institutional, only after rights are settled:** the college Medical Education Unit or library, pitched as an NMC-aligned e-library resource with a faculty dashboard. Colleges buy through NML-ERMED/ONOS consortia, and procurement will ask about content rights first.
6. **Avoid paid performance marketing.** It costs an estimated Rs 1,500-4,000 per paying user (agency estimate, low confidence; upgrowth.in in Section 8) against a ticket of Rs 499-1,499, so it can never pay back.

### Pricing and packaging

| Tier | Price | What's in it |
|---|---|---|
| Free | Rs 0 | 5-10 cited answers a day, the topic library, shared cards |
| Exam pass | Rs 499 (Y1) to Rs 599 (Y3), about 3 months around a professional exam | Unlimited "why was I wrong", viva drills, short-note drafts |
| Annual (per prof year) | Rs 1,499 | Everything above, plus vignette practice mode, Anki/Obsidian export, and the atlas link |
| Institutional | Rs 1-3 lakh per college per year (unsourced; only after rights) | Site licence and faculty dashboard |

Why these prices:
- The direct competitor, DigiONE, costs about Rs 3,374 (sale) or Rs 4,499 (list) **per prof year**, and covers first prof only. Our annual tier sits clearly below it.
- PW's blended online collection is Rs 3,683 per paying user.
- The binding substitute is **free** (ChatGPT Go, Google AI Pro via Jio). So price is not the constraint; conversion is.
- Use passes rather than subscriptions, because students buy for a specific exam.
- Use web/UPI checkout to avoid 15% app-store fees. Below Rs 20 lakh turnover, no GST registration is needed.

Pilot test (SuperMe): run a 2x2, with NEET-PG QBank users vs 2nd-year pathology students, at Rs 199 vs Rs 299 a month. Each student sees one price. The decision metric is revenue after AI cost per student who asks a first question.

### The first 1,000 users plan

- **0 to 100 users:** our own batch, through the faculty sponsor. Two volunteers each demo one real wrong QBank answer in their study group, and classmates get 5 free cited reviews. Track the funnel: demo, then link opened, then first question, then second question within 7 days, then payment.
- **100 to 500 users:** 2-3 nearby colleges with 2 ambassadors each, timed 4-6 weeks before their professional exams.
- **500 to 1,000 users:** publish the audited library of the most common wrong-answer topics, drop topics that bring readers who never ask a question, and run the one-week organic-loop test.
- **The honest arithmetic:**
  - 1,000 *users* (signed up) is reachable from about 5,000-15,000 reached students, which means about 15-50 colleges at about 300 reached per college (2 ambassadors × 160 × 0.95).
  - 1,000 *payers* is not reachable this way. At benchmark conversion rates it would need about 70,000-140,000 installs.
  - Valerie Wagoner (SuperMe) corrected her own funnel: a 2.5% end-to-end rate would need 40,000 users to get 1,000 payers.

### B2B / institutional path

1. Get a faculty sponsor and run a free pilot in one department.
2. Produce a report on the pilot's measured learning outcome.
3. Present it to the MEU or library committee, with a **named budget owner, a faculty lead using the tool in a course, a defined cohort and a fixed review date** (SuperMe: Jonathan Stull).
4. Sign a paid contract only if the college values that outcome. Otherwise keep the campus as free distribution.
5. Later, sell through a consortium (an RGUHS-style arrangement: Elsevier describes a partnership giving ClinicalKey Student plus Complete Anatomy to RGUHS's 55 medical colleges in one arrangement; no price is published).
6. Best route through the licensing problem: **run the verification layer over content the college already licenses**.

### Textbook licensing path

1. **Now:** a private-use, login-gated research build. Show no public excerpts.
2. **Make the product able to drop a source** (B5). This turns a takedown from a threat to the whole product into a routine operation.
3. **Ask for a narrow licence:** one book or one specialty, covering ingest, retrieval, generated answers, short quotes and citations. Make it removable and set a walk-away date. Bring usage data (unanswered questions by book) and the eval harness as evidence.
4. **Precedent:** Wiley made $40M from AI licensing in FY25. Publishers do license for AI, but on their own terms.
5. **Fallback:** an open or government corpus (STGs, NLEM, NTEP, ICMR, WHO, OpenStax A&P under CC BY). The product would be weaker but legal to sell.

### 90-day plan

| Weeks | Product / engineering | GTM / market | Exit check |
|---|---|---|---|
| 1 (17-23 Nov) | Demo as frozen. Re-gate the site. Run `/retro`. | Make the 3 demo asks. Send both questionnaires. | A sponsor named? |
| 2-3 | CI, hooks, `make deploy` and eval gate. ADRs and GLOSSARY. | Write the rights memo and pick a path. Draft the publisher one-pager. | CI is green and blocks a bad deploy |
| 4-6 | Safety module spec, red tests, then the build. Accounts, caps, logs, flag button. | Get answers back on the 9 gold items. Map exam calendars for 10 colleges. | Gold set verified |
| 7-9 | Run the 18-case A/B on the new module. "Why was I wrong" flow. | Start the pilot with 150-500 students. Recruit 2 ambassadors. First publisher meeting. | Safety gate: 0 "major" |
| 10-12 | Fix from the logs. Answer cards plus library v0. | Run the 2x2 price test, the one-week organic pause, and the classroom "what do you already pay for" survey. | Go/no-go (Section 7) |
| 13 | Decision memo | Pilot report sent to the faculty sponsor and the publisher | Decide on scale, pivot to B2B/publisher, or stop selling to students |

---

## 5. Market sizing

### 5.1 Summary table

| Level | Value | Basis |
|---|---|---|
| **TAM** | **Rs 303 cr / yr gross** (about Rs 257 cr net of GST; range about Rs 300-315 cr) | About 823k unique potential users: about 566k MBBS students in college, 87k interns, about 140k non-intern NEET-PG takers and about 30k unique FMGE takers, × Rs 3,683 (PW's blended online collection per paying user). The 140k non-intern NEET-PG and 30k FMGE figures are derived from assumptions #5-6 (de-duplication is a team assumption). The incumbent wallet is about Rs 755 cr (Marrow Rs 641 cr operating revenue, of which about Rs 564 cr is subscriptions, plus PrepLadder Rs 114.6 cr; about Rs 679 cr counting subscriptions only), so TAM is about 40-45% of that wallet. |
| **SAM** | **Rs 13 cr / yr net** (range Rs 8-25 cr) | About 653k in-college students and interns × about 20% already paying for a study app (range 15-30%) = about 131k payers, × about Rs 1,200 a year spent on a supplement (about 35% of DigiONE's Rs 3,374 sale price; the 35% is a TEAM ASSUMPTION) = about Rs 15.7 cr gross, about Rs 13.3 cr net of 18% GST. PG and FMGE are excluded. |
| **SOM Y1** (late 2026 to 2027) | **About 13-27 payers, Rs 0.1-0.2 lakh** (base about 19 payers, about Rs 14k) | Iteration 5 (below). This is a measurement pilot, not a revenue line. |
| **SOM Y3** (2029) | **About 50-100 payers, Rs 0.4-0.8 lakh** (base about 71 payers, about Rs 60k) | Iteration 5 (below). |
| SOM Y3, bull | About 600 payers, about Rs 6.6-8 lakh | All bull levers combined, plus one institutional licence |
| SOM with a publisher or consortium deal | About Rs 0.3-1 cr | Unsourced. Depends entirely on borrowed distribution. |
| **Hard gate** | **Rs 0 commercial SOM** | Applies until the corpus is licensed or replaced with open content |

### 5.2 Iteration history: how the numbers moved and why

| Iteration | Y3 payers | Y3 revenue | What changed |
|---|---|---|---|
| Lens estimates (before the model) | ask-matt 1,250-2,500; chief-of-staff 600-1,000; SuperMe 2,000-3,000 | Rs 15-50 lakh | Assumed 3-20% paid conversion and 30-35% sign-up, borrowed from Indian edtech rules of thumb |
| Iteration 1 (first model) | about 1,200 | about Rs 26 lakh "ARR" | Bottom-up by college; included about 530 NEET-PG add-on payers |
| Critic round 1, 10 challenges | about 280 | lower | Removed the PG add-on, which contradicted the SAM. Cut conversion from 4% to 1-2%, because 4% is about 2x the India/SEA top quartile. Re-anchored ARPU to DigiONE. Reach became per batch (about 170) rather than per college (706). Added churn and seasonality. |
| Critic round 2, 9 challenges | about 90 | about Rs 72k net | Cut activation from 25-30% to 12.5%. Corrected the renewal citation. Replaced ARR with recognised pass revenue. Named Gemini/Jio as the binding free substitute. Reduced organic to 2,000. Set PG to 0. |
| Critic round 3, 11 challenges, giving **Iteration 4** (the final model supplied to this review) | **about 22** | **about Rs 17.7k** | Conversion 1.5% to 0.7% (India/SEA median by *user* geography). Activation 12.5% to 6.5%. 40% ambassador churn and 25% organic overlap. Repeat payers netted out instead of added. 1.0 pass a year. GST removed (below the Rs 20 lakh threshold). SAM rebuilt from Rs 29 cr to Rs 13 cr. |
| Critic round 4, 8 challenges, giving **Iteration 5** (applied in this review) | **about 71 (range 48-98)** | **about Rs 60k (range Rs 41-83k)** | See below. |

**Why Iteration 5 exists.** The fourth critic round found a **category error in Iteration 4**. Iteration 4 used 6.5% as the *reach-to-install* rate, but 6.5% is RevenueCat's *download-to-trial* rate, which applies only after a student has already installed. It then multiplied that by 0.7%, a *download-to-paid* rate. So two after-install rates were chained together, and one of them was being used as a before-install rate. That made the funnel about 2-3x too pessimistic.

This review applies that critic's coherent funnel (A):
- **Reach-to-install: 25%.** This is a team assumption, plausible for a free tool a classmate pushes into a batch group, and to be measured in the pilot.
- **Install-to-paid: 1.0% base**, with 0.7% as the all-category India/SEA floor and 1.4% as the upper end. Education outperforms the all-category median, and an exam-deadline pass is a higher-intent purchase.
- **Supplementary exams count as a second purchase occasion.** NMC CBME 2023 requires them within weeks of results, so pass buyers average 1.1 passes a year.
- **The Razorpay fee is 2.36% in all years.** The new-merchant 0% window probably lapses before the first exam window.

Iteration 5 arithmetic:
- **Y3:**
  - College reach: 21,280 (70 effective colleges × 320 × 0.95). The 70 is 80 nominal colleges after ambassador churn: 80 × (1 − 40% churn × 30% of a year uncovered) = 70.4. The 30% uncovered share is a TEAM ASSUMPTION; the working is in `docs/evidence/som_recompute_output.txt`. 25% install gives 5,320.
  - Organic: 1,500 (2,000 less 25% overlap).
  - Total installs: about 6,820. At 1.0% that is about 68 new payers, plus about 3 repeat, so about **71 payers**.
  - Blended net revenue per payer: 75% × Rs 585 × 1.1, plus 25% × Rs 1,464, = about Rs 849. (Rs 585 and Rs 1,464 are Rs 599 and Rs 1,499 less the 2.36% gateway fee; the 75/25 pass/annual mix is a TEAM ASSUMPTION.)
  - Revenue: about **Rs 60k**.
  - Range: 0.7% conversion gives about 48 payers and Rs 41k; 1.4% gives about 98 payers and Rs 83k. (The low end counts new payers only, 6,820 × 0.7% = 47.7; with scaled repeats it is about 50.)
- **Y1:**
  - Installs: 6,080 × 25% = 1,520, plus about 375 organic, = about 1,895. At 1.0% that is about **19 payers**.
  - Blended net per payer: about Rs 722 (80% × Rs 487 × 1.1, plus 20% × Rs 1,464; the 80/20 mix is a TEAM ASSUMPTION).
  - Revenue: about **Rs 14k**. Range: 13-27 payers.
- **The other reading of "activated".** If "activated" means trial-starters and we apply India/SEA trial-to-paid (15.2%), Y3 would be about 440 payers. We do **not** use this as the base, because we have no trial mechanic. It sits near the bull case.

**Why the numbers fell so far from the lens estimates.** The lenses used conversion rates of 3-20% from blogs and rules of thumb. The benchmark medians (RevenueCat 2026) are 5-30x lower. Every correction moved the numbers down except two: the GST removal (+17-18%) and the Iteration 5 funnel repair (about +3x from Iteration 4). The conclusion did not change at any step: **selling directly to students is a validation pilot, not a business.**

### 5.3 Assumptions

| # | Assumption | Value | Confidence | Source |
|---|---|---|---|---|
| 1 | MBBS seats 2026-27 (NMC revised matrix, excluding INIs) | 140,664 seats; 839 colleges (447 govt / 392 private) | medium | https://news.careers360.com/nmc-revises-mbbs-seat-matrix-adds-13636-mbbs-seats-cross-1-40-lakhs-neet-ug-counselling-2026-admission |
| 2 | MBBS seats and colleges (Lok Sabha, Jul 2026) | 139,489; 844 colleges | high | https://medicaldialogues.in/amp/news/education/139489-mbbs-86360-pg-844-medical-colleges-in-india-mos-health-175751 |
| 3 | Back-calculated cohorts (DERIVED) | 2022-23 about 99,463; 2023-24 about 109,115; 2024-25 about 117,756; 2025-26 128,875 | low | https://medicaldialogues.in/amp/news/education/48563-mbbs-seats-added-in-last-6-years-mos-health-tells-parliament-165138 |
| 4 | Occupancy as a stand-in for enrolment (TEAM ASSUMPTION) | 0.95, giving about 566k in college and about 87k interns | low | same as #2 (enrolment is not published) |
| 5 | NEET-PG 2026 appeared (TAM only) | 265,980 | medium | https://www.pw.live/news/neet-pg-2026-candidates-appeared-attendance-centres-re-exam-result-date |
| 6 | FMGE repeaters | 88% in June 2026, so about 30k unique | medium | https://medicaldialogues.in/news/education/88-percent-fmge-june-2026-candidates-were-repeaters-freshers-had-35-percent-pass-rate-govt-176210 |
| 7 | Marrow (DailyRounds) FY25 | Rs 641 cr operating revenue; about Rs 564 cr from subscriptions; Rs 1,756 cr cash | high | https://entrackr.com/fintrackr/dailyrounds-delivers-rs-363-cr-profit-on-rs-641-cr-revenue-in-fy25-11110021 |
| 8 | PrepLadder FY25 | Rs 114.6 cr | medium | https://inc42.com/company/prepladder/financials/ |
| 9 | Share of in-college students paying for study apps | about 20% (15-30%). Anecdotal plus derived. Marrow's official 12-month prices (Rs 18,999 / Rs 37,999) imply about 2.3-3.8 lakh purchases, mostly NEET-PG aspirants | low | https://www.decodeinternet.in/decode/indias-future-doctors-pay-colleges-for-degree-and-apps-for-education-29593 ; https://www.marrow.com/pro |
| 10 | Direct competitor price per prof year: DigiONE (first prof only) | Rs 4,499 list / about Rs 3,374 sale | medium | https://www.diginerve.com/courses/undergrad/digione/ |
| 11 | PW online average collection per paying user (blended; not a ceiling) | Rs 3,683 FY25 (about Rs 4,104 FY26) | high | https://investmentbank.kotak.com/kib-cms/sites/default/files/offer-documets/Physicswallah%20Limited%20-%20BoA_.pdf |
| 12 | GST registration exemption | None needed below Rs 20 lakh aggregate turnover (inter-state services) | medium | https://taxheal.com/notification-no-102017-integrated-tax.html |
| 13 | Payment gateway fee | 2.36% (2% plus GST, UPI included); 0% only for new merchants for 90 days or Rs 5 lakh GMV | medium | https://razorpay.com/blog/razorpay-payment-gateway-pricing-explained/ ; https://razorpay.com/blog/razorpay-0-percent-platform-fee-offer-90-days-new-merchants-2026/ |
| 14 | Install-to-paid (PROXY) | 1.0% base; 0.7% floor (India/SEA D35 median by user geography, all categories); 1.4-1.9% upside; India/SEA trial-to-paid 15.2% | medium (floor) / low (base) | https://www.revenuecat.com/state-of-subscription-apps-2026-education |
| 15 | Reach-to-install (TEAM ASSUMPTION, Iteration 5) | 25% base (20-25%); 6.5% was the wrong metric (download-to-trial) | low | https://www.revenuecat.com/state-of-subscription-apps-2026-education (for what 6.5% actually measures) |
| 16 | Annual-plan renewal across prof years | about 47.5% (40-55%). Education has the *lowest* first-month annual cancellation (about 30%) | low | https://9to5mac.com/2026/05/27/new-report-shows-annual-app-subscribers-rarely-return-after-they-cancel/ |
| 17 | Passes per pass buyer per year | 1.1 (main plus supplementary exam) | medium | https://news.careers360.com/nmc-issues-cbme-regulation-2023-medical-colleges-granting-mbbs-admission-after-august-30-face-action/amp |
| 18 | Next-prof-year repurchase by pass buyers | about 22% (15-30%) | low | unsourced |
| 19 | Ambassador churn and organic overlap | 40% a year (30-50%); 25% overlap | low | team guess |
| 20 | Team reach and pricing | 20 / 50 / 80 colleges in Y1 / Y2 / Y3; 2 ambassadors × about 160 reach; organic 500 / 1,000 / 2,000; Rs 499 / 599 passes; Rs 1,499 annual | low | team guess |
| 21 | Free substitutes | ChatGPT Go free for 12 months for India sign-ups from 4 Nov 2025; Google AI Pro free for 18 months for Jio 5G users | medium | https://www.business-standard.com/technology/tech-news/openai-offers-chatgpt-go-free-for-one-year-in-india-125102800612_1.html ; https://www.smartprix.com/bytes/google-and-jio-team-up-to-offer-18-months-of-free-google-ai-pro-plan-in-india/ |
| 22 | AI use among MBBS students | 86% (one Mumbai college, n=385); 69.4% use it for exam prep | medium | https://ijmr.org.in/prevalence-utilisation-of-ai-chatbots-for-medical-education-among-students-of-medical-colleges/ |
| 23 | Institutional precedent (base case: 0 MedEvolv licences) | Elsevier ClinicalKey Student plus Complete Anatomy for RGUHS's 55 medical colleges (a "partnership"; no price published) | medium | https://www.elsevier.com/promotions/rguhs-hub |
| 24 | Publisher AI licensing benchmark | Wiley $40M FY25 | high | https://newsroom.wiley.com/press-releases/press-release-details/2025/Research-Growth-AI-Licensing-and-Cost-Reduction-Drive-Wileys-Fiscal-2025-Results/default.aspx |

### 5.4 Sensitivity (Y3, Iteration 5 base about 71 payers / about Rs 60k; one lever changed at a time)

| Lever | Low | Base | High | Effect on payers |
|---|---|---|---|---|
| Install-to-paid | 0.7% | 1.0% | 1.4% (1.9%) | 48 / 71 / 98 (133) |
| Reach-to-install | 12.5% | 25% | 35% | about 45 / 71 / 92 |
| Colleges (nominal) | 40 | 80 | 150 | about 45 / 71 / 115 |
| Ambassadors per college | 1 | 2 | 4 | about 44 / 71 / 125 |
| Organic installs (net) | 750 | 1,500 | 3,750 | about 64 / 71 / 93 |
| Ambassador churn | 50% | 40% | 30% | about 67 / 71 / 75 |
| Annual price | Rs 1,499 | Rs 1,499 | Rs 1,999 | revenue +about 15% *if conversion holds*; it probably won't against free AI |
| Checkout | web/UPI | web/UPI | in-app (15% store fee) | revenue -about 13% |
| Repurchase rate | 15% | 22% | 30% | under ±1 payer |

**Combined cases**
- **Bear** (40 colleges, 1 ambassador each, 50% churn, 12.5% install, 0.7% conversion, 750 organic): about 10 payers (9.8 by the worksheet), about Rs 8-10k.
- **Bull** (150 colleges, 4 ambassadors, 30% install, 1.9% conversion, 5k organic, plus 50 PG payers and repeats): about 620 payers (618 by the worksheet: 136.5 effective colleges × 4 × 160 × 0.95 = 82,992 reach; × 30% + 5,000 organic = 29,898 installs; × 1.9% + 50 PG payers), about Rs 6.6 lakh, which implies about Rs 1,070 net per payer, above the base Rs 849 (a richer annual/PG mix; TEAM ASSUMPTION). With one institutional licence (about Rs 1.5 lakh, unsourced), about Rs 8 lakh. That is still under the Rs 20 lakh GST threshold.
- **Binary overlays:** no content licence means Rs 0. A publisher white-label or consortium deal gives about Rs 0.3-1 cr (unsourced).

**What dominates:** the two funnel rates (reach-to-install and install-to-paid), then the number of ambassadors. Price barely matters. **Measure these in the pilot:** reach per ambassador post, reach-to-install, install-to-paid within 35 days, the share of each batch already paying for Marrow or DigiONE, whether supplementary exams trigger a second purchase, and ambassador retention across semesters.

### 5.5 Top-down vs bottom-up reconciliation

- **Bottom-up (Iteration 5):** about 71 Y3 payers, which is 0.33% of the 21,280 students in college reach, or about 1% of installs.
- **Top-down share-of-SAM:**
  - 71 payers is about 0.05% of SAM payers (131k).
  - Rs 60k is about 0.05% of SAM revenue.
  - It is about 0.001% of the Rs 755 cr incumbent wallet.
- **Top-down prospect band (labelled as an assumption, not corroboration):** a 0.5-1% win rate over **all** 21.3k reached students, not only those already paying, gives about 105-210. The bottom-up figure sits below that band. The win rate was chosen by us, so this check cannot validate the bottom-up number. No public Indian medical-app user-to-payer disclosure exists that would make a real top-down check possible.
- **Against the lenses:** the lens base cases (600-3,000 payers, Rs 15-50 lakh) are about 8-40x above Iteration 5 on payers and about 25-80x on revenue. Even the bull case (about 600 payers, Rs 6.6-8 lakh) only touches the bottom of chief-of-staff's payer range (600-1,000) and stays below its revenue range (Rs 15-25 lakh).
- **Reconciled view:**
  - TAM (Rs 303 cr) and SAM (Rs 13 cr) are real money.
  - The direct-to-student SOM is limited by **distribution**, not by demand or price.
  - The gap between SAM and SOM (about 2,000x: Rs 13 cr vs Rs 60k, or 131k vs 71 payers) is the size of the distribution problem. Only a partner who already reaches colleges (a publisher or consortium) closes it.

### 5.6 SOM worksheet (generated by `docs/evidence/som_recompute.py`)

Every figure in 5.1-5.5 recomputed from the assumption table; inputs marked TEAM ASSUMPTION are guesses the pilot will measure.

```
TAM users                           823,000
TAM Rs cr                             303.1
SAM payers                          130,600
SAM gross Rs cr                       15.67
SAM net Rs cr                         13.28
Y3 reach                             21,280
Y3 installs                           6,820
Y3 payers                              71.2
Y3 net/payer Rs                       848.4
Y3 revenue Rs                        60,407
Y1 reach                              6,080
Y1 installs                           1,895
Y1 payers                              18.9
Y1 net/payer Rs                       721.5
Y1 revenue Rs                        13,672
Y3 payers @ 0.7%                       47.7
Y3 payers @ 1.4%                       95.5
SAM/SOM gap (revenue x)               2,199

# Worksheet: derivations
in-college students = 0.95 x 595,873 (5 cohorts) = 566,079
interns = 0.95 x ~92,000 (2021-22 cohort proxy) = 87,400
Y3 effective colleges = 80 x (1 - 0.40 x 0.30) = 70.4  (report uses 70)
bull: effective colleges 136.5; reach 82,992; installs 29,898; payers 618 (report: ~600)
bull revenue at report's Rs 6.6 lakh implies Rs 1,068 net per payer (base mix gives Rs 848)
bear: effective colleges 34.0; payers 9.8 (report: ~10-12)
```

---

## 6. Where the three lenses agree and disagree

### Agreement (all three)
- **Content rights come first.** Every commercial line is zero without them. Elsevier and Jaypee are licensors *and* competitors.
- **The 12/18 patient-specific drug-advice leak blocks any public growth.** One screenshot (for example, morphine in an RV infarct) could undo the trust positioning.
- **Position next to Marrow and PrepLadder, not against them.** Do not lead with "AI tutor" or "3D".
- **The Gemini "world's first" claim is false**, and the 3D atlas and graph do not drive purchases. Freeze v2 and atlas expansion.
- **Distribution is ambassador or community-led**, with a cheap free tier and caps, priced in the low hundreds to about Rs 2,000.
- **Willingness to pay is the biggest unknown.** A pilot has to replace the borrowed rates.

### Disagreement
| Topic | ask-matt | chief-of-staff | SuperMe |
|---|---|---|---|
| Wedge | University theory exams and vivas, years 1-4.5 | Same, phases 1-3 | The "why was my QBank answer wrong?" moment, which includes NEET-PG aspirants |
| When to recruit students | A free closed pilot right after the demo (private use) | A gated pilot after the site is re-gated | **Not until** the drug-advice fix, a 50-answer audit and a rights position are in place |
| Price shape | Rs 149/month or Rs 1,499-1,999/year | Rs 199/month or Rs 1,499-1,999/year | Rs 199-299 per 30 days; test with a 2x2 |
| Publisher stance | Approach all, including Jaypee and Elsevier, with a verification layer | Non-Elsevier first; treat Elsevier and Jaypee as competitors | A narrow, removable one-book licence with a walk-away date |
| SOM (Y3) | Rs 25-50 lakh; up to Rs 1.1 cr with institutions | Rs 15-25 lakh | about Rs 22 lakh; bull Rs 90 lakh-1 cr |
| Main improvement | Process: retro, CI, ADRs, wayfinder | Environment: wiki, schedules, `make deploy`, re-gate the site | Answer quality and the conversion loop |

**This review's resolution.**
- **Wedge:** use SuperMe's wedge (the "why was I wrong" moment) as the *feature*, and ask-matt and chief-of-staff's segment (university-exam students) as the *first cohort*.
- **Pilot timing:** follow chief-of-staff. Re-gate first, then run a small private pilot. SuperMe's safety gate must pass before anything public or paid.
- **Publishers:** follow chief-of-staff's order, using SuperMe's narrow-licence terms.
- **SOM:** all three lens SOMs are replaced by the model in Section 5, which is far lower.

### Distinctive insight of each lens
- **ask-matt:** *The asset is the verification harness, and right now it lives in prose.* The team's best habit, honestly rejecting changes that failed their tests, depends on people remembering it. There are no CI checks, hooks, ADRs or glossary. Turning that habit into deterministic gates makes the trust claim provable to a buyer, and lets it outlast graduation. After the demo, the next step is a *decision* map whose first blocking ticket is content rights, not a v2 build.
- **chief-of-staff:** *The binding constraint is the environment, not the model or the market.* An unlicensed corpus on a public site, safety only caught by manual review, and trial-credit hosting with hand-pushed deploys are all workarounds for missing process. Build a **corpus-agnostic** verification layer that can run over whatever library a college or a non-Elsevier publisher is entitled to use, and give it a wiki, schedules and data feeds.
- **SuperMe:** *The paid unit is the honest verdict on one wrong answer.* That verdict is a page or an explicit refusal; it is not the 3D atlas or an "AI tutor". The shareable citation card is both the growth loop and the biggest liability. Valerie Wagoner's self-correction shows that a volunteer channel at a 2.5% end-to-end rate needs 40,000 users for 1,000 payers. So test the organic loop (pause invites for a week) before adding colleges.

---

## 7. Risks and kill criteria

### Risks (most severe first)
1. **Copyright and licensing (existential).** Seven commercial textbooks are held as private copies, and excerpts were shown publicly from 12 Nov. Elsevier (4 of 7 books) and Jaypee (Tripathi) ship competing AI. *Mitigation:* re-gate now, build the ability to drop sources, take the narrow-licence or open-corpus path.
2. **Clinical safety and reputation.** 12/18 hard vignettes rated "major". The earlier automatic fix made it worse (major went from 12 to 15). *Mitigation:* the flag-only safety module plus the A/B gate. Frame vignettes as exam practice.
3. **Distribution does not scale.** On benchmark rates, Y3 is about 71 payers. Volunteers churn and graduate. *Mitigation:* borrowed distribution (publisher or consortium) and the organic-loop test.
4. **Free substitutes and unproven willingness to pay.** ChatGPT Go and Google AI Pro via Jio are free, and 86% of students already use chatbots. The India/SEA download-to-paid median is 0.7%.
5. **Incumbent response.** Marrow (Rs 1,756 cr cash) could ship cited answers quickly. Osmosis AI and DigiNerve already sell grounded AI.
6. **Team continuity.** A student team graduating, with knowledge in prose docs. *Mitigation:* the CI, ADR and wiki work.
7. **Vendor and hosting dependency.** One DeepSeek API (a China-based provider, which procurement will question), one OCI VM on trial credit, and one outage already.
8. **Measurement gaps.** Only 2/7 books have retrieval metrics, 9/15 gold items are unverified, and the anatomy smoke test was written by the team.
9. **Market-data fragility.** Enrolment is derived from seats. There is no willingness-to-pay data, and competitor prices mostly come from affiliated blogs. NExT may reshape exams around 2028-29.
10. **Seasonality.** Demand bunches around each university's exams, which have no national calendar. LTV may be 1-3 months.

### Kill criteria (checked at day 90 and day 180)
| Trigger | Action |
|---|---|
| No content-rights path (licence, e-library route or open corpus) chosen and started by **day 90** | Stop all commercial work. Continue as a research and portfolio project only. |
| The safety module still gives **any "major"** on the 18-case set after two redesign cycles | Remove vignette and patient-style modes from any public or paid tier. Keep only factual Q&A. |
| Pilot **4-week weekly-active rate under 15%** (target 30%) | Rethink the wedge before adding colleges. |
| **Fewer than 10% of pilot students** say they would pay Rs 199-499 *and* fewer than 1% actually pay within 35 days | Stop selling direct to students. Move to the B2B or publisher route only. |
| Organic-loop test (one week with no invites) brings **close to zero** new first questions | Fix sharing before expanding. If two fixes fail, stop the volunteer channel. |
| **No publisher or college conversation reaches a second meeting by day 180** | Accept that the realistic outcome is a sustainable side project, portfolio piece or acqui-hire, and plan the team's time on that basis. |
| A takedown or legal notice from any publisher | Remove that source right away (B5), make the product private, and get legal advice before resuming. |
| Any wrong-citation rate **above 2%** in the 50-answer audit | Pause sharing features until it is fixed. |

---

## 8. Sources

**Market and supply**
- MBBS/PG seats and colleges, Lok Sabha Jul 2026: https://medicaldialogues.in/amp/news/education/139489-mbbs-86360-pg-844-medical-colleges-in-india-mos-health-175751
- NMC revised seat matrix 2026-27: https://news.careers360.com/nmc-revises-mbbs-seat-matrix-adds-13636-mbbs-seats-cross-1-40-lakhs-neet-ug-counselling-2026-admission
- Seats added 2020-26: https://medicaldialogues.in/amp/news/education/48563-mbbs-seats-added-in-last-6-years-mos-health-tells-parliament-165138
- 2025-26 seats (Parliament): https://medicaldialogues.in/news/education/altogether-128875-mbbs-80291-pg-medical-seats-in-india-for-2025-26-health-minister-tells-parliament-160593
- NEET-PG 2026: https://www.pw.live/news/neet-pg-2026-candidates-appeared-attendance-centres-re-exam-result-date
- NEET-PG 2026 date and internship cut-off: https://news.careers360.com/neet-pg-2026-exam-date-out-nbems-august-30-mds-tentative-schedule-internship-cut-off-notice-january-22-medical-sciences-board
- FMGE repeaters, June 2026: https://medicaldialogues.in/news/education/88-percent-fmge-june-2026-candidates-were-repeaters-freshers-had-35-percent-pass-rate-govt-176210
- FMGE Dec 2025: https://medicaldialogues.in/news/education/medical-admissions/only-10264-candidates-clear-fmge-december-2025-over-77-percent-fail-screening-test-163962
- NExT status: https://medicaldialogues.in/health-news/nmc/nmc-draft-keeps-fmge-for-provisional-nmr-registration-of-foreign-medical-graduates-until-next-exam-rollout-177477
- NMC CBME Regulations 2023 (supplementary exams): https://news.careers360.com/nmc-issues-cbme-regulation-2023-medical-colleges-granting-mbbs-admission-after-august-30-face-action/amp

**Competitors and wallet**
- Marrow/DailyRounds FY25: https://entrackr.com/fintrackr/dailyrounds-delivers-rs-363-cr-profit-on-rs-641-cr-revenue-in-fy25-11110021
- Marrow Pro prices: https://www.marrow.com/pro
- PrepLadder financials: https://inc42.com/company/prepladder/financials/
- DigiNerve DigiONE: https://www.diginerve.com/courses/undergrad/digione/
- DigiNerve AI launch: https://indiamedtoday.com/diginerve-launches-ai-powered-digineet-digione/
- PW MedEd batches: https://www.pw.live/neet-pg/batches
- PW offer document (ACPU): https://investmentbank.kotak.com/kib-cms/sites/default/files/offer-documets/Physicswallah%20Limited%20-%20BoA_.pdf
- PW ad spend: https://storyboard18.com/advertising/physicswallah-ramps-up-ad-spend-to-rs-276-crore-in-fy25-earmarks-rs-710-crore-for-promotions-from-ipo-80479.htm
- Oncourse and others (competitor-affiliated, low confidence): https://aimed-study.pages.dev/blog/best-neet-pg-online-coaching-platforms-2026
- Osmosis AI (Elsevier): https://www.elsevier.com/about/press-releases/elsevier-launches-study-companion-osmosis-ai-to-transform-how-medical
- ClinicalKey Student StudyFinder AI: https://itbrief.co.uk/story/elsevier-adds-studyfinder-ai-to-clinicalkey-student
- Elsevier RGUHS 55-college partnership: https://www.elsevier.com/promotions/rguhs-hub
- NML-ERMED / Thieme reach: https://www.devdiscourse.com/article/headlines/3989682-union-health-secretary-calls-for-expanding-digital-medical-resources-to-all-medical-colleges
- ONOS: https://narendramodi.in/cabinet-approves-one-nation-one-subscription
- Wiley AI licensing: https://newsroom.wiley.com/press-releases/press-release-details/2025/Research-Growth-AI-Licensing-and-Cost-Reduction-Drive-Wileys-Fiscal-2025-Results/default.aspx
- OpenEvidence: https://pulse2.com/openevidence-250-million-series-d-12-billion-valuation

**Adoption, conversion and economics**
- Mumbai MBBS AI-chatbot survey (IJMR): https://ijmr.org.in/prevalence-utilisation-of-ai-chatbots-for-medical-education-among-students-of-medical-colleges/
- Decode, students paying for apps (anecdotal): https://www.decodeinternet.in/decode/indias-future-doctors-pay-colleges-for-degree-and-apps-for-education-29593
- RevenueCat State of Subscription Apps 2026, Education: https://www.revenuecat.com/state-of-subscription-apps-2026-education
- Annual-subscriber cancellation (9to5mac): https://9to5mac.com/2026/05/27/new-report-shows-annual-app-subscribers-rarely-return-after-they-cancel/
- Edtech CAC (agency estimate, low confidence): https://upgrowth.in/edtech-gtm-strategy-frameworks-execution/
- ChatGPT Go free in India: https://www.business-standard.com/technology/tech-news/openai-offers-chatgpt-go-free-for-one-year-in-india-125102800612_1.html
- Google AI Pro via Jio: https://www.smartprix.com/bytes/google-and-jio-team-up-to-offer-18-months-of-free-google-ai-pro-plan-in-india/
- GST Notif. 10/2017-IT: https://taxheal.com/notification-no-102017-integrated-tax.html
- Razorpay pricing: https://razorpay.com/blog/razorpay-payment-gateway-pricing-explained/ and https://razorpay.com/blog/razorpay-0-percent-platform-fee-offer-90-days-new-merchants-2026/

**Internal (read-only)**
- `docs/eval_2026-11-13.md`, `docs/drug_check_ab.md`, `docs/demo_step1_decision.md`, `docs/demo_script.md`, `docs/atlas_coverage_plan.md`, `docs/master.html`
- `med-rag-v2/docs/research/market_competitor_analysis.md`: written by Gemini and **unverified**. Its "world's first" claim (lines 20, 390) and its "~$50M" Complete Anatomy price (line 45) should not be used.

**Practitioner lens (SuperMe):** Christophe Gillet (PrepScholar), Michał Borkowski (Brainly), Gina Gotthilf (ex-Duolingo), Valerie Wagoner (ZipDial), Kyle Poyar, Micah Moreau, Jonathan Stull (Handshake), Ashim Jolly (Haptik), Dheerja Kaur, Rob Schutz (Ro), Mamuna Oladipo (Theme Health), Erika Warren (Inciteful Med), Marcus Foster (KAYMO). None has Indian medical-student conversion data.

---

### Source check (15 Nov 2026)

The 12 most load-bearing sourced claims were checked twice each: once by fetching the cited page, once by an independent
web search. **11 verified by both checks; 1 partly verified** (the RGUHS arrangement is described as a partnership with
no price, so the wording above was corrected). Caveats found: Marrow's Rs 564 cr subscription figure is derived (88% of
Rs 641 cr operating revenue), not reported directly; PrepLadder's Rs 114.6 cr is total revenue from a single source
(Inc42); RevenueCat's 0.7% India/SEA download-to-paid median is by *user* geography (1.4% by developer HQ); a later
Lok Sabha reply (7 Aug 2026) gives 846 colleges / 1,39,864 seats, a negligible change. Full results:
`docs/evidence/source_check_2026-11-15.md`. Not checked: the team assumptions (rows marked TEAM ASSUMPTION or team guess),
which no source can verify; the pilot is how they get measured.

## Review notes (completeness critic, 15 Nov 2026)

**Recomputed and correct:** TAM (823k × Rs 3,683 = Rs 303 cr; Rs 257 cr ex-GST); Y3 funnel (21,280 → 5,320 + 1,500 = 6,820 installs → 68 + 3 = 71 payers × Rs 849 = Rs 60k); Y1 (6,080 → 1,520 + 375 = 1,895 → 19 payers × Rs 722 = Rs 14k; 13-27 range); net prices (Rs 487 / 585 / 1,464 after 2.36%); every single-lever sensitivity row; the +15% annual-price and -13% in-app-fee effects; top-down shares (0.33%, 0.05%, 105-210 band); 70k-140k installs for 1,000 payers; Wagoner's 40,000.

**Fixed in this file:**
1. Incumbent wallet: Rs 564 cr + Rs 114.6 cr = Rs 679 cr, not Rs 755 cr. Rs 755 cr uses Marrow's Rs 641 cr operating revenue; now stated both ways, and TAM share corrected from "30-40%" to "40-45%".
2. SAM-to-SOM gap: was "about 200x"; actual is about 2,000x (Rs 13 cr / Rs 60k; 131k / 71 payers).
3. Lens-vs-model gap: was "10-40x"; actual is 8-40x on payers and 25-80x on revenue. The bull case meets chief-of-staff's payer range but not its revenue range.
4. "1,000 users needs 10-20 colleges": at about 300 reached per college, 5,000-15,000 reached is about 15-50 colleges.
5. AI cost per heavy user: 300 × $0.0025 = $0.75, about Rs 65 (not Rs 75) at about Rs 88/$.
6. SAM: showed the Rs 15.7 cr gross / Rs 13.3 cr net step that was missing.
7. Labelled the team assumptions that had no label: the 35%-of-DigiONE supplement spend, 70 effective colleges, the 75/25 and 80/20 pass/annual mixes, and the de-duplicated NEET-PG/FMGE counts. Added a source pointer for the CAC estimate. Flagged "Jaypee >50%" as unsourced.
8. Overclaim: "published eval" is now "measured internal eval, not yet externally published". The one-line positioning statement is now tied to settled rights. The 26k / 95% ontology figure is marked internal.

**Still uncertain (not fixed):**
- How 80 nominal colleges becomes 70 effective at 40% churn, and the churn rows (67/75 payers), cannot be recomputed from the stated assumptions.
- *Resolved 15 Nov:* the bull and bear cases and the 80-to-70 college churn step are now derived explicitly in Section 5.6 (bull about 618 payers, about Rs 1,070 net each; bear about 10 payers). The 30%-of-a-year uncovered share behind the churn step is a team assumption.
- The NEET-PG de-duplication (265,980 appeared to about 140k non-intern) is not shown step by step.
- The low end of the SOM range leaves out repeat payers while the base includes them (about 48 vs about 50). This is immaterial.
- The 26k-fact / 95%-precision ontology claim could not be traced to a doc in `docs/`.
- **Budget:** the GTM plan has no cash budget line. Its listed costs are small: evals about $0.10-0.35 per run, credit/stipend ambassadors at 2-3 colleges, no paid ads and free-tier hosting. That looks feasible for a student team, but the ambassador stipend amount and post-trial hosting cost should be written down.
- **Open product risks are addressed:** the 12/18 patient-specific prescribing issue (A1, A2, Risk 2, kill criterion, "not clinical decision support") and textbook licensing (Section 4 licensing path, B5, hard gate, Risk 1, kill criteria) are both covered. All three lenses are represented throughout.
