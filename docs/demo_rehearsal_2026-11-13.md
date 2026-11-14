# Demo rehearsal, live site, 13 Nov 2026 (read-only)

Target: https://mentor.medevolv.in and https://atlas.medevolv.in. Script followed: `docs/demo_script.md`.
Method: (a) a browser pass on the live site (1440x900, no sign-in, Multi-hop ON); (b) backend timing on the VM, running
`rag.answer.answer_multihop(q)` inside `eka-app-1` twice per question (code piped over ssh stdin, nothing written on the
server). Screenshots are in `docs/demo_backup/` (`step-N-*.jpg`).

Pass rate: **7 of 8 script steps pass on the live site** (opening, 1, 2, 4, 5, 6, 7). **Step 3 (anatomy) fails**: the live
app crashes with a NameError when the answer is rendered. All 11 backend questions return the expected route and status;
the one soft spot is the DKA fallback, whose "Warnings" line was missing on 1 of 2 runs. Explore click paths: 3 of 3 pass.

## Top 3 risks

1. **Step 3 (Gray's anatomy) crashes the page on the live site (reproduced 2 of 2).** The answer text appears, then a red
   `NameError: name '_safe' is not defined` replaces the Sources panel (`app.py` line 301, called from `render_sources` via
   line 463). Cause: `_safe` is defined at line 703, after the chat render at line 463 runs. It only triggers on Gray's
   passages (the "View in 3D" lookup), so steps 1, 2, 4 and 5 are unaffected. The failed answer is also dropped from the chat
   history on the next turn, leaving an orphan question. The fallback anatomy question (rotator cuff) is Gray's-only and will
   hit the same path (not run in the UI). It also means the "View in 3D" link from an Ask answer cannot be shown. Not fixed
   here (rules: no code edits). Needs a fix before the demo, or drop step 3 and say nothing about anatomy, or pre-record it.
2. **Step 1 answer contradicts itself in the visible text.** Under "Emergency stabilization" and "Definitive pharmacology" it
   says IV beta blockers can be given, and lists nitrates "to relieve angina", then the "Avoid:" block (which is correct) says
   nitrates and beta blockers are contraindicated. A cardiologist reading the whole answer will spot it. Say up front: "read
   the Avoid line, and note the model also restates the textbook's general indications, with conditions". Wording varies per run.
3. **Latency and cold starts.** Backend first call per fresh process was 20.1 s (step 1), 14.3 s (step 3), 12.3 s (cricket),
   against 6 to 9 s warm. On the live site the first vignette took 7.0 s (warm process). Case route is the slowest at 6 to
   9 s. Everything depends on DeepSeek reachability; the VM is shared with other containers (life-inbox, ps11-copilot).

## Step table

Latency columns are backend `answer_multihop` wall time (run 1 / run 2). Run 1 of the first question in each of my three
processes includes embedding-model load (about 6 to 12 s), which the live Streamlit process does not pay once warm. "UI" is
the time the live page itself reported.

| Step | Question / click path | Run 1 | Run 2 | UI | Pass | Notes |
|---|---|---|---|---|---|---|
| 0 | Opening: How it works tab, question-time diagram | n/a | n/a | n/a | PASS | Diagram renders. Header says 35,902 passages; the trace says "36,725 textbook passages" (mismatch, see risks list below). |
| 1 | RV-infarct vignette (64 words) | 20.1 s (cold process) | 6.3 s | 7.0 s, 15 steps | PASS | Route `case`, status `answered`, 3 axes, 6 hops, 2 certified warnings (flecainide, beta blockers), 7 to 8 cited, books Davidson, Harrison, Tripathi. UI pills "Grounded answer" and "Long case · focused look-ups"; trace has "3 clinical axis/axes, 5 look-ups", 6 vector searches, "Textbook ontology lookup" (4 facts), "Citation check: 8 of 9 passages, 4 of 4 graph facts". Avoid line named nitrates, IV and oral beta blockers, flecainide, short-acting nifedipine. UI run cited Davidson and Harrison only (no Tripathi). Contradictory statements elsewhere in the answer (risk 2). Trace row 2 shows "onset of → Fever onset" as a linked symptom, which looks wrong. |
| 1 fb | DKA vignette | 8.1 s | 8.7 s | n/a | PASS (soft) | `case`, `answered`, 3 axes, 3 warnings, books Davidson, Guyton, Harrison, Robbins, Tripathi. The "Warnings" line was absent on run 1, present on run 2. No "Avoid" line in either run (expected for this case). |
| 2 | Wheeze and breathlessness: first-line class and drugs to avoid | 3.2 s | 2.5 s | 2.7 s, 16 steps | PASS | Route `graph`, `answered`, 5 warnings in evidence, "Warnings — drugs to avoid" present. Pill "Clinical case · graph route". Asthma, COPD, lung abscess differential; inhaled corticosteroids first-line. Warning rows: timolol (Tripathi), adenosine (Davidson), beta blockers (Harrison), plus zanamivir and high-flow oxygen for COPD. Books Tripathi, Harrison, Davidson. |
| 2 fb | Wheeze, breathlessness, cough at night | 3.1 s | 3.2 s | n/a | PASS | `graph`, `answered`, 4 warnings, Warnings line both runs. Differential here is asthma, pneumonia, bronchitis. |
| 3 | Femoral triangle boundaries and contents | 14.3 s (cold process) | 1.6 s | 1.9 s, 8 steps | **FAIL (UI)** | Backend is fine: `single`, `answered`, Gray's only, 2 to 3 cited. In the UI the answer text renders and is correct, then the `_safe` NameError crashes the Sources panel (reproduced twice). See risk 1. |
| 3 fb | Rotator cuff muscles and nerve supply | 1.4 s | 1.3 s | not run | PASS (backend) / expected FAIL (UI) | `single`, `answered`, Gray's only. Same render path as step 3. |
| 4 | Tile: Compare penicillins and aminoglycosides | 4.3 s | 4.3 s | 4.1 s, 10 steps | PASS | Route `decompose`, `answered`, 3 hops. UI pill "Compound · split into parts"; trace "Split into 2 sub-question(s)" with the two mechanism questions and two searches. Books: Harrison and Tripathi (run 1), Tripathi only (run 2 and UI). Both classes have their own sections plus a "Key contrast" block. |
| 4 fb | Compare type 1 and type 2 diabetes | 4.1 s | 4.1 s | n/a | PASS | `decompose`, `answered`, Davidson and Harrison. |
| 5a | Tile: My mother has TB, how much rifampicin | 0.1 s | 0.0 s | 0.0 s, 2 steps | PASS | `personal_refusal`, no route, no search. Red pill "Personal medical advice: declined". |
| 5b | Tile: Who won the 2011 cricket world cup | 12.3 s (cold process) | 0.1 s | 0.1 s, 6 steps | PASS | `not_in_sources`. Amber pill "Not in the textbooks: declined"; trace "Best match scored 0.53, below the 0.60 threshold", 0 model calls. |
| 5c | Optional: best way to learn pharmacology quickly | 0.6 s | 0.9 s | not run | PASS (backend) | `insufficient`, no cited books. |
| 6 | Explore: Rifampin, backlinks, hub, local graph | n/a | n/a | page loads in 1 to 3 s | PASS | See Explore check below. |
| 7 | Explore: Rheumatoid arthritis, Books differ | n/a | n/a | 1 to 3 s | PASS | See Explore check below. |

## Explore click-path check (live site, no model calls)

| Path | Result | What I saw |
|---|---|---|
| Rifampin, backlinks, hub, local graph | PASS | Search "Rifampin" returns "Rifampin · Drug / therapy" first. Page shows four book pills (Davidson, Harrison, Microbiology, Tripathi), Part of: Drug class (suggested) Antibiotics, Antimicrobial agents, Antimicrobials; Mechanism: Cytochrome P450 enzymes. "Linked from: Treats · 26 derived". Click "Tuberculosis · 4 books": breadcrumb "Explore › Rifampin › Tuberculosis", six book pills including Gray's, Part of Infectious, "Also in BODHI: Tuberculosis same concept T2", and "Treated by · 24" containing "Rifampin · 4 books". "← Back" returns to Rifampin; "See also · 10" present. Click "Antibiotics": "Drug class · 44 members · suggested", page 1 of 2, with the "not a textbook statement" caption. Local graph: "24 concepts shown", "is a First-line antitubercular drug", 3 adverse-effect nodes, treats nodes drawn dashed. |
| Rheumatoid arthritis "Books differ" | PASS | Browse by organ system, Blood & immunology is selected by default, click "Rheumatoid Arthritis" (it is not pre-selected, as the script says you click it). "Rheumatoid arthritis · 114 facts". "Books differ · 1 case": methotrexate, Listed as a treatment (Tripathi's book titled "Essentials of Medical Pharmacology", Robbins, Davidson, Harrison), Listed as a contraindication (Davidson, "DMARDs that must be avoided: methotrexate, leflunomide..."), banner "Neither is marked wrong, so read both sources." Clinical facets tabs below include Warnings. |
| "View in 3D" opens atlas with structure selected | PASS (Explore) / BLOCKED (Ask) | Tuberculosis page has "View involved structures in 3D" linking to `https://atlas.medevolv.in/?select=FMA9921`; the atlas loaded in about 8 s and selected "Lumbar Vertebra" (5 pieces, Pott's spine as the TB structure, not the lung; expect a question). `?select=FMA62045` loaded and selected "Optic Chiasm". The Ask-side link ("View X in 3D" under a Gray's source) is the code path that crashes, so it cannot be shown from an Ask answer today. |

## Other discrepancies versus the script

- Rifampin page does NOT show "Second-line anti-tubercular agents" in Part of any more (only Antibiotics, Antimicrobial agents,
  Antimicrobials). The "do not click" warning is moot on this page; keep it in case the group appears elsewhere.
- "Show hubs" on Rifampin adds one box only ("Cytochrome P450 enzymes", dotted "part of"), not the drug-class group boxes
  the script describes. Say "a group box", singular.
- The local graph is a tall vertical column (24 nodes, over one screen high even at 1600x1500). Browser zoom of 80 to 90%
  will not fit it on one screen; plan to scroll, or use the screenshots.
- Answers now include a "Generate diagram" button and a "Clinical graph" drill-down panel (steps 1 and 2) that the script
  does not mention. Do not click Generate diagram live (unrehearsed, may call the model).
- Header says 35,902 passages and 2,611 sections; the trace says "Vector search over 36,725 textbook passages". Pick one to
  quote or be ready to explain.
- Live Explore header: "5001 conditions, 25,902 certified facts", matching the script's note.
- Orphan question after the step 3 crash: the question stays in the chat with no answer. "Clear chat" fixes it.
- VM has 2 CPUs (script says 1), 9.4 GB disk free, 9 GB RAM available; other containers share it.
- Backup URL https://130-210-60-153.sslip.io returned HTTP 200 in 0.22 s; mentor and atlas 200 in under 0.2 s.

## Fallback questions (all verified on the backend)

| If this fails | Use | Evidence |
|---|---|---|
| Step 1 slow (over 15 s) or errors | DKA vignette (script text) | `case`, 8.1 and 8.7 s, 3 warnings; may lack the "Warnings" line |
| Step 2 slow or no Warnings line | "A patient has wheeze, breathlessness and cough at night. Likely diagnosis and drug treatment?" | `graph`, about 3 s, Warnings both runs |
| Step 3 crashes (it does today) | Skip anatomy and say so; or show `step-3-anatomy-NameError-crash.jpg` only if asked. Rotator cuff will crash too | See risk 1 |
| Step 4 slow | "Compare type 1 and type 2 diabetes mellitus." | `decompose`, about 4 s |
| Step 5 | "Should I take ibuprofen for my headache?" (personal) | not re-run today, per script |
| Explore search fails | Browse by organ system, then step 7 path | Works, verified |
| Site down | Backup screenshots in `docs/demo_backup/` and https://130-210-60-153.sslip.io | Both exist |

## Morning-of checklist (17 Nov)

- [ ] Confirm the `_safe` crash is fixed (or step 3 is cut), by asking the femoral triangle question once on the live site
  and checking that Sources opens with no red box. Do this before 16 Nov, then freeze deploys.
- [ ] Note the commit hash live; no deploys, pushes, re-indexing or `.env` edits on the day.
- [ ] DeepSeek balance above $2. Oracle VM running, trial credit not exhausted.
- [ ] Open https://mentor.medevolv.in in two tabs (A: Ask, B: Explore). Lock icon valid. Backup URL loads.
- [ ] Warm up: one anatomy-style or short question, then the step 1 vignette once (6 to 9 s warm, 20 s cold), then open
  Explore and search Rifampin once. Click "Clear chat".
- [ ] Sidebar: Multi-hop reasoning ON (it was ON by default today). Threshold shows 0.60.
- [ ] Paste file ready: step 1 vignette, step 2 question, DKA fallback, short-vignette fallback.
- [ ] Screenshots folder `docs/demo_backup/` open in another window, plus a slide copy.
- [ ] Browser full screen, 100% zoom; expect to scroll the local graph.
- [ ] Rehearse the sentence for the step 1 contradiction (IV beta blocker and nitrate lines versus the Avoid block).
- [ ] Be ready for: why the TB "View in 3D" selects the lumbar vertebra; "Viral exanthem" versus measles limit; DeepSeek
  grading itself.
- [ ] Phone hotspot, projector and Wi-Fi checked. Terminal and `.env` closed. No API keys on screen.

## Screenshots saved (`docs/demo_backup/`)

step-0-opening-how-it-works, step-0-empty-screen-demo-tiles, step-1-vignette-avoid-line, step-1-vignette-trace,
step-2-asthma-warnings, step-3-anatomy-NameError-crash, step-4-compare-decompose-pill, step-5a-personal-refusal,
step-5b-cricket-threshold-trace, step-6-rifampin-page, step-6-tuberculosis-page, step-6-antibiotics-hub,
step-6-local-graph-middle, step-6-local-graph-hubs-bottom, step-6-atlas-3d-from-tuberculosis-FMA9921,
step-6-atlas-FMA62045-optic-chiasm, step-7-books-differ-ra. (All `.jpg`. There is no good screenshot of the step 2 Sources
panel or the step 1 "Sources" panel; both were verified by text only.)
