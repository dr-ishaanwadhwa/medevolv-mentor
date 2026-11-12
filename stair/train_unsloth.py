"""Fine-tune STAIR (Mistral-7B-Instruct + QLoRA) on stair/data/<book>/ with Unsloth.

UNTESTED HERE (no CUDA GPU on the dev Mac). Written for a Kaggle T4 notebook or an RTX laptop under WSL2.
Run the 100-step speed test first (--max-steps 100) and note tokens/s + peak VRAM before a full run.

Kaggle cell:
  !pip install -q unsloth
  !python stair/train_unsloth.py --data stair/data/tripathi --out stair/adapters/tripathi --max-steps 100

Notes
- Mistral-7B-Instruct v0.2's chat template has no system role, so the system prompt is folded into the
  first user turn.
- Loss is computed on the answer (the title) only, not on the long ToC listing in the prompt.
- Checkpoints every --save-steps so a Kaggle session timeout (~12 h) loses little; resume with --resume.
"""
import argparse
import inspect
import json
import random
import time
from pathlib import Path


def load_rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def to_text(row: dict, tokenizer) -> str:
    msgs = row["messages"]
    system = next((m["content"] for m in msgs if m["role"] == "system"), "")
    turns = [m for m in msgs if m["role"] != "system"]
    if system:
        turns[0] = {"role": "user", "content": system + "\n\n" + turns[0]["content"]}
    return tokenizer.apply_chat_template(turns, tokenize=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="unsloth/mistral-7b-instruct-v0.2-bnb-4bit")
    ap.add_argument("--max-seq", type=int, default=2048)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--max-steps", type=int, default=-1, help="set e.g. 100 for the speed test")
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--save-steps", type=int, default=200)
    ap.add_argument("--eval-steps", type=int, default=400)
    ap.add_argument("--eval-samples", type=int, default=150,
                    help="fixed random subset of val.jsonl for in-training loss (full val is too slow)")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--export-gguf", action="store_true",
                    help="also merge the adapter and write a q4_k_m GGUF for `python -m stair.serve install`")
    a = ap.parse_args()

    # Unsloth must be imported BEFORE trl/transformers/datasets, or its patches only partly apply.
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    import torch
    # T4 has no bfloat16: load in float16 so the weights match fp16 training (newer Unsloth may default to bf16,
    # which makes the fp16 grad scaler fail with "not implemented for 'BFloat16'").
    use_bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if use_bf16 else torch.float16
    model, tokenizer = FastLanguageModel.from_pretrained(a.model, max_seq_length=a.max_seq, load_in_4bit=True,
                                                         dtype=dtype)
    print("precision:", dtype)
    if not use_bf16:
        # The pre-quantised checkpoint keeps its unquantised layers (norms, embeddings, lm_head) in bfloat16, and
        # Unsloth's fast grad-clipping groups gradients by those dtypes, which the fp16 grad scaler rejects. Cast
        # every remaining bfloat16 tensor to float16 (4-bit weights are untouched: they're uint8).
        n_cast = 0
        for t in list(model.parameters()) + list(model.buffers()):
            if t.dtype == torch.bfloat16:
                t.data = t.data.half()
                n_cast += 1
        print("cast bfloat16 -> float16 tensors:", n_cast)
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=32, lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=13,
    )
    if not use_bf16:
        # fp16 mixed precision needs the TRAINABLE (LoRA) weights in float32: the grad scaler cannot unscale
        # half-precision gradients, and newer Unsloth creates LoRA weights in bfloat16. Base weights stay 4-bit.
        for prm in model.parameters():
            if prm.requires_grad and prm.dtype != torch.float32:
                prm.data = prm.data.float()
    trainable = {str(prm.dtype) for prm in model.parameters() if prm.requires_grad}
    print("trainable params:", sum(prm.numel() for prm in model.parameters() if prm.requires_grad),
          "dtypes:", trainable)

    data = Path(a.data)
    train = Dataset.from_list([{"text": to_text(r, tokenizer)} for r in load_rows(data / "train.jsonl")])
    val_rows = load_rows(data / "val.jsonl")
    random.Random(13).shuffle(val_rows)
    val = Dataset.from_list([{"text": to_text(r, tokenizer)} for r in val_rows[:a.eval_samples]])

    # TRL renamed arguments across versions (max_seq_length -> max_length, tokenizer -> processing_class);
    # pick whichever this installed version accepts so a rename can't crash the run after the model download.
    cfg_params = inspect.signature(SFTConfig.__init__).parameters
    seq_kw = "max_length" if "max_length" in cfg_params and "max_seq_length" not in cfg_params else "max_seq_length"
    trainer_params = inspect.signature(SFTTrainer.__init__).parameters
    tok_kw = "tokenizer" if "tokenizer" in trainer_params else "processing_class"

    steps_per_epoch = -(-len(train) // (a.batch * a.grad_accum))
    total_steps = a.max_steps if a.max_steps > 0 else int(steps_per_epoch * a.epochs)
    wanted = dict(
        output_dir=a.out, dataset_text_field="text", per_device_train_batch_size=a.batch,
        gradient_accumulation_steps=a.grad_accum, num_train_epochs=a.epochs, max_steps=a.max_steps,
        learning_rate=a.lr, lr_scheduler_type="cosine", warmup_steps=max(1, int(0.03 * total_steps)),
        logging_steps=10, save_steps=a.save_steps, save_total_limit=3, eval_strategy="steps",
        eval_steps=a.eval_steps, bf16=use_bf16, fp16=not use_bf16, optim="adamw_8bit", seed=13, report_to="none",
        **{seq_kw: a.max_seq},
    )
    # Keep only the settings this TRL/transformers version accepts, and say which were dropped.
    dropped = [k for k in wanted if k not in cfg_params]
    if dropped:
        print("SFTConfig does not accept (dropped):", dropped)
    trainer = SFTTrainer(
        model=model, train_dataset=train, eval_dataset=val, **{tok_kw: tokenizer},
        args=SFTConfig(**{k: v for k, v in wanted.items() if k in cfg_params}),
    )
    # Train only on the answer: Mistral wraps user turns in [INST] ... [/INST]
    trainer = train_on_responses_only(trainer, instruction_part="[INST]", response_part="[/INST]")

    import torch
    t0 = time.time()
    stats = trainer.train(resume_from_checkpoint=a.resume or None)
    model.save_pretrained(a.out)
    tokenizer.save_pretrained(a.out)
    print(stats)
    # Speed / memory record: decides how many epochs fit in a Kaggle session (12 h) and the weekly quota.
    steps = stats.global_step
    rec = {"steps": steps, "seconds": round(time.time() - t0, 1), "train_runtime": stats.metrics.get("train_runtime"),
           "examples_per_step": a.batch * a.grad_accum, "train_examples": len(train),
           "steps_per_epoch": -(-len(train) // (a.batch * a.grad_accum)),
           "peak_vram_gb": round(torch.cuda.max_memory_allocated() / 1e9, 2), "gpu": torch.cuda.get_device_name(0),
           "train_loss": stats.metrics.get("train_loss")}
    rec["sec_per_step"] = round(rec["train_runtime"] / max(steps, 1), 2) if rec["train_runtime"] else None
    if rec["sec_per_step"]:
        rec["est_hours_per_epoch"] = round(rec["sec_per_step"] * rec["steps_per_epoch"] / 3600, 2)
    Path(a.out).mkdir(parents=True, exist_ok=True)
    (Path(a.out) / "run_stats.json").write_text(json.dumps(rec, indent=1))
    print("RUN_STATS", json.dumps(rec))
    if a.export_gguf:
        # Merges LoRA into the base weights and quantises to ~4 GB; runs on the demo Mac via Ollama.
        # Builds llama.cpp in the notebook, which can fail; the adapter above is already saved either way.
        try:
            model.save_pretrained_gguf(a.out, tokenizer, quantization_method="q4_k_m")
            print("GGUF written under", a.out)
        except Exception as e:                       # merge + convert locally instead (see docs/stair.md)
            print("GGUF export failed, adapter is saved:", type(e).__name__, e)
    print("Adapter saved to", a.out, "-- never upload it publicly (it is trained on a copyrighted book).")


if __name__ == "__main__":
    main()
