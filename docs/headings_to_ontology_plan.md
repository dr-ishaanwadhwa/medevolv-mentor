# Textbook headings as ontology concepts: measurements and common-sense rules

Status: **plan only, nothing implemented, no code or data changed.** Measured 2026-11-13 on the 2,676 sections in
`data/okf/<book>/toc.json`, the certified ontology (`rag.ontology_facts.facts()`: 25,902 CERTIFIED facts, 20,342 nodes),
and the built graph layers in `data/graph/`. Counts and heading titles only; no textbook body text is reproduced.
DeepSeek prices are the repo's own assumption (`ontology/gapfill.py`: $0.28 per M input, $0.42 per M output; the
older plans allow up to $1.10 per M output). Recheck before spending.

Throwaway scripts (not in the repo) are in
`/private/tmp/claude-501/-Users-ishaanwadhwa-Projects/6347ad9d-256b-4601-abf0-654b70348ad9/scratchpad/`:
`h2.py` (heading tree), `hlib.py` (matching), `hclass.py` (classifier), `h4.py` to `h7.py` (measurements).
Stage A below promotes them to `eval/heading_metrics.py`.

## 0. How to read the numbers

- "Heading" = one node of the ToC tree below the book title: 3,135 nodes, of which 2,675 are sections (the 2,676 sections
  have 2,675 distinct paths: Tripathi has one duplicated path, `... Maturation Factors > Uses`).
- Match = `ontology.merge.merge_key` equal to the key of any ontology node label (any type), after stripping the numbering
  prefix ("52 Jaundice", "37.", "Unit VI"), folding ALL CAPS, and (relaxed pass) removing parentheses, "The", "Diseases of",
  "[IX]" and `rag.atlas.variants`. `concepts.search_concepts` is a prefix search over the same labels; it adds almost
  nothing as a matcher (only 60 of 1,569 unmatched entity-like headings have any label that starts with the heading,
  and those are mostly false friends: "Heart" vs "Heart failure", "Leg", "Foot").
- The classification (generic facet / entity-like / group...) is a **heuristic** (`hclass.py`, regexes plus book context).
  I audited it by reading 22 random entity-like headings per book. The audited precision is in 3.3. Treat the entity-like
  counts as +/- 15%, and the by-type counts as rough until the Stage B LLM pass replaces the regexes.

## 1. Headline measurements

### 1.1 Headings per book

| Book | Sections | Tree nodes | Distinct strings (after cleaning) | Strings per level (L1 = part/chapter group, L2 ...) |
|---|---|---|---|---|
| Gray's | 614 | 732 | 522 | L1 9, L2 18, L3 208, L4 157, L5 112, L6 38, L7 13 |
| Tripathi | 446 | 541 | 475 | L1 15, L2 78, L3 278, L4 108 |
| Guyton | 478 | 578 | 461 | L1 15, L2 85, L3 362 |
| Davidson | 338 | 376 | 322 | L1 3, L2 35, L3 284 |
| Harrison | 505 | 573 | 573 | L1 68, L2 505 (chapters only) |
| Robbins | 212 | 241 | 218 | L1 30, L2 191 |
| Micro | 82 | 94 | 94 | L1 2, L2 10, L3 82 |
| **All** | **2,675** | **3,135** | **2,593 distinct keys** | |

Two facts shape everything below:

1. **Harrison, Davidson, Robbins, Guyton and Micro have no headings inside a section.** Their section bodies contain zero
   markdown sub-headings, so "Clinical features / Treatment / Pathogenesis" almost never exist as headings in those
   books. The generic facet headings live in Gray's and Tripathi, plus "Overview" everywhere.
2. **Only Gray's (1,588) and Tripathi (350) have in-body sub-headings** (Gray's 1,332 distinct, Tripathi 285 distinct).
   For Gray's these are the real anatomy vocabulary: 1,211 distinct entity-like names that are not in the ToC (Radial nerve,
   Carotid sheath, Femoral sheath, Superior orbital fissure...). The rules below apply to them too; counts in 3.x are ToC only
   unless said otherwise.

### 1.2 What the 3,135 headings are

