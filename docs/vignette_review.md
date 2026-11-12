# Pre-check of the 15 gold vignettes (`eval/questions.jsonl`)

Reviewer: AI pre-check for the student's sign-off. The file was not modified. All 15 `gold_sections` titles were found in the matching `toc.json`. Some are too broad, and one points at the wrong subsection (see below). Medical points are by standard textbook teaching and need your judgement as the final check.

## Summary table

| id | starts with | verdict | reason |
|---|---|---|---|
| q01 | 12-year-old, staring spells, prolonged seizure | FIX | Vignette describes status epilepticus (seizure continuing after rectal diazepam) but asks about absence-seizure drug of choice. Question and stem do not match. Answer itself is correct. |
| q02 | 54-year-old, new T2DM, metformin | FIX | `gold_sections` points to the Overview subsection, which does not discuss metformin. The metformin text is in "Oral Hypoglycaemic Drugs". "Complex I" is a contested mechanism. |
| q03 | 68-year-old, gentamicin, hearing loss | OK | Consistent and correct. Hearing loss, gait and creatinine rise are all explained. Minor: the stem more or less names the two toxicities. |
| q04 | 62-year-old, ischemic cardiomyopathy | OK | Section matches (Guyton ch. 9). Vignette is decorative: the answer is the textbook law and never uses the patient. |
| q05 | 23-year-old, blunt abdominal trauma | OK | Consistent haemorrhagic shock. Baroreflex answer correct and matches the section. |
| q06 | 58-year-old smoker, LDL 190, coronary thrombosis | OK | Correct and the section matches. Small nit: "refractory hypertension" plus sudden death is a loose stem. |
| q07 | 34-year-old immigrant, apical cavitation | FIX | Question asks for "mechanisms" of caseous necrosis, but the gold gives morphology only. The section (Cell Death) is the wrong place for the mechanism. |
| q08 | 19-year-old T1DM, Kussmaul, pH 7.12 | OK | Vignette is realistic and the answer correct. Gold should state the potassium threshold more precisely. |
| q09 | 46-year-old, fatigue, TSH 38 | OK | Correct. Leakage: the stem lists most of the manifestations the question asks for. |
| q10 | CSF from febrile 2-year-old, Gram stain | CHECK | Vignette unrelated to the question (generic Gram-stain theory). Gold section is a 68-page chapter, too broad for a retrieval metric. |
| q11 | 28-year-old, step-ladder fever, S. Typhi | FIX | Stem says blood culture is already positive, then asks about diagnostic timing. Gold omits bone marrow culture and gives Widal without caveat. |
| q12 | 42-year-old, 45 min palpitations, HR 160 | CHECK | Gold describes narrow vs wide-complex triage, which the 1-page Harrison chapter does not appear to cover. Gold may not be supported by the cited text. |
| q13 | 29-year-old, day-5 dengue, platelets 40,000 | FIX | Stem has warning signs, not severe dengue. Gold is vague on fluid regimen and the Reye syndrome claim is dubious. |
| q14 | 65-year-old, nosocomial pneumonia, beta-lactam vs aminoglycoside | FIX | Comparison question but `gold_sections` lists only the penicillin section. The aminoglycoside mechanism is in ch. 53 Overview. |
| q15 | 32-year-old, rainforest, polyarthralgia, rash | CHECK | Differential too narrow (Zika, Mayaro, other alphaviruses missing). "Specialist" part is not textbook-answerable. Shares its single section with q13, so not true multi-hop. |

**Counts: OK 6 (q03, q04, q05, q06, q08, q09), FIX 6 (q01, q02, q07, q11, q13, q14), CHECK 3 (q10, q12, q15).**

## Suggested corrections

**q01 (FIX).** Either (a) remove the status-epilepticus framing and use a plain absence picture (child with brief staring spells, 3 Hz spike-wave on EEG, no prolonged seizure), or (b) change the question to ask the status-epilepticus step after benzodiazepine failure. Keep the answer as is for option (a). Fever, tachycardia and drowsiness add nothing for the absence question. Also consider a tripathi section that covers the mechanism of ethosuximide (the "Treatment of Epilepsies" text may not carry the T-type channel point; add "Overview" of ch. 30 or the ion-channel section if retrieval is expected to find it).

**q02 (FIX).** Add or replace with `19. Insulin, Oral Hypoglycaemic Drugs and Glucagon › Oral Hypoglycaemic Drugs`. The Overview subsection (pp. 275-276) is a short intro and does not carry the metformin mechanism. Soften the gold: say it reduces hepatic gluconeogenesis, increases peripheral insulin sensitivity/glucose uptake, activates AMPK, and does not stimulate insulin secretion. Complex I inhibition is the commonly taught mechanism but is debated, so mark it as "reported" or drop it if the book does not say it. The stem's "eGFR > 80" is fine.

