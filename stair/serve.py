"""Serve the fine-tuned STAIR model locally with constrained decoding.

After training on Kaggle (stair/train_unsloth.py --export-gguf), copy the .gguf to the demo Mac and register it:
    python -m stair.serve install --book tripathi --gguf stair/adapters/tripathi/unsloth.Q4_K_M.gguf
That writes a Modelfile and runs `ollama create stair-tripathi`. Then:
    python -m stair.serve ask --book tripathi "first line drug for absence seizures"

retrieve(question, book) -> [(chapter, "chapter › section")]
  Stage A: the model sees the chapter list and must output one chapter title (JSON-schema enum = real titles only).
  Stage B: it sees that chapter's section list and must output one section title (same constraint).
The prompts match stair/build_dataset.py exactly -- a fine-tuned model is sensitive to prompt format.
"""
from __future__ import annotations

import functools
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from rag import config
from rag.backends import chat
from stair.build_dataset import SYSTEM_A, SYSTEM_B, load_labels


def model_name(book: str) -> str:
    return f"stair-{book}"


@functools.cache
def _installed(name: str) -> bool:
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_URL}/api/tags", timeout=5) as r:
            return any(m["name"].split(":")[0] == name for m in json.load(r)["models"])
    except OSError:
        return False


@functools.cache
def labels(book: str) -> dict:
    return load_labels(book)


LLAMA_URL = os.environ.get("STAIR_URL")   # llama-server with the LoRA loaded (Ollama >=0.40 dropped adapters)


def _llama(prompt: str, options: list[str]) -> str:
    """Exactly the training format ([INST] system+user [/INST] -> bare title); a grammar allows only real titles."""
    lit = lambda o: '"' + o.replace("\\", "\\\\").replace('"', '\\"') + '"'
    grammar = "root ::= " + " | ".join(lit(o) for o in options)
    body = json.dumps({"prompt": f"[INST] {prompt} [/INST]", "grammar": grammar, "temperature": 0,
                       "n_predict": 120, "cache_prompt": True}).encode()
    req = urllib.request.Request(f"{LLAMA_URL}/completion", body, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["content"].strip()


def _pick(system: str, user: str, options: list[str], book: str) -> str:
    # Training folded the system prompt into the user turn (Mistral has no system role); do the same here.
    schema = {"type": "object", "required": ["title"], "properties": {"title": {"type": "string", "enum": options}}}
    if LLAMA_URL:
        out = _llama(system + "\n\n" + user, options)
        return out if out in options else options[0]
    raw = chat("", system + "\n\n" + user + '\n\nReply as JSON {"title": "..."}.', temperature=0.0,
               max_tokens=80, schema=schema, model=model_name(book))
    try:
        return json.loads(raw[raw.find("{"): raw.rfind("}") + 1])["title"]
    except (json.JSONDecodeError, KeyError, ValueError):
        return options[0]


def retrieve(question: str, book: str = "tripathi", k: int = 1) -> list[tuple[str, str]]:
    if not LLAMA_URL and not _installed(model_name(book)):
        raise RuntimeError(f"Ollama model '{model_name(book)}' not installed -- train it, then "
                           f"`python -m stair.serve install --book {book} --gguf <file>`")
    lab = labels(book)
    listing = "\n".join(f"- {c}" for c in lab["chapters"])
    chapter = _pick(SYSTEM_A.format(book=lab["book"]), f"Chapters:\n{listing}\n\nQuestion: {question}",
                    lab["chapters"], book)
    secs = lab["sections"].get(chapter, [])
    if len(secs) <= 1:
        return [(chapter, f"{chapter} › {secs[0]}" if secs else chapter)]
    s_listing = "\n".join(f"- {s}" for s in secs)
    section = _pick(SYSTEM_B.format(book=lab["book"]),
                    f"Chapter: {chapter}\nSections:\n{s_listing}\n\nQuestion: {question}", secs, book)
    return [(chapter, f"{chapter} › {section}")]


BASE = "mistral:7b-instruct-v0.2-q4_K_M"   # Ollama's quantised copy of the model the adapters were trained on


def install(book: str, gguf: str | None = None, adapter: str | None = None) -> None:
    """Register stair-<book> in Ollama, from a merged GGUF or from a LoRA adapter dir applied to BASE."""
    src = Path(gguf or adapter or "").resolve()
    if not (gguf or adapter) or not src.exists():
        raise SystemExit(f"{src} not found")
    if gguf:
        head, modelfile = f"FROM {src}", src.parent / "Modelfile"
    else:
        head, modelfile = f"FROM {BASE}\nADAPTER {src}", src / "Modelfile"
    # Mistral-instruct template; temperature 0 because retrieval should be deterministic.
    modelfile.write_text(f'{head}\nTEMPLATE "[INST] {{{{ .Prompt }}}} [/INST]"\n'
                         "PARAMETER temperature 0\nPARAMETER stop [INST]\nPARAMETER stop [/INST]\n")
    subprocess.run(["ollama", "create", model_name(book), "-f", str(modelfile)], check=True)
    print(f"installed {model_name(book)}")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "install":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--book", required=True)
        src = ap.add_mutually_exclusive_group(required=True)
        src.add_argument("--gguf")
        src.add_argument("--adapter", help="LoRA adapter dir (adapter_model.safetensors) to apply to " + BASE)
        a = ap.parse_args()
        install(a.book, a.gguf, a.adapter)
    elif len(sys.argv) >= 2 and sys.argv[1] == "ask":
        import argparse
        ap = argparse.ArgumentParser()
        ap.add_argument("cmd")
        ap.add_argument("--book", default="tripathi")
        ap.add_argument("question", nargs="+")
        a = ap.parse_args()
        print(retrieve(" ".join(a.question), a.book))
    else:
        print(__doc__)