| Class | Headings | Share of 3,135 | Share of 2,675 sections |
|---|---|---|---|
| Matches an ontology node today (strict) | 507 | 16.2% | 17.6% (471 sections) |
| Generic facet ("Overview", "Nerves", "Uses"...) | 460 (91 distinct strings) | 14.7% | 15.7% (420) |
| Front/back matter, letters, appendices, "Bibliography" | 103 (83 are Guyton "Bibliography") | 3.3% | 4.0% (incl. bare "Case N") |
| "Case N: <condition>" (Gray's) | 98 (+5 bare "Case N") | 3.3% | 3.7% |
| Positional sub-part ("Roof", "Second layer", "Anterior wall") | 19 | 0.6% | 0.7% |
| Procedural / statement headings ("How to find the thyroid gland") | 15 | 0.5% | |
| Topic headings (Approach to..., Principles of..., Clinical examination of...) | 222 | 7.1% | 7.8% |
| Group / hub headings ("Diseases of the aorta", part and chapter groups) | 348 | 11.1% | 7.3% (with the drug classes below) |
| Drug-class headings not in the ontology (Tripathi) | 137 | 4.4% | |
| **Entity-like, not in the ontology** | **1,221** | **38.9%** | **43.3% (1,158 sections)** |

Facet headings that match an ontology node by accident: 29 ("Nerves" and "Arteries" match an AnatomicalStructure node,
"Joints" matches a **TherapeuticAgent**, "Toxicity" a phenotype). So the facet filter must run before the entity match.

Entity-like headings (matched + unmatched, 1,728 plus 137 drug-class headings): **27% are in the ontology, 73% are missing.**
By book (matched / entity-like incl. matched): Harrison 40%, Tripathi 40% (with classes), Robbins 35%, Davidson 30%,
Micro 19%, Gray's 16%, Guyton 5%.

### 1.3 The missing entity-like headings, by likely type (heuristic)

| Likely type | Raw count | Where | Audited precision of the guess |
|---|---|---|---|
| AnatomicalStructure (incl. 18 body systems) | 270 | Gray's 252+18; Robbins 8; Davidson 2 | Gray's about 95% (21 of 22 sampled) |
| Structure or process (organs and their functions) | 41 | Guyton | mixed |
| PhysiologicalProcess | 307 | Guyton 275, Harrison 10, Davidson 8, Robbins 8, Tripathi 6 | about 86% entity-like for Guyton (19 of 22); typing about 75% |
| PathologicalCondition (incl. infections, syndromes) | 345 | Harrison 175, Davidson 58, Robbins 51, Micro 35, Guyton 19 | Harrison about 68% (15 of 22), Robbins about 73%, Davidson about 32% (7 of 22) |
| TherapeuticAgent, single drugs | 54 | Tripathi | about 50% (11 of 22; the rest are pharmacology topics) |
| TherapeuticAgent, classes ("Chelating Agents", "Lincosamide Antibiotics") | 137 | Tripathi | about 85% on a read of 20 |
| ClinicalPhenotype (symptom chapters) | 29 | Harrison Part 2, 57 chapters of which 22 already match | not audited; Part 2 is the symptom block by construction |
| EtiologicalAgent (organism) | about 6 | Micro headings with a parenthetical organism | organisms are almost absent from headings |
| Not typeable by regex | 173 + 20 | Harrison 81, Davidson 45, Robbins 47, Micro 20 | needs the LLM pass |

Adjusting each book's entity-like count by its audited precision gives **about 900 (range 800 to 1,000) genuinely new,
entity-grade concepts**, not 1,221. Davidson's headings are the least entity-like (Davidson's 113 are mostly care
processes and topics: "Palliative care", "Laboratory reference ranges in adults").

### 1.4 Other patterns (distinct heading strings, entity-like and group headings only)

| Pattern | Count | Notes |
|---|---|---|
| "X and Y" / "&" | 625 strings; 417 entity-like | Splittable with confidence: **42** (both halves match an ontology node, e.g. "Bleeding and Thrombosis", "Lumbar vertebrae and the sacrum"). 130 have one half matching. **245 have none and are mostly shared-head composites** ("Racial and Ethnic Disparities in Health Care", "Less Common Lymphoid and Myeloid Malignancies") that a naive split would break. |
| Comma lists | 96 | "Aviation, High Altitude, and Space Physiology" |
| Plural head noun | about 626 | Crude regex. Plural is not a matching problem (`merge_key` folds a trailing "s"); it signals a **class** ("Penicillins", "Anaemias", "Auditory ossicles"). |
| Parentheses | 98 (Tripathi 68) | 23 have an alias that matches a node; **13 match only through the alias** (main text does not); 7 have main and alias hitting two different nodes (merge candidates) |
| Abbreviation in parentheses | 32 (Tripathi 28) | "Amphotericin B (AMB)", "Dipeptidyl peptidase-4 (DPP-4) inhibitors" |
| Synonym list in parentheses | 16 | "5-Hydroxytryptamine (5-HT, Serotonin)", "Urolithiasis (renal calculi, stones)" |
| Possessive eponyms | 10 (Harrison 9) | "Alzheimer's Disease", "Wilson's Disease", "Bell's Palsy" inside a longer title. 167 ontology labels already have a possessive. |
| Colon with a facet word | 6 | "Heart Failure: Management", "Diabetes Mellitus: Diagnosis, Classification, and Pathophysiology" |
| "Case N: <condition>" | 103 headings, 98 conditions | **77 of 98 (79%) already match an ontology node** |
| Cranial nerve "[N]" suffix | 10 | "Vagus nerve [X]" |
| Tables | 79 "Table N.N" captions in 62 Gray's sections (Guyton 106, Micro 295, Harrison 18, Robbins 9; none in a heading except one "Branches (Table 7.7, pp. 729-730)") | Table rows survive as Gray's `###` per-muscle sub-headings, not as tables. No markdown tables exist in any section. |
| Gray's "In the clinic" boxes | 285 body headings | already used by `ontology/grays.py` for the 1,819 Gray's facts |

### 1.5 Existing coverage that the rules start from

- Sections with at least one certified fact: **1,143 of 2,676 (42.7%)**: Harrison 491/505, Gray's 227/614 (37%), Robbins 183/212,
  Tripathi 103/446, Davidson 91/338, Micro 47/82, Guyton 1/478.
- Sections with at least one mention-index entity: 2,564 of 2,676 (112 have none). But **there is no "primary topic"
  relation anywhere**: nothing says which one entity a section is about.
- Of the 471 section headings that match a node, only **219 (47%)** have a certified fact for that entity from that same section,
  and 326 (69%) from the same book. 31% match an entity that no fact of this book supports (a legitimate bridge, and the main
  precision risk).
- 119 of 507 matched headings (23%) match more than one node (Condition + Phenotype + Etiological...). The wanted type is
  present for 90% of Harrison matches, 92% of Gray's, 88% of Tripathi, 74% of Robbins, 67% of Davidson, and **11% of Guyton**
  (Guyton headings are processes, the ontology holds 9 Guyton facts).
