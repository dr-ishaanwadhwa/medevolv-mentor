# Atlas coverage plan (plan only; nothing built, no code or data changed)

Date 2026-11-14. Scope: the "View in 3D" links from ontology structures and conditions to the human-atlas / BodyParts3D models.
Demo 2026-11-17, so what follows is ordered by what can be finished and audited by 2026-11-15.

## 1. Baseline re-measured on current main

Same measurement as the first build, run against main's `rag/atlas.py`, `data/graph/atlas_crosswalk.jsonl` and certified `facts()`.

| Measure | First build | Now |
|---|---|---|
| AnatomicalStructure entities linked | 106 / 354 (30%) | **113 / 354 (31.9%)** |
| Link methods | 89 exact, 17 embedding+LLM | 98 atlas-name, 4 synonym, 4 synonym-parts, 1 atlas-pair, 6 embedding+LLM |
| Conditions with INVOLVES_STRUCTURE (certified) | 295 | 295 |
| ...of which with at least one linked structure | 113 (38%) | **118 (40.0%)** |
| INVOLVES_STRUCTURE facts whose structure is linked | not measured | 159 / 458 |
| Conditions partly linked (some structures linked, some not) | not measured | 39 |

The "115" quoted in the request is the count under a different key; I get 113 by merge-key. Against all 5,001 condition labels
only 2.4% have a link, and that is correct: most conditions are systemic (see section 5).

## 2. Why the 241 unlinked structures are unlinked

A sonnet subagent classified every unlinked label against the 3,432 atlas concepts (names and FMA ids). Counts below are the agent's
calls; I audited 28 of the 136 "b" rows and the "a" and "d" rows myself (section 6 gives the precision I measured).

| Category | n | Meaning | Examples |
|---|---|---|---|
| a. Present under another name | **5** (3 usable) | Same structure, other wording | Anterior interventricular artery = anterior interventricular branch of left coronary artery (FMA3862); Iliotibial band = iliotibial tract (FMA51048); Intercostal arteries ~ posterior intercostal arteries (loose). "Nerve" and "Arteries" also match, but they are whole-category concepts that the build deliberately refuses to link |
| b. Absent, honest modelled parent | **136** | A parent or container is modelled | Greater trochanter -> femur (part_of); Supraspinatus tendon -> supraspinatus (tendon_of); Internal pudendal artery -> internal iliac artery (branch_of); Colon -> large intestine (part_of) |
| c. Absent, no sensible stand-in | **84** | Nothing modelled that is the structure or its parent | Ulnar, median, radial, sciatic, facial nerves; brachial plexus; uterus; thyroid gland; thoracic duct; latissimus dorsi; lymph node groups |
| d. Not really a structure | **16** | Bad typing | Intima, growth plate, pelvic inlet, synovial joints, lymph nodes, superficial veins, tissue layers of the scalp |

By kind (all 241): nerve 43, bone/joint 43, space/region 36, organ 34, ligament/tendon 26, artery 18, other 17, muscle 10, lymphatic 9, vein 5.
Of the 84 "c", 41 are nerves and 8 are lymphatics: BodyParts3D has no peripheral-nerve trunks, plexuses or lymph node groups.
Weighted by use in INVOLVES facts (299 uses among the unlinked structures): a 6, b 160, c 116, d 17.

What this says: **name matching is exhausted** (about +3 structures). The remaining headroom is almost entirely category b, which is a
fallback to a parent, not a match. Category c (35%) is a hard limit and the demo must not pretend otherwise.

Of the 136 "b" rows by relation: part_of 70, bounded_by 39, region_containing 17, tendon_of 6, branch_of 4. The relation labels are the
agent's judgement; the first stage below replaces them with official tables.

## 3. Why the 177 unlinked conditions are unlinked

All 177 (295 - 118) already have INVOLVES_STRUCTURE facts, so for them there is no extraction gap. It is a crosswalk gap, and by the
categories above their structures break down as: 140 have one structure, 23 two, 14 three or more. Routes if each category-b structure
fell back to its parent:

| Route | Conditions newly linked (of 177) |
|---|---|
| a-gain only | 2 |
| a + tier 1 fallbacks (part_of, branch_of, tendon_of: 80 structures) | **55** |
| a + tier 1 + tier 2 (bounded_by, region_containing: 56 more) | 101 |
| No route (their structures are all c or d) | 76 |

