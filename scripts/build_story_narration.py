"""Write the /how scroll-story narration with DeepSeek, from the facts the scenes actually show.

    ../med-rag/.venv/bin/python -m scripts.build_story_narration

Reads var/story_facts.json (scripts/build_library_map.py). For each chapter the model gets what is on screen and the
real numbers behind it, and writes a short, warm explanation for a first-time visitor. Then every number in the copy
is checked against the facts sheet; a chapter with a number that is not in its facts is regenerated (then fails).
Output: apps/web/src/content/narration.json (committed: product copy, no textbook text).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from rag.backends import chat

ROOT = Path(__file__).resolve().parent.parent
FACTS = ROOT / "var/story_facts.json"
OUT = ROOT / "apps/web/src/content/narration.json"

SYSTEM = """You write the narration for a scroll-driven explainer of a study app for Indian MBBS students.
The page shows a 3D scene; you explain, in plain warm language, what the visitor is looking at and why it matters.
Rules:
- Second person, conversational, like a senior student showing a friend. No hype words (revolutionary, magic, cutting-edge, seamless, powerful).
- Describe what is ON SCREEN first ("Each dot you see is ..."), then what it means.
- Use ONLY numbers that appear in the facts given. Never invent a number, percentage, book, or claim.
- No medical advice. Do not restate the clinical answer beyond what the facts say.
- Output JSON: {"kicker": 2-4 words, "title": max 8 words, "body": 2-3 sentences (max 60 words), "onscreen": one short line (max 14 words) describing what the scene shows right now, starting with a verb or "Each"}"""


def chapters(f: dict) -> list[dict]:
    j, books = f["journey"], f["books"]
    ev = j["evidence"]
    cited = [e for e in ev if e["cited"]]
    book_line = "; ".join(f"{b['title']}: {b['count']} passages" for b in books)
    return [
        {"id": "library", "scene": "36,725 glowing dots slowly rotating in space, coloured by textbook.",
         "facts": f"Total passages: {f['n']}. Seven textbooks. Each dot is one passage of about 300 words (260 for Gray's) "
                  "placed so that passages about similar things sit close together. The app answers only from these."},
        {"id": "books", "scene": "The dots pull apart into seven coloured clusters, one per book, each labelled.",
         "facts": f"Books and passage counts: {book_line}. Harrison's and Davidson's (both general medicine) overlap the most "
                  "in the full map, because they cover the same diseases."},
        {"id": "guard", "scene": "A question arrives as a bright point and passes through a ring; a second question bounces off the ring.",
         "facts": f"Question that passes: \"{j['question']}\". Question that is refused: \"{f['refusal']['question']}\". "
                  "The refusal happens before any textbook search, because it asks for dosing for a real person. The app is a study aid."},
        {"id": "route", "scene": "The bright point splits into two smaller points, each heading into the library.",
         "facts": f"The question asks two things (what drug first, and why), so it is split into {len(j['sub_questions'])} "
                  f"sub-questions: {' | '.join(j['sub_questions'])}. Splitting stops one topic crowding out the other in the search."},
        {"id": "search", "scene": "Thin beams connect each sub-question to its nearest dots; the rest of the library dims.",
         "facts": f"Each sub-question is compared with all {f['n']} passages. The closest passages have similarity around "
                  f"{min(n['neighbours'][0]['sim'] for n in j['near'])} to {max(n['neighbours'][0]['sim'] for n in j['near'])} "
                  f"(1 means identical meaning). The two searches took {sum(s['ms'] for s in j['steps'] if s['stage']=='retrieve')} ms together."},
        {"id": "floor", "scene": "A different, off-topic question lands far from everything; a translucent shell shows the cut-off and its nearest dots stay dark.",
         "facts": f"Off-topic question: \"{f['declined']['question']}\". Its best match scores {f['declined']['best']}, below the "
                  f"cut-off of {f['min_similarity']}. So the language model is never called and the app says it could not find this in its textbooks, instead of guessing."},
        {"id": "evidence", "scene": f"{len(ev)} dots lift out of the library and become numbered cards.",
         "facts": f"{len(ev)} passages are sent to the language model as numbered evidence: "
                  + "; ".join(f"[{e['n']}] {e['where'][:90]}" for e in ev)
                  + ". The model is told to use nothing else and to put a number like [1] after every claim."},
        {"id": "cite", "scene": "Lines run from each [n] in the answer back to its card; the cited cards light up, the others stay grey.",
         "facts": f"The answer cites {len(cited)} of the {len(ev)} passages: "
                  + ", ".join(f"[{e['n']}]" for e in cited)
                  + ". Code then checks that every [n] points at a passage that was actually sent; an answer that fails is not shown. "
                  "Passages sent but not cited are listed as retrieved, not cited."},
        {"id": "atlas", "scene": "The dots fade and a 3D model of an anatomical structure (the optic chiasm) appears.",
         "facts": "Anatomy concepts link to a 3D atlas of real anatomical models (BodyParts3D). The highlight shows where a structure sits; "
                  "it is labelled navigation only and is never a clinical claim."},
        {"id": "measured", "scene": "Three numbers count up: 39/39, 30/30 and 90.8%.",
         "facts": "On the team's own 39-question test set it did the right thing 39 out of 39 times (answer, decline or refuse). "
                  "All 30 answers carried at least one citation. On 446 pharmacology questions the right chapter was in the top 3 "
                  "search results 90.8% of the time. These are internal test sets, not a clinical-safety guarantee."},
    ]


def numbers(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def write(ch: dict) -> dict:
    user = f"SCENE ON SCREEN: {ch['scene']}\nFACTS (the only numbers you may use): {ch['facts']}"
    allowed = numbers(ch["facts"] + " " + ch["scene"]) | {"1", "2", "3", "7"}
    for attempt in range(2):
        out = json.loads(chat(SYSTEM, user, temperature=0.4 if attempt == 0 else 0.2, max_tokens=400, json_mode=True))
        text = " ".join(str(out.get(k, "")) for k in ("kicker", "title", "body", "onscreen"))
        bad = numbers(text) - allowed
        if not bad and all(out.get(k) for k in ("kicker", "title", "body", "onscreen")):
            return {"id": ch["id"], **{k: out[k].strip() for k in ("kicker", "title", "body", "onscreen")}}
        user += f"\nYour last draft used numbers not in the facts: {sorted(bad)}. Use only the facts."
    raise SystemExit(f"chapter {ch['id']}: invented numbers {sorted(bad)}")


def main() -> None:
    f = json.loads(FACTS.read_text())
    out = [write(c) for c in chapters(f)]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"chapters": out}, ensure_ascii=False, indent=2) + "\n")
    for c in out:
        print(f"[{c['id']}] {c['kicker']} | {c['title']}\n  {c['body']}\n  > {c['onscreen']}")


if __name__ == "__main__":
    main()