- Wrong-type matches seen: "Pulmonary valve" matches a TherapeuticAgent node; "Joints" matches a TherapeuticAgent.
- Anatomy smoke set (14 questions, `eval/anatomy_smoke.jsonl`): the main concept of the question exists as an ontology node for
  **4 of 14** (Diaphragm, Radial nerve, Ureters, Common fibular nerve). It exists as a ToC or in-body Gray's heading for
  **11 of 14** (adds Inguinal canal, Proximal femur, Carotid sheath, Bronchopulmonary segments, Femoral triangle,
  Femoral sheath, Superior orbital fissure). Not a heading at all: Erb's palsy, Rotator cuff, and (only partly) the rectal veins.
- Gray's anatomy relations are **absent**: its 1,819 certified facts are clinical-box facts; `ontology/grays.py` tells the
  model "Do NOT extract normal anatomy". Gray's has 354 AnatomicalStructure nodes and 458 INVOLVES_STRUCTURE facts, no
  `part_of`, no innervation, supply, drainage, boundaries or contents.

## 2. Tiers used below (from `docs/graph_networking_plan.md`)

| Tier | Meaning | May reach an answer prompt? |
|---|---|---|
| T1 certified | LLM-extracted, verbatim quote found in the section, verifier passed (`status: CERTIFIED`) | Yes, only this |
| T2 derived | A deterministic rule over the ToC or over T1 facts (inverse, heading = concept, hierarchy) | No (navigation, display) |
| T3 inferred | LLM or similarity judgement, shown with evidence | No (navigation, display, retrieval hints) |
| navigation | Structure of the book itself (a facet, a position) | No |

New records go to a new file `data/graph/headings.jsonl` (and a loader `rag/headings.py` shaped like `rag/hubs.py`), never into
`data/ontology/clinical_ontology.jsonl`.

## 3. Rules

Each rule: statement, tier, expected count (this data), precision risk, cost, examples. Precision numbers marked "audit" come from
my reading of random samples (small, 20 to 22 each); the plan's own bar is 90 to 95% on 100 per layer before anything ships.

### 3.0 Order of evaluation for one heading (the decision list)

1. Strip numbering ("52 ", "37.", "Unit VI", "Chapter 15 "), fold ALL CAPS, keep the original string as `raw`.
2. Front/back matter, bare letters, "Appendix N", "Bibliography", "Acknowledgments": no concept.
3. "Case N: X": Rule 8.
4. Generic facet: Rule 3. **Before any entity match** (otherwise "Joints" links to a drug).
5. Positional sub-part, procedural or statement heading: composite name or navigation only.
6. Exact or relaxed match to an ontology node, type chosen by book context: Rule 1.
7. Group, class, topic heading: hub or topic node (navigation).
8. Otherwise entity-like and unmatched: Rule 2.

### Rule 1. A heading that matches an existing entity becomes the section's primary topic

- **Rule:** `section -- primary_topic --> entity` when the cleaned heading (or its parenthetical or alias part) has the same
  `merge_key` as a node. Stronger than a mention: at most one per section, and the heading is the evidence.
  If several nodes match, choose the type expected for the book (Gray's AnatomicalStructure, Tripathi TherapeuticAgent,
  Harrison/Robbins/Davidson/Micro PathologicalCondition, Guyton PhysiologicalProcess), else the better-connected node;
  keep the others as `same_label` (as `concepts.concept()` already does).
- **Tier:** T2 derived. `evidence` = section id, `method` = `heading-exact | heading-paren | heading-variant`. Never T1: a heading
  is not a clinical quote.
- **Expected count:** 507 strict matches (471 of 2,675 sections = 17.6%), +47 relaxed ("Oculomotor nerve [III]", "Diseases of the Aorta",
  "Heart Failure: Management") = about 550. Gray's in-body headings add 137 matched (111 distinct).
- **Precision risk:** medium. (a) Wrong type or wrong sense: 23% of matches hit more than one node; 23 are wrong-type (Joints, Pulmonary valve).
  (b) Generic labels: single-word matches like "Pain", "Imaging", "Cancer", "Shock", "Infections" are 126 non-Tripathi headings; these are
  right as hubs ("Shock" chapter is about shock) but must not be treated as the specific condition node. (c) Only 47% have same-section
  provenance. Mitigation: facet filter first; type tie-break by book; for single-word generic labels require the entity to have
  at least one fact in the same book, else store the link as `bridge`, not `primary_topic`.
- **Cost:** $0, about 0.5 day. Audit 100 links.
- **Examples:** Harrison "Tuberculosis", "Heart Failure"; Gray's "Diaphragm", "Ureters", "Liver", "Pleura"; Tripathi "Cabergoline",
  "Rifampin (Rifampicin, R)" (matches through the parenthetical); Robbins "Atherosclerosis", "Amyloidosis".

### Rule 2. An entity-like heading with no match becomes a new concept typed by book context

- **Rule:** create a concept `source: heading`, `tier: T3`, status CANDIDATE, minted id `MED:OKF/<type>/<slug>` (same scheme as
  the extractor), with a topic page that lists the section(s) and the parent chain. Type by context: Gray's AnatomicalStructure
  (OrganSystem if the heading ends in "system"), Tripathi TherapeuticAgent (class if the heading contains drugs, agents,
  antibiotics, inhibitors, blockers...), Harrison Part 2 chapters ClinicalPhenotype and the rest PathologicalCondition, Robbins and
  Davidson PathologicalCondition or AnatomicalStructure (organ chapters: "Ovaries", "Vagina"), Guyton PhysiologicalProcess, Micro
  PathologicalCondition (infection chapters) plus an EtiologicalAgent parsed from the parenthesis or the adjective
  ("Staphylococcal" gives genus Staphylococcus). Anything the regexes cannot type goes to the LLM; anything the LLM calls "topic"
  gets no entity node (Rule 3 style navigation topic).
  Heading concepts are **not entered into `facts()`**; they live beside it and, when a certified fact later names the same
  `merge_key`, they merge into the certified node (`plan_merges` logic) and the `source: heading` flag stays as a second source.
