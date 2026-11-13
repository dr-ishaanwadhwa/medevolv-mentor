"""Build the entity <-> section mention index into data/graph/ (deterministic, no LLM).

    .venv/bin/python scripts/build_mentions.py [--max-df 0.02]

Writes mentions.jsonl (entity -> sections), by_section.jsonl (section -> entities) and meta.json.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from rag.mentions import GRAPH_DIR, phrase_key, tokens  # noqa: E402
from rag.ontology_facts import GENERIC  # noqa: E402

ONTOLOGY = Path("data/ontology/clinical_ontology.jsonl")
SECTIONS = "data/okf/*/sections/*.md"
STOP = GENERIC | {"the", "of", "and", "or", "in", "to", "a", "an", "for", "on", "by", "at", "other", "disease", "diseases",
                  "syndrome", "disorder", "pain", "agent", "drug", "therapy", "treatment", "test", "normal", "factor",
                  "finding", "correction", "dependence", "epidemic", "histology", "reactivation", "frequency", "lead", "expansion", "drainage", "invasion", "displacement", "pandemic", "exacerbation"}
# back matter has no teaching content (a reference list mentions everything); its links would be noise
NOISE_TITLE = re.compile(r"\b(bibliography|references|index|further reading|preface|acknowledg\w*|contents|appendix|glossary|"
                         r"abbreviations)\b", re.I)
# "Stage 1 (T1D)" loses its qualifier and would match every "stage 1" in the books
BARE_ORDINAL = re.compile(r"^(stage|grade|type|class|phase|group|level) \w+$")
CERTIFIED_BONUS = 5.0     # the ontology fact itself cites this section
MAX_LEN = 8


def load_entities() -> dict[str, list[tuple[str, str, str]]]:
    """phrase key -> [(entity id, label, type)] for CERTIFIED facts' subjects and objects."""
    seen, by_key = set(), defaultdict(list)
    for line in ONTOLOGY.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        if f.get("status") != "CERTIFIED":
            continue
        for side in ("subject", "object"):
            eid, label = f[side + "_id"], f[side + "_label"]
            if eid in seen:
                continue
            seen.add(eid)
            key = phrase_key(label)
            if key:
                by_key[key].append((eid, label, f[side + "_type"]))
    return by_key


def load_aliases(by_key) -> tuple[dict[str, str], dict[str, str]]:
    """(alias phrase key -> label key, upper-case abbreviation -> label key) from the registry synsets."""
    try:
        from ontology.registry import MEDICAL_SYNSETS
    except Exception:
        return {}, {}
    words, abbrs = {}, {}
    for alias, canon in MEDICAL_SYNSETS.items():
        ck = phrase_key(canon)
        if ck not in by_key:
            continue
        if re.fullmatch(r"[a-z]{2,5}", alias):
            abbrs[alias.upper()] = ck
        else:
            ak = phrase_key(alias)
            if ak and ak != ck:
                words[ak] = ck
    return words, abbrs


