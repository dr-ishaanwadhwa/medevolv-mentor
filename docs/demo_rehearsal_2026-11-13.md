# Demo rehearsal on the LIVE site (13/14 Nov 2026)

Run on 14 Nov 2026 (evening) against https://mentor.medevolv.in and https://atlas.medevolv.in, read-only, built-in browser,
no sign-in, no code or deploy changes. Script followed: `docs/demo_script.md`.

**Result: all 9 demo steps pass functionally (9/9). 14/14 main question runs and 7/7 fallback questions behaved as scripted
(route pill, status pill). No crash, no errors in console. 6 script details differ from the live behaviour (listed in "Deviations").**

## How latency was measured

"Server" is the number the app prints itself ("Done · N steps in X s"). "Wall" is click/Enter to the end of the Streamlit rerun,
measured in the page (includes about 1 s of Streamlit rerun overhead, which is why instant refusals show ~1 s wall).
Run 1 is the first call of that question in this session; Run 2 is straight after. The site had been idle before run 1 of step 1.

Step 1 run 1: only the server time (6.1 s) was captured, the wall clock was not (my timer misfired). Run 2 wall was 6.0 s.

## Step table

| Step | Latency run 1 (wall / server) | Latency run 2 (wall / server) | Pass? | Notes |
|---|---|---|---|---|
| 0 Opening: How it works tab, empty screen with tiles | page loads in 0.4 s (curl) | - | PASS | Diagram is tiny at a 1024-px-wide window (hard to read from the back of a room). The "Try a demo question" tile box is a scroll box, so tiles are cut off at small window heights. |
| 1 Clinical vignette (38-year-old, pheochromocytoma) | n/a / 6.1 s | 6.0 s / 4.9 s | PASS | Pills "Grounded answer" + "Long case · focused look-ups" both runs. Alpha-blockade first, beta-blocker only after, "Avoid:" line (beta-blocker first, furosemide) in both runs. 13 steps, 4 textbook searches, 2 model calls. Sources: 7 and 6 cited of 9. The "books give no dosing protocol" line is present in run 2 ("Note: the sources do not give a specific acute i.v. dosing regimen...") but NOT in run 1. |
| 2 Wheeze + breathlessness (graph route, Warnings) | 4.0 s / 2.9 s | 4.3 s / 3.2 s | PASS | Pills "Grounded answer" + "Clinical case · graph route". "Warnings" line present both runs (run 2: timolol, adenosine, beta blockers in asthma; zanamivir and high-flow oxygen in COPD). First-line = inhaled corticosteroids. |
| 3 Femoral triangle (Gray's) | 3.2 s / 2.3 s | 3.1 s / 2.1 s | PASS | "Single question · direct search". All 6 retrieved passages are Gray's, match 0.72-0.80. Cited: 2 of 6 (run 1), 3 of 6 (run 2), script says 4 of 6. No crash (an old backup image in the folder shows a NameError on this question; it does not reproduce live). |
| 4 Compare penicillins vs aminoglycosides (tile) | 5.4 s / 4.4 s | 5.9 s / 4.9 s | PASS | "Compound · split into parts". Trace row "Split into 2 sub-question(s)" shows the exact two questions in the script. One section per drug class. Optional contrast (Multi-hop OFF) works: no Compound pill, single search, 6 steps, 3.5 s, sources mostly Tripathi. Toggle restored to ON. |
| 5a Personal refusal (tile) | 1.0 s / 0.0 s | 1.0 s / 0.0 s | PASS | Red pill "Personal medical advice: declined", 2 steps. |
| 5b Cricket (tile) | 1.1 s / 0.1 s | 1.2 s / 0.1 s | PASS | Amber pill "Not in the textbooks: declined". Trace row: "Best match scored 0.53, below the 0.60 threshold ... language model is never called". 0 model calls. |
| 5c Learn pharmacology (optional third refusal) | 2.4 s / 1.4 s | 1.8 s / 0.8 s | PASS | "Evidence insufficient: declined". |
| 6 Explore: Rifampin, TB, Antibiotics hub, local graph | search to page: 0.9 s; TB 1.2 s; Back 0.9 s; hub 0.9 s; Show hubs 1.3 s | not repeated (no model call) | PASS | Search lists "Rifampin · Drug / therapy" first. Four book pills. Part of: Antibiotics, Antimicrobial agents, Antimicrobials + Mechanism: Cytochrome P450 enzymes. "Treats · 26 derived", then "Tuberculosis · 4 books". TB page: breadcrumb "Explore > Rifampin > Tuberculosis", six book pills incl. Gray's, Part of Infectious, Also in BODHI "Tuberculosis same concept T2", "Rifampin · 4 books" present. See also · 10 (Rifamycins, Rifabutin, Pyrazinamide, Ethambutol, Isoniazid ...). Hub: "Drug class · 44 members · suggested". Local graph: "24 concepts shown", Show hubs adds a grey box (Cytochrome P450 enzymes) on a dotted line. Header on the Explore tab: 5001 conditions, 25,902 certified facts. |
| 7 Books differ, rheumatoid arthritis | Browse 1.0 s; RA 1.1 s | - | PASS | Condition box reads "Rheumatoid arthritis · 114 facts". "Books differ · 1 case": methotrexate card, treatment cited to Tripathi, Robbins, Davidson, Harrison; contraindication cited to Davidson pp. 1043-1048 ("DMARDs that must be avoided..."); banner "Neither is marked wrong, so read both sources." |
| 8 Atlas deep links (3D) | `?select=FMA62045`: opens Optic Chiasm with info panel in under 4 s cold, 0.25 s warm | - | PASS | FMA62045 = Optic Chiasm (panel, "Show surrounding anatomy"). FMA9921 (from the TB "View involved structures in 3D" button) = lumbar vertebra, panel fades in. FMA10446 (Intervertebral disc, from "Also in 3D") shows the 3D pieces with a label but no info panel. Invalid ID (FMA99999999) falls back to the whole-body view, no error. Links open in a new tab (`target=_blank`). Console clean. |
| Backup / infrastructure | - | - | PASS | https://130-210-60-153.sslip.io returns 200. HTTPS certificates (Let's Encrypt) valid until 10-11 Feb 2027 on mentor, atlas and the sslip.io backup. |

## Fallback questions (one run each, all behave as scripted)

| Fallback | Wall / server | Route pill |
|---|---|---|
| 1 Falciparum malaria vignette | 9.2 s / 8.0 s | Long case · focused look-ups |
| 2 Wheeze, breathlessness, cough at night | 3.9 s / 2.7 s | Clinical case · graph route |
| 2 Morphine in head injury | 2.4 s / 1.3 s | Single question |
| 3 Rotator cuff | 2.3 s / 1.0 s | Single question |
| 4 Type 1 vs type 2 diabetes | 5.1 s / 3.8 s | Compound · split into parts |
| 5 Ibuprofen for my headache | 1.4 s / 0.0 s | Personal medical advice: declined |
| 5 Eka Care's revenue | 2.0 s / 0.6 s | Evidence insufficient: declined (the script text says off-topic; it still declines) |

## Deviations from the script (edit the script, not the site)

1. **Step 1, "where the books stop" point is not guaranteed.** Run 1 had no "no dosing protocol" line; run 2 did. Say it only if it is on screen.
2. **Step 3 "4 of 6 passages cited"** is really 2 to 3 of 6 on the live site. All passages are still Gray's.
3. **Step 6, "5 hub chips"**: the Rifampin page shows 3 drug-class chips (Antibiotics, Antimicrobial agents, Antimicrobials) plus the Mechanism chip. The "Second-line anti-tubercular agents" chip is no longer on the page, so the "known flaw" paragraph and "Do not click that chip" are out of date.
4. **Step 6 / Local graph size:** the graph is 2,519 px tall with Show hubs on. It does not fit one screen at 80-90% zoom on a typical laptop; plan to scroll or zoom to about 50%, or use the screenshots.
5. **New features the script does not mention:** "Generate diagram" button and the "Clinical graph · complaints > differential > phases > workup > therapy" panel under every clinical answer (Drill in / Show all 5 levels / Reset), and "View involved structures in 3D" on condition pages. The professor will see them; know what they do.
6. **Step 6 hub count / book pills for TB** match the script (six pills, Gray's included).

## Risks and fallbacks

| # | Risk | Likelihood / impact | Fallback |
|---|---|---|---|
| 1 | **Single point of failure: DeepSeek API balance and the 1-CPU Oracle VM.** Steps 1, 2, 3, 4 all call the model; if DeepSeek is down or the balance is zero, they all fail. Explore (6, 7), the refusals 5a/5b and atlas make no model call and keep working. | Low / High | Check balance on the morning. Reorder the demo to lead with Explore and refusals if the model is down. The offline Ollama fallback exists but is weaker. |
| 2 | **Long answers are the slow ones.** Step 1 is 5-6 s warm; the malaria fallback is 9 s; first call after a restart or idle can take longer (about 12 s per the script). | Medium / Medium | Warm the site (anatomy question, then step 1) and Clear chat 5 minutes before. Prefer the faster step 1 alternative: the wheeze case (3-4 s). Keep the status box talking while it works. |
| 3 | **Local graph does not fit the screen** (2,519 px tall), and the "Drill in" buttons wrap badly in a narrow window; the opening diagram is tiny. | High / Low | Browser zoom to 50-67% for the graph, full-screen window, or show `step-6-local-graph-hubs-bottom.png`. Test the projector resolution on the day. |
| 4 | **Answers are non-deterministic.** The wording, number of cited passages and optional lines (e.g. the "no protocol" note) vary run to run. | High / Low | Do not promise exact text; use the "point at" list, not the wording. |
| 5 | **Atlas details are uneven.** FMA10446 (Intervertebral disc) shows no info panel, and Optic Chiasm shows generic nervous-system text. | Medium / Low | Demo only FMA62045 and FMA9921 (both have panels). |
| 6 | Stale files in `docs/demo_backup/`: older `.jpg` screenshots from an earlier pass remain, including `step-3-anatomy-NameError-crash.jpg` which would be embarrassing if opened on screen. | Low / Medium | Delete or move the `.jpg` files before the demo (I did not touch them). |
| 7 | Free Oracle trial credit / certificate: VM stops when trial credit ends; cert expires 10 Feb 2027 (fine). | Low / High | Check the Oracle console on the morning. Backup address already works. |

## Pre-demo checklist (additions marked NEW)

- [ ] Freeze: no deploys, no re-index, no `.env` edits. Write down the live commit hash.
- [ ] Check DeepSeek balance (>= $2) and the Oracle VM + credit.
- [ ] Open https://mentor.medevolv.in in two tabs (Ask, Explore). Confirm the lock icon. Open the backup https://130-210-60-153.sslip.io once.
- [ ] Warm-up: anatomy question, then the step 1 vignette, then "Clear chat". Search Rifampin once in Explore.
- [ ] Sidebar: Multi-hop reasoning ON (verified ON and restored after the contrast test).
- [ ] NEW: Set browser zoom for the local graph (50-67%) and check it on the projector.
- [ ] NEW: Open both atlas links once beforehand: `https://atlas.medevolv.in/?select=FMA62045` and `?select=FMA9921` (about 4 s cold).
- [ ] NEW: Remove the stale `.jpg` files (including the NameError one) from `docs/demo_backup/`, keep the `.png` set; open that folder in a second window.
- [ ] NEW: Update the script for deviations 1-5 above (step 3 cited count, step 6 hub chips, the "second-line" note, new diagram and 3D features).
- [ ] Paste-ready notes file with step 1, step 2 and fallback vignettes. Phone hotspot ready.

## Screenshots (docs/demo_backup/, PNG, from the live site)

`step-0-empty-screen-demo-tiles.png`, `step-0-opening-how-it-works.png`, `step-1-vignette-answer.png`, `step-1-vignette-trace.png`,
`step-2-warnings-line.png`, `step-3-anatomy-grays.png`, `step-4-compare-decompose.png`,
`step-5-refusals-personal-and-insufficient.png`, `step-5b-cricket-threshold-trace.png`, `step-6-rifampin-page.png`,
`step-6-rifampin-backlinks.png`, `step-6-tuberculosis-page.png`, `step-6-antibiotics-hub.png`, `step-6-local-graph-hubs-bottom.png`,
`step-7-books-differ-ra.png`, `step-8-atlas-FMA62045-optic-chiasm.png`, `step-8-atlas-from-tuberculosis-FMA9921.png`.