- **Tier:** T3. Navigation only. A heading existing proves the book discusses the topic, not any property of it.
- **Expected count:** 1,221 raw nodes (1,158 section leaves), about **900 after the audit** (Gray's 255, Guyton 290, Harrison 180,
  Robbins 85, Tripathi 60 incl. classes, Micro 35, Davidson 35). Gray's in-body adds about 1,250 distinct names (282 resolvable in the atlas
  crosswalk, which would type them with certainty).
- **Precision risk:** high without the LLM. Raw regex typing was right for roughly 50% (Tripathi), 32% (Davidson), 68% (Harrison). Typical errors:
  a care process typed as a condition ("Palliative care"), a pharmacology topic typed as a drug ("Idiosyncrasy", "Food value"), a
  statement heading typed as a structure. Fix: one batched LLM pass that sees the heading, parent path, book and chapter, and answers
  `{kind: entity|class|topic|facet, type, canonical_name}`. Canonical name removes "Heart Failure: Management" down to "Heart failure".
- **Cost:** about 1,600 headings (1,221 entity-like plus group/class and the 1,588 Gray's in-body ones in a second batch). 40 per call,
  about 130k input and 70k output tokens: **about $0.05 to $0.10**, $0.20 with retries and an adjudication pass. Effort 1.5 days with the audit.
- **Examples:** Gray's "Inguinal canal", "Femoral triangle", "Bronchopulmonary segments", "Proximal femur", "Pelvic floor";
  Tripathi "Chelating Agents", "Nonopioids", "Taxanes"; Harrison "Syncope", "Fatigue", "Altitude Illness";
  Guyton "Coronary Circulation", "Cerebrospinal Fluid System"; Robbins "Ovaries", "Cellular aging".

### Rule 3. A generic facet heading is a facet of its parent, never an entity

- **Rule:** if the cleaned heading is in a facet list, create no concept. Record `facet: <kind>` on the section and attach it to the
  parent's concept (`parent -- has_facet --> section`). A section search for "Innervation of the diaphragm" can then use
  facet = innervation under the concept "Diaphragm". Facet kinds: overview, anatomy-part (nerves, vessels, muscles, bones, joints, ligaments,
  lymphatics, venous drainage, arterial supply, innervation), clinical (in the clinic, uses, adverse effects, interactions, treatment, investigations),
  context (relationship to other regions, surface anatomy, key features, component parts, functions).
- **Tier:** navigation (T2 for the `has_facet` edge). Never a node, never an answer source.
- **Expected count:** **460 headings (14.7%), 420 sections (15.7%), 91 distinct strings.** Top: Overview 184 (all books except Harrison/Micro),
  Bibliography 83 (structural, Guyton), Functional anatomy and physiology 17 (Davidson), Muscles 15, Nerves 15, Innervation 9, Vessels 9,
  Uses 9, Joints 8, Bones 8, Conceptual overview 7, Component parts 7, Relationship to other regions 7, Key features 7. Gray's alone has 248
  (40% of its ToC) and 149 more in body headings; Tripathi 100.
- **Precision risk:** low for the 91 strings (high frequency, unambiguous); the risk is the **false negative that leaves a facet as an
  entity** and the false positive that kills a real concept ("Bone" is a facet under a region but a concept under "The Body"; "Peritoneum"
  repeats 3 times and is a real structure). Rule: a facet needs a parent concept, and a heading that is frequent but names a body part
  ("Fascia", "Meninges", "Peritoneum", "Diaphragm") stays an entity when it sits at region level. Check by hand the 30 strings that occur 3+ times.
- **Cost:** $0, 0.5 day (a curated list of about 100 strings, built from the frequency table, plus a book-specific regex).
- **Examples:** Gray's Nerves, Vessels, Innervation, Lymphatic drainage, Surface anatomy, Relationship to other regions, Key features;
  Tripathi Uses, Adverse effects, Interactions, Pharmacokinetics, Precautions and contraindications, Preparations, dose, administration;
  Davidson Functional anatomy and physiology, Investigations, Epidemiology; the Gray's positional parts ("Roof", "Floor", "Anterior wall",
  "Second layer", "Anterior compartment", 19 ToC + 31 body) are composite names: "Roof" under "Inguinal canal" becomes the
  structure "Roof of the inguinal canal" (T3), never a node called "Roof".

### Rule 4. The heading hierarchy gives subtopic and part-of links

- **Rule:** every parent-to-child step in `section_path` becomes `child -- subtopic_of --> parent` between concept nodes (the nearest
  ancestor that has a concept; skip structural levels such as "Regional anatomy"). Where both ends are AnatomicalStructure, also propose
  `part_of` as a **T3 candidate** (Thorax > Pleural cavities > Lungs).
- **Tier:** `subtopic_of` is T2 navigation, 100% faithful to the book's own nesting. `part_of` is T3 until Rule 9 finds a sentence
  that says it; the nesting is also used for non-part reasons ("Imaging > Nuclear medicine imaging" is a topic list).
- **Expected count:** 2,993 parent-child steps from chapter level down; 2,414 after dropping facet, structural and positional children.
  Gray's alone: 188 steps where both ends are entity-like (the `part_of` candidates, e.g. Back musculature > Superficial group of back muscles),
  plus roughly 1,500 more from the body-heading nesting (`###` under `##`). Harrison contributes 505 chapter steps and nothing deeper.
