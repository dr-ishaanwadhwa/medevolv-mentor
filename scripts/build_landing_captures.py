"""Capture the real answers the landing page shows (journey, decline, Why verdict), pointers only.

    API_WARMUP=0 .venv/bin/python -m scripts.build_landing_captures [--only journey|declined|why]

Runs the real FastAPI app in-process (no server) against the local index, so it calls DeepSeek (a handful of calls,
approved by the user for this release, PRD 6.2a OQ-3). Writes apps/web/public/landing/{journey,declined,why}.json.

What is stored: the question, route, Mentor's own answer prose, and citation POINTERS (book, edition, chapter, pages,
section id, cited flag). `excerpt` (textbook passage text) and every other free-text passage field are dropped, and a
final check refuses to write a file that still contains one. Each file carries captured_at and the git commit.
Candidates are tried in order and the first that gives the wanted shape (answered with >= 2 cited books for the journey,
a decline for `declined`, a verdict for `why`) is kept; the choice is recorded so the user can approve or swap it.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("API_WARMUP", "0")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "apps/web/public/landing"

JOURNEY_CANDIDATES = [
    "Trace the visual pathway and the field defect from a lesion at the optic chiasm.",
    "Describe the visual pathway from the retina to the occipital cortex and the field defects at each level.",
    "What are the boundaries and contents of the inguinal canal?",
]
DECLINED_CANDIDATES = [
    "Describe the stages of normal labour and the management of the third stage.",
    "Explain the steps of glycolysis and how it is regulated.",
    "What are the indications and complications of tonsillectomy?",
]
WHY_CANDIDATES = [
    {"question": "Which drug is the drug of choice for absence seizures?",
     "options": ["Phenytoin", "Ethosuximide", "Carbamazepine", "Phenobarbitone"], "chosen": 0},
    {"question": "Which of the following drugs is contraindicated in a patient with raised intracranial pressure after head injury?",
     "options": ["Morphine", "Paracetamol", "Mannitol", "Levetiracetam"], "chosen": 3},
]
KEEP_CITATION = ("index", "cited", "book", "edition", "chapter", "pages", "section_id")


def commit() -> str:
    return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def sse_events(client, path: str, body: dict) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    with client.stream("POST", path, json=body, timeout=180) as r:
        r.raise_for_status()
        name = None
        for line in r.iter_lines():
            if line.startswith("event: "):
                name = line[7:].strip()
            elif line.startswith("data: ") and name:
                out.setdefault(name, []).append(json.loads(line[6:]))
    return out


def pointer(c: dict) -> dict:
    return {k: c.get(k) for k in KEEP_CITATION}


def stamp(d: dict, tried: list[str]) -> dict:
    d["captured_at"] = dt.date.today().isoformat()
    d["commit"] = commit()
    d["candidates_tried"] = tried
    return d


def write(name: str, d: dict) -> None:
    text = json.dumps(d, indent=1, ensure_ascii=False)
    if '"excerpt"' in text:
        sys.exit(f"{name}: refusing to write, an excerpt field is present")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(text + "\n")
    print(f"wrote {name}.json ({len(text)} bytes)")


def journey(client) -> None:
    tried = []
    for q in JOURNEY_CANDIDATES:
        tried.append(q)
        ev = sse_events(client, "/api/chat/stream", {"question": q})
        a = (ev.get("answer") or [None])[0]
        steps = ev.get("step", [])
        if not a or a["status"] != "answered":
            print("journey: not answered:", q, a and a["status"]); continue
        cited = [c for c in a["citations"] if c["cited"]]
        books = {c["book"] for c in cited}
        print("journey:", q, "| cited", len(cited), "books", books)
        if len(cited) < 2:
            continue
        spatial = (ev.get("spatial") or [{"actions": []}])[0]["actions"]
        write("journey", stamp({
            "question": q, "route": a["route"], "status": a["status"], "answer": a["text"],
            "citations": [pointer(c) for c in a["citations"]],
            "steps": [{"stage": s["stage"], "title": s["title"], "status": s["status"]} for s in steps],
            "spatial": [{"fma_ids": x.get("fma_ids"), "label": x.get("label")} for x in spatial],
        }, tried))
        return
    sys.exit("journey: no candidate gave a cited answer")


def declined(client) -> None:
    tried = []
    for q in DECLINED_CANDIDATES:
        tried.append(q)
        ev = sse_events(client, "/api/chat/stream", {"question": q})
        a = (ev.get("answer") or [None])[0]
        print("declined:", q, "|", a and a["status"], "|", a and a["text"][:90])
        if a and a["status"] in ("not_in_sources", "insufficient"):
            write("declined", stamp({"question": q, "status": a["status"], "text": a["text"], "route": a["route"]}, tried))
            return
    sys.exit("declined: no candidate was declined")


def why(client) -> None:
    tried = []
    for c in WHY_CANDIDATES:
        tried.append(c["question"])
        ev = sse_events(client, "/api/why/stream", c)
        v = (ev.get("verdict") or [None])[0]
        print("why:", c["question"], "|", v and v["status"], v and v["correct_option"])
        if v and v["status"] == "verdict" and v["correct_option"] != c["chosen"]:
            v = dict(v)
            v["citations"] = [pointer(x) for x in v["citations"]]
            write("why", stamp({**c, "verdict": v}, tried))
            return
    sys.exit("why: no candidate gave a verdict with a wrong pick")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["journey", "declined", "why"])
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    from fastapi.testclient import TestClient
    from api.main import app
    client = TestClient(app)
    for name, fn in (("journey", journey), ("declined", declined), ("why", why)):
        if args.only in (None, name):
            fn(client)


if __name__ == "__main__":
    main()
