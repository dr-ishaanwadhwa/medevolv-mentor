# Demo click-path: v2 web app (presentation, 17 Nov)

Live: https://v2.130-210-60-153.sslip.io   ·   Fallback (unchanged): https://mentor.medevolv.in (Streamlit)

Measured on the live host, 16 Nov (curl + built-in browser):
- Ask, pheochromocytoma case: 3/3 answered, phenoxybenzamine, 2 citations each, 3.2–4.2 s warm.
- Why was I wrong (picked propranolol): 3/3 verdict = B phenoxybenzamine, 6 citations, 3 viva questions.
- Concept page + 3D resolve: 3/3 HTTP 200. No console errors on the atlas.
- First request after an API restart: ~11 s (models warm at startup). Warm it with one question before going on stage.

## Steps
1. **Ask** (`/`): tap the pheochromocytoma demo card. Point at the live step trace, then the answer.
   Tap a citation chip `[1]`: the drawer shows book · chapter · pages and the excerpt. "N more retrieved, not cited" = honesty.
2. **How this answer was made**: expand; 10 steps incl. "Citation check: every [n] checked against the evidence".
3. **Decline**: tap the cricket card: designed "the books don't cover this" state, not a hallucination.
4. **Why was I wrong?** (`/why`): "Try an example" -> picked A Propranolol -> submit.
   Verdict: B Phenoxybenzamine, "why yours is wrong" with citations, 3 viva questions (tap one -> opens in Ask).
5. **Explore** (`/explore`): search "pheochromocytoma" (richest graph) or "optic chiasm" -> concept page:
   where the books discuss it, linked from / links to (tier tags), local graph (click a node to navigate, Back works).
6. **3D**: on Optic chiasm, the compact 3D panel -> "Open in 3D Atlas" -> highlighted structure, side panel with the
   textbook sections and the "Navigation only, not a clinical claim" note.
7. **Mobile**: open the same URL on a phone: bottom tabs Ask · Why · Explore · 3D.

## If something fails on stage
Switch tabs to https://mentor.medevolv.in and run docs/demo_script.md steps (same backend engine).