- **Precision risk:** `subtopic_of` none by construction; the cost is noise (a chapter node "Diseases of the aorta" is a hub, not a disease).
  `part_of`: estimate 85 to 90% for Gray's structure-under-region (the regional chapters are anatomical partitions), lower for systems.
  The 1,648 T3 `drug_class` and 196 `condition_hierarchy` edges in `hubs.jsonl` overlap; deduplicate by (child, parent).
- **Cost:** $0, 1 day. Reuses the `hubs.jsonl` record format (`hub_type: heading_hierarchy`).
- **Examples:** Gray's Lower Limb > Regional anatomy > Leg > Posterior compartment of leg > Nerves (Nerves is a facet: the edge is
  "Posterior compartment of leg has facet Nerves", not a structure called Nerves); Tripathi 38 Antiarrhythmic Drugs > Class I > Disopyramide.

### Rule 5. Split "X and Y" and plural headings, and read parenthetical aliases

- **Rules:**
  a. **Parentheses:** `Name (alias, abbreviation)` creates aliases of the concept `Name`: "Rifampin (Rifampicin, R)", "Amphotericin B (AMB)",
     "Measles (Rubeola)", "Systemic Sclerosis (Scleroderma)". An all-caps token of 2 to 6 characters is an abbreviation, other tokens are
     synonyms. If main and alias already hit two different nodes, emit a merge proposal (7 cases), never an automatic merge.
  b. **"X and Y" split:** only when both halves are 1 to 3 words and each half matches a node or an atlas name (42 strings); one half matching
     (130 strings) goes to the LLM; no half matching (245) stays as one composite concept. Shared-head forms ("Acute and Chronic Pancreatitis",
     "Benign and Malignant Diseases of the Prostate") must expand to "Acute pancreatitis", "Chronic pancreatitis": an LLM job, not a regex.
  c. **Plural / class heading:** a plural head noun ("Penicillins", "Anaemias", "Auditory ossicles") is typed as a class (hub); the members come
     from Rule 7. Singular matching is already handled by `merge_key`; add `_singular` forms (-ae, -i, -ys) from `rag/atlas.py` into the key
     for headings only, not into `merge_key` itself (that would re-key the whole ontology).
- **Tier:** (a) T2 when the alias is stated in the heading itself, the heading is the quote; apply to the matching key only after a human
  reviews the list (it is a synonym fact, not a clinical claim). (b) T2 for the 42 safe splits, T3 otherwise. (c) T3.
- **Expected count:** (a) 98 headings with parentheses, 32 with abbreviations, 16 with synonym lists, 13 newly matched through the alias, 7 merge
  proposals. (b) 42 + about 60 after LLM = about 100 split headings, giving about 220 half-concepts. (c) about 150 class-typed headings in the
  unmatched entity-like set.
- **Precision risk:** (a) low for Tripathi (author-supplied), but "Class I" style letters and "(Table 7.7, pp. ...)" must be filtered. (b) high for
  regex splits: 245 of 417 "and" headings would be mangled, hence the restriction. (c) medium.
- **Cost:** (a) $0, half a day. (b) $0.01 for about 130 ambiguous headings. (c) in the Rule 2 pass.
- **Examples:** "Insulin, Oral Hypoglycaemic Drugs and Glucagon" splits into 3 (Insulin matches); "Lumbar vertebrae and the sacrum";
  "Bleeding and Thrombosis"; "Diarrhea and Constipation" (two symptoms); "Systemic microbiology (infectious diseases)".

### Rule 6. The same heading in two books is the same concept (cross-book bridge)

- **Rule:** headings with equal `merge_key` (after dropping parentheses) in two or more books, excluding facets, link to one concept node.
  Near duplicates (equal token set after dropping disease, disorder, infection, acute, chronic, of, the) become `same_as_candidate` T3.
- **Tier:** T2 for identical keys; T3 for near duplicates. Never auto-merged into certified nodes.
- **Expected count:** **64 identical headings in 2+ books**, of which 37 already match a node (so 27 would be new concepts that now have two sections).
  71 near-duplicate groups. Pairs: Davidson-Harrison 17, Gray's-Robbins 12 (organ names), Davidson-Robbins 10, Harrison-Robbins 7,
  Guyton-Tripathi 3. That is 2.5% of 2,593 distinct strings: books name chapters differently, so heading identity finds few bridges.
  Real cross-book bridges come after Rule 1 and Rule 2 canonical naming and from the mention index, not from raw heading equality.
- **Precision risk:** medium for generic words ("Infection", "Bone", "Overview" excluded as facet); low for disease names.
- **Cost:** $0, 2 hours. Examples: "Glomerular diseases" (Davidson, Harrison, Robbins), "Acute kidney injury" (Davidson, Guyton, Harrison),
  "Fungal infections" (Davidson, Harrison, Robbins), "Irritable bowel syndrome", "Osteoarthritis", "Cardiac arrhythmias" (Davidson, Tripathi).

### Rule 7. Lists under a class heading give MEMBER_OF candidates with section evidence

- **Rule:** if a parent heading is a class (CLASSWORDS or typed class by Rule 2) and a child heading is a drug (ontology TherapeuticAgent or Rule 2
  drug), emit `child -- member_of_candidate --> parent` with `evidence = child section id` and `tier T3`. Reuses the existing `drug_class` hub kind.
  Same for organisms under a genus or family heading, and for conditions under "Diseases of X" (condition hierarchy).
