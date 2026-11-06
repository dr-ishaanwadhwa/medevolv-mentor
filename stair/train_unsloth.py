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
import json
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
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()

    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import train_on_responses_only

    model, tokenizer = FastLanguageModel.from_pretrained(a.model, max_seq_length=a.max_seq, load_in_4bit=True)
    model = FastLanguageModel.get_peft_model(
        model, r=16, lora_alpha=32, lora_dropout=0,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        use_gradient_checkpointing="unsloth", random_state=13,
    )

    data = Path(a.data)
    train = Dataset.from_list([{"text": to_text(r, tokenizer)} for r in load_rows(data / "train.jsonl")])
    val = Dataset.from_list([{"text": to_text(r, tokenizer)} for r in load_rows(data / "val.jsonl")])

    trainer = SFTTrainer(
        model=model, tokenizer=tokenizer, train_dataset=train, eval_dataset=val,
        args=SFTConfig(
            output_dir=a.out, dataset_text_field="text", max_seq_length=a.max_seq,
            per_device_train_batch_size=a.batch, gradient_accumulation_steps=a.grad_accum,
            num_train_epochs=a.epochs, max_steps=a.max_steps, learning_rate=a.lr,
            lr_scheduler_type="cosine", warmup_ratio=0.03, logging_steps=10,
            save_steps=a.save_steps, save_total_limit=3, eval_strategy="steps", eval_steps=a.save_steps,
            bf16=False, fp16=True, optim="adamw_8bit", seed=13, report_to="none",
        ),
    )
    # Train only on the answer: Mistral wraps user turns in [INST] ... [/INST]
    trainer = train_on_responses_only(trainer, instruction_part="[INST]", response_part="[/INST]")

    stats = trainer.train(resume_from_checkpoint=a.resume or None)
    model.save_pretrained(a.out)
    tokenizer.save_pretrained(a.out)
    print(stats)
    print("Adapter saved to", a.out, "-- never upload it publicly (it is trained on a copyrighted book).")


if __name__ == "__main__":
    main()
