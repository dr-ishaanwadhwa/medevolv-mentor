# Case diagrams: PaperBanana evaluation and what we shipped instead

_2026-11-13. Reviewed PaperBanana at commit `9ceea03` (cloned to `~/Projects/third_party/PaperBanana`). The code was read but none of it was run._

## What PaperBanana needs

| Question | Finding (from the code) |
|---|---|
| Licence | Apache-2.0. Fine to use. |
| Pipeline | Retriever → Planner → Stylist → Visualizer → Critic. The Critic and Visualizer loop for up to 3 rounds (`utils/paperviz_processor.py`). |
| Models | Text and vision default to `gemini-3.1-pro-preview`. Images default to `gemini-3.1-flash-image-preview` (`configs/model_config.template.yaml`). Image models can also go through OpenRouter, OpenAI `gpt-image`, Atlas or LiteLLM. The local and Ollama routes are text-only; the Visualizer rejects them (`assert_not_local_openai_image_model`). **No free or local image path exists.** |
| Keys | `GOOGLE_API_KEY` or `OPENROUTER_API_KEY`. Both are set in our `.env`, but image generation on either one is billed. |
| Calls per diagram | 1 candidate in `demo_full` mode makes up to 7 Pro text/vision calls (retriever, planner, stylist and 3 critics, some carrying images) and up to 4 image generations. The skill's CLI defaults to `--num-candidates 10`, which is 10× that. |
| Cost / latency | Estimated at roughly $0.2–0.5 and 1–3 minutes per diagram, with retries on rate limits. This is not measured, because we did not spend money to measure it. |
| Headless / Docker | Yes. Python 3.12 slim image, CPU only. It still pulls in google-genai, openai, anthropic, gradio, streamlit, pyarrow and matplotlib. |
| Reference data | Retrieval needs PaperBananaBench downloaded from Hugging Face, which holds **computer-science** paper figures, so its style guides are NeurIPS-specific. |
| Third-party data flow | The method text sent to it would be the answer plus verbatim textbook quotes, and it goes to Google or OpenRouter. |
| Code risk | `utils/plot_execution.py` runs LLM-written matplotlib code with `exec` (plot task only). The diagram task doesn't use it. |

## Why we didn't integrate it

1. **The image model writes the text in the picture.** Drug names, doses and test names are drawn by a diffusion model. They can come out misspelled or invented, and nothing in the image can be traced back to a certified fact. For a medical study tool, that rules it out as the default.
2. Every diagram costs money, takes minutes, and copies corpus-derived text to a third party.
3. Its reference set and style guides are for ML papers, not clinical algorithms.

The user chose a deterministic diagram over PaperBanana on 2026-11-13.

## What shipped: `rag/diagrams.py`

* **Case flowchart:** condition → presentation → differentials → workup → treatment, with treatment split by line (first, second, adjunct, refractory, supportive). Strict contraindications appear as a red warning column and cautions in amber.
* **Drug mechanism:** drug → molecular targets → what it treats, its adverse effects, and where it is contraindicated. This kind is chosen when the question names a drug and asks about mechanism, adverse effects or contraindications.
* Every box is one **CERTIFIED** fact's label with a numbered source (book, chapter, pages). The only other text is fixed section headings. Boxes the answer mentions are drawn bold.
* The output is Graphviz DOT, which `st.graphviz_chart` renders in the browser. The VM needs no graphviz binary and no network access.
* **Caching:** diagrams are cached on disk under `data/ontology/diagrams/`, which is git-ignored. The cache key includes the ontology file's mtime, so re-certifying facts invalidates old diagrams.
* **On demand:** diagrams draw only when the user clicks "📊 Generate diagram" (`diagrams.render(st, question, answer_text, condition=...)`). Building one takes a few hundredths of a second, so no background thread is needed.
* **Degrades quietly:** with no ontology, no matching condition or drug, or any error, there's no button, no diagram and no exception.

Samples: `data/ontology/diagrams/samples/{mi_case,tb_case,isoniazid_moa}.{dot,html}` (git-ignored).

If image-model polish is wanted later, the right input is this DOT/spec rather than free text. Anything it draws would then need to be checked against the certified labels.