- **Tier:** T3 navigation. **Never** propagate TREATED_BY, CONTRAINDICATES or CAUSES_ADVERSE_EFFECT from class to member, in either direction.
- **Expected count:** Tripathi alone: 69 parents with 2+ children, 244 child links; 134 class-to-drug pairs after removing pharmacology-principle parents,
  of which 102 children are already drug nodes. Hubs already hold 1,648 `drug_class` T3 edges (LLM, audited 95% on 20), so the new value is
  the **section evidence** and about 30 to 60 members not in the hubs file. Across other books the nesting is flat, so little else.
- **Precision risk:** medium: read of 10 pairs gave 8 correct. Wrong parents: "Notes on Individual Drugs" (a container), "Antiarrhythmic Drugs > Class III"
  (a class letter, not a drug). Require the child to be a single-word drug name or to match a drug node.
- **Cost:** $0 for the rule; $0.05 if the LLM adjudicates the 134 pairs. 0.5 day.
- **Examples:** Antimalarial Drugs > Primaquine; Anthelmintic Drugs > Pyrantel pamoate; Estrogens, Progestins and Contraceptives > Estrogens (Female Sex Hormones);
  Macrolide, Lincosamide, Glycopeptide... > Glycopeptide Antibiotics.

### Rule 8. "Case N: <condition>" maps the condition to its case section

