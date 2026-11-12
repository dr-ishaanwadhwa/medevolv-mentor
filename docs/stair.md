# STAIR workflow (owner: Hardik)

> **Status (2026-11-12): dropped from the demo, kept as future work.** The dataset, training script and Kaggle
> notebook are complete but untrained. The app shows STAIR only with `EXPERIMENTAL=1`.

STAIR = a fine-tuned LLM that answers a question with the **ToC title** of the section that contains the answer.
We train it in two stages so prompts stay ~750 tokens (fits 8 GB GPUs):

| Stage | Prompt | Answer |
|---|---|---|
| A | question + the book's chapter list (78 for Tripathi) | chapter title |
| B | question + that chapter's section list | section title (path below the chapter) |

At demo time both stages use **constrained decoding** over the same lists, so STAIR can only output titles that exist.

## Pipeline

```bash
# 1. OKF bundle with a full ToC (Tripathi needs the font-based rebuilder; ~17 s)
python -m ingest.font_toc data/books/978-93-5025-937-5.pdf --book-id tripathi \
  --title "Essentials of Medical Pharmacology (7th ed.)" --subject Pharmacology \
  --isbn 978-93-5025-937-5 --parent-pattern '^(Section \d+:|Appendices$)'

# 2. Question -> section pairs (LLM-generated, resumable). Use LLM_BACKEND=oci for quality.
python -m stair.make_pairs --book tripathi --level section --per-section 10      # 447 targets
#   smoke test: add --limit 5 ; chapter-level variant: --level chapter (78 targets)

# 3. Two-stage chat dataset + label lists
python -m stair.build_dataset --book tripathi --level section

# 4. Train (Kaggle T4 / RTX laptop) -- run the speed test first
python stair/train_unsloth.py --data stair/data/tripathi --out stair/adapters/tripathi --max-steps 100
python stair/train_unsloth.py --data stair/data/tripathi --out stair/adapters/tripathi
```

## Measured so far (2026-11-07, local llama3.2:3b generator)
- Pair generation (local llama3.2:3b, 3 passages/section): 3,952 questions for 446 of 447 sections;
  27 dropped by the copy / eval-overlap guards.
- Dataset: **6,972 train / 886 val** examples (stage A 3,506, stage B 3,466), median 737 tokens,
  **3.09 M tokens per epoch**.
- At an assumed ~500 tok/s on a T4 that is **~1.7 GPU-h per epoch → 3 epochs ≈ 5 h**, inside one Kaggle session.
  Replace with the real number from the 100-step test.
- Baseline to beat (vector search, 446 held-out questions, all 5 books indexed): chapter@1 76.7%,
  **section@1 65.5%**, section@3 84.3%.

## Quality guards built in
- Questions sharing **8+ consecutive words** with their source passage are dropped (paraphrase, don't memorise text).
- Questions too similar to `eval/questions.jsonl` are dropped, so STAIR never trains on the evaluation set.
- One question per target is held out into `val.jsonl`.
- The user (medical domain expert) spot-checks ~30 random pairs before the full training run.

## Rules
- `stair/pairs/`, `stair/data/`, `stair/adapters/`, `*.gguf` are git-ignored. **Never publish adapters or weights**
  — a model trained to memorise a copyrighted book carries that book. Kaggle datasets holding these files stay private.
- Publish code, method and eval numbers only.

## Still to build
- `stair/serve.py`: merge LoRA → GGUF → llama.cpp/Ollama with a grammar (or trie) restricting output to `labels.json`.
- `stair/evaluate.py`: Recall@1 for chapter and section on `val.jsonl` + `eval/questions.jsonl`, vs vector search.