def parse(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    head, _, body = text.removeprefix("---\n").partition("\n---\n")
    meta = {}
    for line in head.splitlines():
        k, _, v = line.partition(": ")
        meta[k] = v
    sp = json.loads(meta.get("section_path", "[]"))
    return {"id": json.loads(meta["id"]), "book_id": json.loads(meta["book_id"]), "title": json.loads(meta["title"]),
            "path": sp[1:], "body": body}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-df", type=float, default=0.25, help="labels found in more than this share of sections only keep links where they are in the title/heading path")
    args = ap.parse_args()
    t0 = time.time()

    by_key = load_entities()
    alias_words, abbrs = load_aliases(by_key)
    phrases: dict[tuple, str] = {}                       # token tuple -> label key
    for key in by_key:
        toks = tuple(key.split())
        if len(toks) > MAX_LEN or all(t in STOP for t in toks) or (len(toks) == 1 and len(toks[0]) < 4) \
                or BARE_ORDINAL.match(key):
            continue
        phrases[toks] = key
    for ak, ck in alias_words.items():
        toks = tuple(ak.split())
        if len(toks) <= MAX_LEN and not all(t in STOP for t in toks) and not (len(toks) == 1 and len(toks[0]) < 4):
            phrases[toks] = ck
    firsts = defaultdict(list)
    for toks in phrases:
        firsts[toks[0]].append(toks)
    abbr_re = re.compile(r"\b(" + "|".join(map(re.escape, abbrs)) + r")\b") if abbrs else None

    def scan(toks: list[str]) -> Counter:
        c = Counter()
        for i, t in enumerate(toks):
            for p in firsts.get(t, ()):
                if tuple(toks[i:i + len(p)]) == p:
                    c[phrases[p]] += 1
        return c

    # certified provenance: entity id -> section ids that the ontology fact cites
    cited = defaultdict(set)
    for line in ONTOLOGY.read_text(encoding="utf-8").splitlines():
        if line.strip():
            f = json.loads(line)
            if f.get("status") == "CERTIFIED":
                for s in f.get("sources") or [f.get("provenance", {})]:
                    for side in ("subject_id", "object_id"):
                        cited[f[side]].add(s.get("section_id"))

    secs, counts, title_hits = [], {}, {}
    for p in sorted(Path(".").glob(SECTIONS)):
        s = parse(p)
        noise = bool(NOISE_TITLE.search(s["title"]))
        c = Counter() if noise else scan(tokens(s["body"]))
        if abbr_re and not noise:
            for m in abbr_re.findall(s["body"]):
                c[abbrs[m]] += 1
        secs.append(s)
        counts[s["id"]] = c
        title_hits[s["id"]] = set(scan(tokens(" ".join([s["title"]] + s["path"]))))
        for m in abbr_re.findall(" ".join([s["title"]] + s["path"])) if abbr_re else ():
            title_hits[s["id"]].add(abbrs[m])
    n = len(secs)
    ids = {s["id"] for s in secs}

    df = Counter(k for c in counts.values() for k in c)
    dropped = {k for k, d in df.items() if d / n > args.max_df}
    idf = {k: math.log(n / d) for k, d in df.items()}

    strengths = {}
    links = defaultdict(dict)                             # key -> section id -> [count, strength, evidence]
    for sid, c in counts.items():
        for k, cnt in c.items():
            strength = (1 + math.log(cnt)) * idf[k] * (2.0 if k in title_hits[sid] else 1.0)
            strengths[k, sid] = round(strength, 2)
            if k not in dropped or k in title_hits[sid]:      # too generic: only title/heading hits survive
                links[k][sid] = [cnt, strengths[k, sid], "mention"]
    # certified provenance always stays, flagged evidence="certified"
    for key, ents in by_key.items():
        for eid, _, _ in ents:
            for sid in cited[eid] & ids:
                cur = links[key].get(sid)
                cnt = counts[sid].get(key, 0)
                links[key][sid] = [cnt, round(strengths.get((key, sid), 0.0) + CERTIFIED_BONUS, 2), "certified"]

    GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    by_section = defaultdict(list)
    total = 0
    with open(GRAPH_DIR / "mentions.jsonl", "w", encoding="utf-8") as out:
        for key, ents in by_key.items():
            if not links.get(key):
                continue
            secrows = [[sid, v[0], v[1], v[2]] for sid, v in sorted(links[key].items(), key=lambda x: -x[1][1])]
            for eid, label, typ in ents:
                out.write(json.dumps({"id": eid, "label": label, "type": typ, "key": key, "sections": secrows},
                                     separators=(",", ":")) + "\n")
                total += len(secrows)
                for sid, cnt, st, ev in secrows:
                    by_section[sid].append({"label": label, "type": typ, "count": cnt, "strength": st, "evidence": ev})
    with open(GRAPH_DIR / "by_section.jsonl", "w", encoding="utf-8") as out:
        for s in secs:
            out.write(json.dumps({"section_id": s["id"], "book_id": s["book_id"], "title": s["title"], "path": s["path"],
                                  "entities": by_section.get(s["id"], [])}, separators=(",", ":")) + "\n")
    meta = {"sections": n, "max_df": args.max_df, "labels_dropped_as_generic": len(dropped), "links": total,
            "build_seconds": round(time.time() - t0, 1)}
    (GRAPH_DIR / "meta.json").write_text(json.dumps(meta, indent=1))
    print(meta)


if __name__ == "__main__":
    main()