- **Rule:** `condition -- illustrated_by --> case section` (Gray's clinical cases). The condition is Rule 1 if matched, else Rule 2 with type PathologicalCondition.
  Bare "Case N" headings (5) take the condition from the case's first line (LLM, optional).
- **Tier:** T2 navigation. The case section is not a source of general claims (it is one patient), and the certified Gray's facts already come from these cases
  (`ontology/grays.py` reads all "Clinical cases" sections whole).
- **Expected count:** 103 case sections, 98 named conditions, **77 already match a node (79%)**, 21 new conditions. Titles are often clinical
  scenarios, not diseases ("Case 3: How to examine the hand", "Case 5: Brachial plexus nerve block", "Case 5: Broken pacemaker", "Case 10: Venous access"); expect
  about 90 true conditions after review.
- **Precision risk:** low for matched ones, medium for the unmatched (procedures typed as conditions). Use the LLM kind field `condition | procedure | injury | structure`.
- **Cost:** $0 for the 77, about $0.01 for the rest. 2 hours.
- **Examples:** "Case 2: Extradural hematoma", "Case 1: Pulmonary embolism", "Case 6: Coarctation of the aorta", "Case 7: Aortic dissection", "Case 8: Pneumonia".

### Rule 9. Anatomy relations for Gray's (innervated by, supplied by, drains to, boundaries, contents, part of)

This is the one rule that adds clinical-grade content. It needs targeted LLM extraction with quote verification.

- **Why:** the 14-question smoke set is mostly anatomy relations (nerve supply of the diaphragm, boundaries of the inguinal canal, blood supply of the head of the femur,
  contents of the carotid sheath, venous drainage of the rectum, contents of the femoral sheath, structures through the superior orbital fissure). Nothing in the
  certified graph says any of them today, because the Gray's extraction was deliberately limited to clinical boxes.
- **Pipeline:** passages = heading-scoped, about 500 to 700 words (a `##`/`###` block with its heading path, never crossing a region), skipping figure-label
  paragraphs. One call per passage with a new anatomy addendum (mirror of `ontology/grays.py`'s `ADDENDUM`, inverted: normal anatomy only). The facts go through the normal
  gates: `reconciler` verbatim-quote check, negation check, `check_direction`, the DeepSeek verifier, `merge.py`, and multi-source merge. Output cap raised from 12 to 20 triples per call.
- **Minimal schema additions** (`ontology/schema.py`, `reconciler.TYPE_RULES`, `concepts.INVERSE`, `verifier` prompt):
  - `ClinicalRelation`: `INNERVATED_BY` (structure to nerve), `SUPPLIED_BY` (structure to artery), `DRAINED_BY` (structure to vein or lymph node/trunk), `BOUNDED_BY`
    (space/canal/region to its walls and borders), `CONTAINS` (space or sheath to what lies or passes in it; `rationale` carries "passes through"), `BRANCH_OF` (artery or nerve to its parent).
    Reuse the existing `part_of`. Optional second batch: `ATTACHES_TO` (muscle origin/insertion), `ARTICULATES_WITH`.
  - `TYPE_RULES`: all new predicates are (AnatomicalStructure, AnatomicalStructure), one direction only; the inverse wording lives in `concepts.INVERSE`
    ("innervates", "supplies", "drains", "bounds", "contained in", "has branch"). A wrong-direction fact is swapped by `check_direction`, as for INVOLVES_STRUCTURE.
  - `ClinicalFacet`: add `spinal_levels` (e.g. "C3-C5", "T4-T9") and `structure_kind` (muscle, nerve, artery, vein, bone, ligament, space, organ), so `INNERVATED_BY`
    can require a nerve-kind object without a new EntityType. No new EntityType is needed.
  - `eval/`: a `gold_triples` field for the 14 questions (about 40 triples written by hand from the `key_points`), and a `gold_sections` field.
- **Tier:** T1 certified if the quote verifies (same gate as every other fact); CANDIDATE otherwise. This is the only rule whose output may reach an answer.
- **Expected count:** Gray's text is 366k words outside 38k words of figure labels (and 56k words of clinic boxes already used). The clinic run produced about 32 facts
  per 1,000 words; anatomy prose is denser in relations. Planning figure: 15 to 20 raw facts per 1,000 words gives **5,500 to 7,300 raw, about 4,500 to 6,500 certified** at
  the file's 90% certified rate; Gray's would go from 227 of 614 sections with a fact (37%) to about 85 to 90%.
- **Cost:** about 600 to 800 calls. Input about 1.5M tokens ($0.42), output about 1.0 to 1.3M tokens ($0.42 to $1.20 depending on the output price), verifier about $0.20,
  a 40-section pilot about $0.10. **Total about $1.2 to $2.5 (plan on $2)**, 40 minutes at 6 workers. Effort 3 to 4 days with schema, tests, gold set and audit.
- **Precision risk:** medium. Gray's lists left/right and variants ("Medial and lateral circumflex femoral arteries" to two facts); eponymous and numbered names; clinical
  boxes mixed in the passage. The base gold precision of the pipeline is 0.89 to 0.94 (`reports/ontology_reinforcement_results.md`). Keep quotes short and require the subject
  and object to appear in the quote. Anatomy relations are frequently stated across two sentences ("The X arises from... It is supplied by..."): the extractor must name the subject in the
  quote or the fact is dropped (lower recall, higher precision, which is the right bias).
- **Examples to prove it on:** diaphragm and phrenic nerve, inguinal canal walls, femoral sheath compartments, carotid sheath contents, head of femur arterial supply,
  rectal veins and portal-systemic anastomosis, superior orbital fissure contents, ureter relations.

### Rule 10. Eponyms and synonym aliases

- **Rule:** keep a separate alias table `data/graph/aliases.jsonl` `{alias, canonical concept id or description, kind: eponym|abbrev|british|descriptive, source: heading|curated|llm, tier}`.
  Sources: parentheticals (Rule 5), `merge.DRUG_SYNONYMS` (29) and `registry.MEDICAL_SYNSETS` (72, of which 21 acronyms), the 167 ontology labels that already carry a possessive,
  and a one-off LLM list of about 400 eponym and descriptive pairs for anatomy and neurology. Used for **retrieval query expansion and concept search**, not as a merge.
- **How it fixes the Erb's palsy miss:** Gray's never says "Erb" (checked on the whole PDF in `docs/anatomy_fix.md`). It has "Brachial plexus" and a general injury box. An alias
  `Erb's palsy -> upper trunk (C5-C6) injury of the brachial plexus` makes the question retrieve the Gray's passage and lets the answer say what the book says, while the
  UI states "Erb's palsy is not named in this book". Rule 9 adds the certified supply facts (the upper trunk takes C5 and C6) that the aliased concept then reaches.
  It does not make the arm position or the "waiter's tip" appear, because the book does not state it; that has to come from Harrison/Davidson if they say it.
- **Tier:** T3 (retrieval hint, shown with its source). Heading-derived aliases (Rule 5a) T2. Never an answer fact.
- **Expected count:** 98 parenthetical headings (about 60 usable aliases), 10 possessive headings, 167 existing possessive labels, about 400 curated pairs. Also Gray's cranial
  nerve forms ("Vagus nerve [X]" = CN X = vagus).
- **Precision risk:** medium for the LLM list; wrong eponyms are common (Erb-Duchenne, Klumpke...). Human spot-check 100 pairs; ship only `checked` ones.
- **Cost:** about $0.05 for the LLM list plus 2 hours of review. Effort 1 day.

## 4. Summary table

| # | Rule | Tier | Expected count | Precision risk | LLM cost | Effort |
|---|---|---|---|---|---|---|
| 1 | Heading = existing node: primary topic | T2 | about 550 (471 sections strict) | medium (type twins, generic labels) | $0 | 0.5 d |
| 2 | Unmatched entity-like heading: new concept | T3 | about 900 (1,221 raw) + about 1,250 Gray's body names | high without LLM | $0.05 to 0.20 | 1.5 d |
| 3 | Generic facet: facet of parent | navigation | 460 headings, 91 strings | low | $0 | 0.5 d |
| 4 | Hierarchy: subtopic / part_of | T2 / T3 | 2,414 steps; 188 Gray's part_of candidates | none / 10-15% | $0 | 1 d |
| 5 | Split, plural, parenthetical alias | T2/T3 | about 100 splits; 98 parenthetical; 13 new matches; 7 merges | splits high, aliases low | $0.01 | 1 d |
| 6 | Same heading across books | T2/T3 | 64 identical + 71 near-duplicate groups | medium | $0 | 0.25 d |
| 7 | Class members (MEMBER_OF) | T3 | 134 pairs (102 already drugs) | medium | $0 to 0.05 | 0.5 d |
| 8 | Case-to-condition | T2 | 98 (77 matched) | low | $0 to 0.01 | 0.25 d |
| 9 | Gray's anatomy relations | T1 if quote verifies | 4,500 to 6,500 certified facts | medium | about $2 | 3-4 d |
| 10 | Eponyms and aliases | T3 / T2 | about 400 curated + 60 from headings | medium | about $0.05 | 1 d |

Top 5 by value: Rule 9 (the only one that answers questions), Rule 2 (about 900 concepts), Rule 1 (about 550 primary topics), Rule 3 (460 facet headings
removed from the entity pool), Rule 4 (2,414 hierarchy steps).

## 5. Recommended order

**Stage A: deterministic, $0, about 3 days.** Rules 3, 1, 8, 6 (identical keys), 5a (parenthetical aliases), 4 (`subtopic_of`). Write `data/graph/headings.jsonl`
(`heading_id, book, section_id, level, class, facet, concept_ids, parent_id, tier, method, evidence`), `rag/headings.py` loader, `eval/heading_metrics.py` (promote the
scratch scripts), and the **leak test**: no record from this file can reach `graph_block`. Audit 100 primary-topic links.

**Stage B: small LLM pass, about $0.15 to 0.30 plus audits, about 3 days.** Rule 2 (typing, canonical names, kind), Rule 5b (ambiguous splits), Rule 7 (class membership),
Rule 4 `part_of` candidates, Rule 10 alias table. Audit 100 per layer before any is shown in the UI. Run Gray's body headings in the same pass.

**Stage C: anatomy facts, about $2, about 4 days.** Rule 9 only after Stage A and B exist, so extracted subjects and objects resolve to heading concepts. Schema additions,
40-section pilot, gold triples, then the full run. Decide go or no-go on the pilot: certified precision at least 90% on 100 sampled facts and the smoke set recall below.

**Stage D: integration, about 3 days.** Concept topic pages (heading concepts with their sections and facets), "primary topic" chips, retrieval use as a section filter
(`search(..., section_ids=...)` already supports it) and query-time alias expansion. Behind a flag, with the answer prompt unchanged.

Total new LLM spend: **about $2.5 to 3.5**. The cost is engineering time and audits, not tokens.

## 6. Success metrics (measure with `eval/heading_metrics.py` after each stage)

| Metric | Baseline (2026-11-13) | After A | After B | After C | Gate |
|---|---|---|---|---|---|
| Sections with a primary-topic link to an existing node | 0 recorded (471 derivable, 17.6%) | 17.6% to 20% | same | same | |
| Sections with an entity-grade primary topic (existing or new concept; facets inherit the parent's) | 0% | about 20% (plus 15.7% inherited facets) | **about 70% (audit-adjusted) to 84% (raw) of the 2,568 eligible sections**; 100% including hub and topic nodes | same | at least 70% |
| Sections with no concept of any kind | 100% | 0 after hubs | 0 | 0 | 0 eligible |
| Heading concepts with at least 1 section | n/a | 100% by construction | 100% | 100% | 100% |
| Certified nodes with at least 1 heading link | 0 | about 460 of 20,342 (2%) | about 4 to 5% | | report only; headings fix the section side, the mention index already links 8.5 times more |
| Cross-book concepts (2+ books) | 12.1% of certified nodes | +64 identical headings | +150 to 250 after canonical names | | no regression |
| Generic facets promoted to an entity | n/a | **0** | **0** | **0** | hard gate |
| Leaf share (degree 1 nodes), certified view | 68.9% (earlier measurement) | unchanged | unchanged | Gray's structure nodes mostly gain 3+ edges | report certified and T1+T2 views separately; new heading concepts are mostly leaves, do not hide this |
| Gray's sections with at least 1 certified fact | 227 of 614 (37%) | same | same | at least 85% | at least 80% |
| Anatomy smoke: main concept present as a node | 4 of 14 | 4 of 14 | **11 of 14** | 12 of 14 | |
| Anatomy smoke: gold triples found in certified facts (to be written) | about 0 | 0 | 0 | **at least 60%** of about 40 | at least 50% |
| Anatomy smoke: key points (existing judge) | 29 to 30 of 34 | same | same | at least 31 of 34 without regressing Harrison/Davidson questions | no regression |
| Erb's palsy | miss | miss | alias table retrieves the brachial-plexus passage | answer says what Gray's says | answers without invented "waiter's tip" unless a book states it |
| Link precision (100-sample audit per layer) | n/a | at least 90% primary topic, 99% facet | at least 90% new concept type, 90% class membership | at least 90% certified (existing gold bar 0.89-0.94) | no UI display below the bar |
| Non-T1 records reaching `graph_block` | 0 | 0 | 0 | 0 | hard gate, unit test |

## 7. What must never reach answers

- Anything from `headings.jsonl` of tier T2, T3 or navigation: primary topics, new heading concepts, facets, `subtopic_of`, `part_of` candidates, `member_of_candidate`,
  `same_as_candidate`, case links, aliases. "Section X is about Y" is not "Y does Z".
- A heading concept that has no certified fact must never be rendered as if the book said anything about it other than "discussed in".
- No propagation of TREATED_BY, CONTRAINDICATES, CAUSES_ADVERSE_EFFECT or CAUSED_BY from a class heading to a member, from a parent heading to a child, or from a group
  chapter ("Disorders of the Adrenal Cortex") to a condition inside it. No inverse or roll-up created from a heading path.
- A facet heading is never an entity and never a subject or object of a fact. "Nerves under Posterior compartment of leg" is not "Nerves".
- An alias is a retrieval hint: do not let it make an answer assert that the book names the eponym ("Erb's palsy" is absent from Gray's).
- Rule 9 facts reach answers only when `status: CERTIFIED` (quote verified in the passage and verifier pass); CANDIDATE anatomy facts follow the existing rule for candidates.
- Case sections: one patient is not a general statement.
- Guyton "Bibliography" and any other structural heading never become concepts or search hits.

## 8. Open items and caveats

- The classifier is heuristic; the audit samples are 22 per book. Stage B replaces the regexes with an LLM label and a 100-item audit per class.
- 1,211 Gray's in-body names and Tripathi's 285 body headings are counted in part only; the full numbers need the body-heading pass.
- Harrison (3.9M words, 505 chapters, no inner headings) and Davidson/Robbins/Guyton/Micro get one concept per chapter and nothing deeper from headings. Deeper structure
  there needs body-text extraction, which is outside this plan.
- Graph metrics elsewhere (`docs/graph_networking_plan.md`, 18,831 nodes) were measured on an earlier snapshot; the ontology now has 20,342 nodes and 25,902 certified facts.
- 29 facet strings and several generic single-word labels (Pain, Cancer, Shock, Imaging, Infections) need an explicit "hub, not the specific condition" flag.