The real extraction gap is on the other side. Gray's contributes 473 conditions; 283 have an INVOLVES_STRUCTURE fact and about 190 do not.
Examples that are plainly local: Skull fracture, Femoral neck fracture, Shoulder dislocation, Recurrent laryngeal nerve damage, Atrial septal defect,
Subclavian artery stenosis, Serratus anterior muscle paralysis. The 4,500 other conditions are not Gray's and mostly systemic. A better headline
metric than "% of 295" is therefore **Gray's conditions with a 3D link**: 118 / 473 = 25% today.

## 4. Options, with expected gain, cost and precision risk

| # | Option | Expected gain | Cost | Precision risk |
|---|---|---|---|---|
| A | Better normalisation, TA/FMA synonym tables | Structures +3 (1%); conditions +2. Exhausted: the build already does plural, "the", word order, "muscle"/"bone", hyphen, side and curated synonyms | about 1 h, $0 | Low. Keep refusing whole-category concepts |
| B | Nearest *modelled ancestor* fallback, tier 1 only (part_of / branch_of / tendon_of, child -> parent, one hop), shown as "Closest model: X" | Structures 113 -> about 193 (55%); conditions 118 -> about 173 (59% of 295; Gray's 37%) | Needs FMA/TA part-of and branch tables (below) or the agent's 80 rows verified; DeepSeek or sonnet check of 80 pairs under $0.10; 3-4 h | Medium, fully controllable. My audit of tier-1 rows: about 90% honest, so it needs the gate in section 6 |
| C | Use the new anatomy relations (BRANCH_OF / part_of) to bridge conditions -> structure -> modelled parent | Only **9** of the 241 unlinked structures reach a linked ancestor (6 part_of, 3 BRANCH_OF), 11 of the 177 conditions. Subset of B, but with certified quotes. Example: Extradural hematoma -> Middle meningeal artery -> Maxillary artery | Free once merged; the facts are hidden from `facts()` by design, so this needs an explicit, read-only `anatomy_facts()` use in `rag/atlas.py` | One of the 9 is not an honest stand-in (Sympathetic trunk part_of Posterior mediastinum). Branch hops stay in the same vessel family; stop at one hop |
| D | INVOLVES_STRUCTURE gap-fill for Gray's conditions that have none (about 190) | About 50-60 more conditions with a 3D link after A+B (roughly half get a structure, most of those linkable) | Targeted extraction with the existing certified pipeline; about $0.3-0.6 DeepSeek (the anatomy run was $1.1 for about 1,200 passages); 1 day with audit | Medium: it needs the same verbatim-quote and verifier gates, plus a "local condition" rule |
| E | Tier-2 fallbacks (bounded_by, region_containing: 56 structures) | +46 conditions (101 vs 55) | same as B | **High**: my audit finds about 55% honest. Joint -> one of two bones, Ischio-anal fossa -> external anal sphincter, Saphenous opening -> great saphenous vein, Medial longitudinal arch -> talus |
| F | Region fallbacks for absent plexuses and nerves ("brachial plexus region") | Would touch about 41 nerve entities | High effort, no data to compute the region | **Very high**; do not build for the demo |
| G | LLM check for ambiguous name matches | +0 to 3 (only about 3 real candidates remain) | $0.01 | Low; fold into B's verifier |

The official FMA part-of and IS-A tables ship with the BodyParts3D archive (`ATTRIBUTION.md` lists "IS-A and PART-OF concept, element, and inclusion tables from
the same archive"); the atlas catalogue itself only holds mesh sets, which give generic IS-A parents ("segment of artery") and cannot say part-of vs
branch-of. Fetching that archive is a download, so it needs your approval before it happens.

## 5. What must never be shown

- A wrong-parent or wrong-direction fallback: a parent standing in for a child is allowed ("closest model: femur" for the greater trochanter);
  the reverse is not; no "coronary artery part_of aorta" (it is a branch). Branch fallbacks only inside the same vessel or nerve family, one hop.
- Nerve-to-bone, organ-to-unrelated-neighbour or joint-to-single-bone stand-ins (tier 2). Fallbacks that change the meaning: a stand-in for the
  *lesion site* is not the site.
- A condition link for a **systemic** condition. Some are shown today, by what the fact says, but are misleading in a 3D view: tuberculosis
  (lumbar vertebra), peripheral vascular disease, osteomyelitis, pneumonia, stress fracture, muscle tear, ovarian cancer, hepatic cirrhosis,
  temporal arteritis, tumor embolus, intermittent claudication, metastatic lesions in liver; and the fallback route adds more (cystic fibrosis
  -> distal bronchi -> tracheobronchial tree). A "local condition" rule (curated list plus a one-time classification of every condition that has
  a link, shown only when the fact names a single site) must run before coverage grows.
- Category-d items (tissue layers, planes, junctions), whole-category concepts ("nerve", "artery"), and anything that reads as a clinical claim:
  the link stays navigation, and the fallback label must say so ("closest model").
- Mention, hub, crosswalk or co-mention layers as clinical claims, as before.

## 6. Recommended order, targets, and the gate

**Gate for anything shown: at least 95% precision on a seeded audit of at least 60 links per tier (all of them if the tier is smaller), by me
and a sonnet pass independently; a failed audit means the tier stays hidden, not tuned until it passes.**

| Stage | What | Structures linked | Conditions with a link (of 295) | Cost | When |
|---|---|---|---|---|---|
| 0 | Option A (3 synonyms) plus the systemic-condition guard and an audit of the 118 shown conditions | 113 -> 116 (32.8%) | 118 -> about 105-110 after removing systemic ones (an honest drop) | $0 to $0.05; 2-3 h | Nov 14-15 |
| 1 | Option B tier-1 fallback with FMA tables (and option C for the certified 9), "Closest model: X" in the UI | 116 -> about 196 (55%) | about 105 -> about 160 (54%); Gray's about 34% | under $0.15; 4-6 h incl. audit | Nov 15, only if the audit passes; otherwise stop at Stage 0 |
| 2 | Option D gap-fill for the Gray's conditions without INVOLVES, then link through stages 0-1 | unchanged | +50 to +60 conditions with a link | $0.3-0.6; 1 day plus audit | after the demo (Nov 18+) |
| not planned | Option E (tier 2), Option F (regions) | | | | do not ship |

Top three steps if time is short: (1) Stage 0's systemic guard, because it protects what is already live; (2) Stage 1 tier-1 fallback, the
only cheap step that moves the numbers a lot (conditions 40% -> about 55-59%); (3) Stage 2 gap-fill. Ceiling to keep in mind: the 84
category-c and 16 category-d structures (about 100 of 354, 28%) and the 76 conditions whose structures are all c/d will not link, so the realistic
end state is about 55% of structures and about 60% of INVOLVES conditions, not 100%.

## 7. Demo-safe examples today (no fallback needed)

Aortic dissection (aorta, celiac trunk, mesenteric arteries), Pituitary macroadenoma (optic chiasm, pituitary gland), Deep vein thrombosis
(femoral, popliteal veins), Subclavian steal syndrome (subclavian, vertebral arteries), Epiglottitis. Extradural hematoma -> Middle meningeal
artery has no model; it only links after Stage 1 (as Maxillary artery, labelled "closest model"), so keep it out of a live demo unless that
stage ships.

Method notes: the structure categories and relations come from one sonnet pass with my audit on top; the bridge and gain numbers are computed
on main's data and the `anatomy-relations` worktree's `data/ontology` (read-only, 2,643 certified relations; 977 are BRANCH_OF or part_of between
structures). Scratch files are in the session scratchpad, not in the repo.

## 8. Stage 0 outcome (14 Nov)

- Synonyms: anterior interventricular artery → FMA3862, iliotibial band → FMA51048. Structures linked 113 → 115.
- Guard: conditions with a 3D link 120 → **65** (68 classified local, then fixes below). DeepSeek labels: 68 local,
  49 misleading_site, 3 multi_site; cost ≈ $0.006.
- Audit 1 (builder, 72 "local"): 94.4%, failed; 4 moved to hidden (nerve injuries shown on denervated muscle, pelvic kidney).
- Audit 2 (independent reviewer, 68): **92.6%, failed**. Fixed by rule, not by tuning one case at a time:
  - signs shown on a denervated target muscle are hidden (Trendelenburg's sign, diaphragmatic paralysis, complete ptosis);
  - `LESION_ONLY` restricts three conditions to their lesion structure (pituitary macroadenoma → pituitary gland, not the
    compressed optic chiasm; aortic dissection and dissecting thoracic aneurysm → aorta, not branch or landmark arteries).
- After the fixes every remaining condition passed the independent reviewer; 15 borderline passes are listed in its report
  (e.g. coarctation highlights the whole aorta, ureteric stone the whole ureter). A third audit on a fresh reviewer is the
  next gate before Stage 1.