**q07 (FIX).** Choose one: (a) change the question to "what are the morphologic hallmarks of caseous necrosis" and keep the Cell Death section, or (b) keep "mechanisms" and expand the gold with the cell-mediated (type IV) hypersensitivity / macrophage activation by T-cell interferon-gamma pathway, then add the Robbins infections section on tuberculosis (and optionally the chronic inflammation section on granulomas) to `gold_sections`. Also the stem already gives Langhans giant cells and "central acellular eosinophilic debris", so the answer is partly leaked; consider removing "Langhans giant cells" from the stem.

**q08 (OK, optional polish).** Tighten the gold: insulin infusion is started once K+ is at or above about 3.3 mmol/L (hold and replace K+ first if lower); add K+ to the fluids once K+ is below about 5.3 mmol/L and urine output is confirmed; add dextrose when glucose falls to about 200 mg/dL in DKA. Balanced crystalloid is now an accepted alternative to saline in recent consensus guidance. Bicarbonate is not routine unless pH is very low. These are details; the current answer is acceptable.

**q10 (CHECK).** The stem about CSF in a febrile 2-year-old suggests a clinical question (bacterial meningitis organisms and what the Gram stain shows) but then asks pure Gram-stain theory. Either rewrite the question to "what would Gram stain of CSF show and why do the organisms stain as they do", or drop the vignette. Narrow `gold_sections` if the TOC has a Gram-staining subsection; otherwise accept the broad chapter but expect the retrieval metric to be lenient.

**q11 (FIX).** Remove "Blood cultures confirm Salmonella enterica serotype Typhi" from the stem (change to "suspected enteric fever"). Add bone marrow culture (highest yield, stays positive after antibiotics) to the gold, and note that Widal is of limited value (low specificity, endemic-area baselines) even where taught. Day 10 is the second week, so a good vignette makes the answer "blood culture still useful, Widal now becoming positive".

**q12 (CHECK).** Confirm the Harrison palpitations chapter (about one page) actually contains the ECG / narrow-wide complex triage and red-flag list used in the gold. A quick read suggests it focuses on causes, history and examination, with no rhythm triage. If so, trim the gold to what the chapter states (cardiac vs psychiatric causes, history, examination, ECG/monitoring) or add a section that does cover tachyarrhythmia triage. The vignette (regular HR 160, stable) is consistent with SVT, so the red-flag part of the question is slightly out of step with a stable patient; fine, but state that in the gold.

**q13 (FIX).** Platelets 40,000 with rising hematocrit and positive tourniquet test is dengue with warning signs (hemoconcentration, thrombocytopenia), not yet defined severe dengue, which needs shock, severe bleeding or organ involvement. Either add "narrow pulse pressure, cold clammy extremities, hypotension" to the stem or rename the question "dengue with warning signs". Add concrete fluid guidance to the gold (isotonic crystalloid, small boluses, titrate to hematocrit/urine output, avoid overload, colloid only if refractory shock). Replace the Reye syndrome rationale with bleeding/gastritis risk; Reye is not a standard reason to avoid NSAIDs in dengue (verify the one Reye mention in the Harrison chapter is about this). The 24k-word chapter is a very broad gold section.

**q14 (FIX).** Add `53. Aminoglycoside Antibiotics › Overview` to `gold_sections` (and keep the penicillin section; the actual beta-lactam mechanism text is in the penicillin subsections, so also check `Penicillin-G` if the Penicillins intro is too short). Without this, a correct retrieval of both halves will be scored as a miss. Also, current HAP/VAP guidance avoids routine aminoglycoside as the second agent, so reword the stem to "regardless of regimen choice, compare mechanisms" to avoid implying a recommended combination. Keep "bactericidal" in the question; both classes are indeed bactericidal.

**q15 (CHECK).** Add Zika and Mayaro (rainforest) to the acceptable differential, and note that chikungunya is the best fit for symmetric small-joint polyarthralgia. "Relevant medical specialist" is not answerable from the cited chapter; drop it or accept "physician / infectious disease" as free-text. The type is labelled multi-hop but there is a single gold section shared with q13; either add a second source (for example the microbiology text's section on arboviral fevers, which exists in the TOC) or relabel as a factual vignette. Also confirm the paracetamol advice in the gold is in the Harrison text.

## Top issues across the set

1. Question and vignette do not match (q01, q10, q13, q15): the stem describes one thing and the question asks another.
2. `gold_sections` wrong or incomplete (q02 wrong subsection, q14 missing the aminoglycoside section, q07 mechanism not in cited section, q10/q13 sections far too broad).
3. Answer leaks into stem or stem contradicts the question (q11 culture already confirmed, q07 Langhans giant cells, q09 manifestations listed).
4. Gold may go beyond the cited text (q12 triage, q13 Reye claim, q02 Complex I).
5. Clinical-guidance polish (q08 K+ thresholds, q11 Widal/bone marrow, q14 HAP/VAP guidance).
