"""Post-answer, patient-aware drug consistency check (config.DRUG_CHECK).

An answer can list a condition's general first-line drugs in one section while its own "Avoid:" line, or a WARNING
graph fact, rules them out for THIS patient (beta blockers in a hypotensive RV infarct). Every sentence is cited,
yet the answer contradicts itself. This module finds and fixes that, deterministically first:

    findings = patient_findings(question)          # BP, HR, pregnancy, allergies, renal/hepatic, meds, age (regex)
    avoid    = avoid_set(text, plan, findings)     # {drug key: reason}: what this answer/patient rules out
    found    = conflicts(text, avoid)              # sentences outside Avoid/Warnings that still recommend one
    text     = revise(text, found, plan, avoid)    # one temperature-0 rewrite, validated; else drop the sentences

The check never adds a drug or a citation: an LLM rewrite that introduces either is discarded.
"""
from __future__ import annotations

import functools
import re

from ontology.merge import merge_key
from rag import ontology_facts, trace

# ---------- 1. Patient findings (regex only) ----------

BP = re.compile(r"\b(?:bp|blood pressure)\D{0,20}?(\d{2,3})\s*/\s*(\d{2,3})|\b(\d{2,3})\s*/\s*(\d{2,3})\s*mm\s*hg", re.I)
HR = re.compile(r"\b(?:hr|heart rate|pulse(?: rate)?)\D{0,15}?(\d{2,3})\b|\b(\d{2,3})\s*(?:bpm|beats?\s*(?:/|per)\s*min)", re.I)
HYPO_WORDS = re.compile(r"\bhypotensi(?:ve|on)\b|\bin (?:\w+ )?shock\b", re.I)
PREGNANT = re.compile(r"\bpregnan|\bgravid|\bprimigravida\b|\bG\d\s*P\d\b|\b\d{1,2}\s*weeks?'?\s*(?:of\s*)?gestation", re.I)
TRIMESTER = re.compile(r"\b(first|second|third|1st|2nd|3rd)\s+trimester", re.I)
WEEKS = re.compile(r"\b(\d{1,2})\s*weeks?'?\s*(?:of\s*)?(?:gestation|pregnan)", re.I)
ALLERGIC_TO = re.compile(r"\ballerg(?:ic|y)\s+to\s+([a-z][a-z\- ,]{2,60}?)(?=[.;:)(]|\bwho\b|\bwith\b|\bpresents?\b|$)", re.I)
X_ALLERGY = re.compile(r"\b([a-z][a-z\-]{3,})[- ](?:allergy|allergic)\b", re.I)
RENAL = re.compile(r"\b(?:renal|kidney) (?:failure|impairment|insufficiency)|\bckd\b|\bchronic kidney disease|\baki\b|"
                   r"\bacute kidney injury|\bend[- ]stage renal|\besrd\b|\bon (?:haemo|hemo)?dialysis", re.I)
HEPATIC = re.compile(r"\b(?:hepatic|liver) (?:failure|impairment|insufficiency|disease)|\bcirrhosis\b|\bcirrhotic\b", re.I)
TAKING = re.compile(r"\b(?:taking|takes|on|uses|using|receiving)\s+((?:[a-z][a-z\-]+)(?:\s*(?:,|and|&)\s*[a-z][a-z\-]+)*)", re.I)
AGE = re.compile(r"\b(\d{1,3})[- ]?(?:year|yr)s?[- ]?old\b|\b(\d{1,3})\s*(?:yo|y/o|y\.o\.)\b|\b(\d{1,3})\s*[MF]\b")
NOT_ALLERGENS = {"drug", "drugs", "known", "food", "seasonal", "nothing", "none", "no", "any"}
DRUG_SUFFIX = re.compile(r"(?:afil|mab|nib|ine|in|ol|ide|one|azole|cycline|mycin|pam|lam|pine|zide|ate|ium|an|il)$")
NOT_MEDS = {"examination", "arrival", "admission", "presentation", "day", "the", "his", "her", "their", "a", "an",
            "and", "this", "that", "oxygen", "ventilation", "ventilator", "dialysis", "treatment", "medication",
            "medications", "drugs", "therapy", "insulin pump", "auscultation", "palpation", "ecg", "exam", "admission"}


def patient_findings(question: str) -> dict:
    """{"flags": set, "bp": (sys, dia) | None, "hr": int | None, "age": int | None, "trimester": int | None,
    "allergies": [names], "medications": [names]}. Flags: hypotension, severe_hypertension, bradycardia,
    tachycardia, pregnancy, renal_failure, hepatic_failure, elderly, child."""
    q = question or ""
    flags: set[str] = set()
    out = {"flags": flags, "bp": None, "hr": None, "age": None, "trimester": None, "allergies": [], "medications": []}
    if m := BP.search(q):
        s, d = (int(m.group(1)), int(m.group(2))) if m.group(1) else (int(m.group(3)), int(m.group(4)))
        out["bp"] = (s, d)
        if s < 90:
            flags.add("hypotension")
        elif s >= 180:
            flags.add("severe_hypertension")
    if HYPO_WORDS.search(q):
        flags.add("hypotension")
    if m := HR.search(q):
        hr = int(m.group(1) or m.group(2))
        out["hr"] = hr
        if hr < 50:
            flags.add("bradycardia")
        elif hr > 100:
            flags.add("tachycardia")
    if PREGNANT.search(q) or TRIMESTER.search(q):
        flags.add("pregnancy")
        if m := TRIMESTER.search(q):
            out["trimester"] = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3}[m.group(1).lower()]
        elif m := WEEKS.search(q):
            w = int(m.group(1))
            out["trimester"] = 1 if w < 14 else 2 if w < 28 else 3
    allergies = []
    for m in ALLERGIC_TO.finditer(q):
        allergies += [a.strip() for a in re.split(r",|\band\b|\bor\b", m.group(1)) if a.strip()]
    allergies += [m.group(1) for m in X_ALLERGY.finditer(q)]
    out["allergies"] = list(dict.fromkeys(a.lower() for a in allergies if a.lower() not in NOT_ALLERGENS))
    if RENAL.search(q):
        flags.add("renal_failure")
    if HEPATIC.search(q):
        flags.add("hepatic_failure")
    meds = []
    for m in TAKING.finditer(q):
        for w in re.split(r"\s*(?:,|\band\b|&)\s*", m.group(1)):
            w = w.strip().lower()
            if len(w) >= 4 and w not in NOT_MEDS and (w in _vocab_keys() or _classes(w) or DRUG_SUFFIX.search(w)):
                meds.append(w)
    out["medications"] = list(dict.fromkeys(meds))
    if m := AGE.search(q):
        age = int(next(g for g in m.groups() if g))
        if age <= 120:
            out["age"] = age
            if age >= 65:
                flags.add("elderly")
            elif age < 12:
                flags.add("child")
    return out


# A contraindication's population/rationale text applies to this patient when it names one of their findings.
FINDING_TEXT = {
    "hypotension": r"hypotens|\bshock\b|low blood pressure|h(?:a)?emodynamic(?:ally)? (?:unstable|instability|compromise)",
    "severe_hypertension": r"hypertens|uncontrolled (?:blood )?pressure",
    "bradycardia": r"bradycard|heart block|\bav block|atrioventricular block",
    "tachycardia": r"tachycard",
    "pregnancy": r"pregnan|breast-?feed|lactat|teratogen|fetal|foetal",
    "renal_failure": r"renal|kidney|creatinine clearance|\begfr\b",
    "hepatic_failure": r"hepat|liver|cirrho",
    "elderly": r"elderly|older (?:adult|patient)|\bage(?:d)? (?:over|above|>)",
    "child": r"\bchild|p(?:a)?ediatric|infant",
}


def _matching_finding(text: str, findings: dict) -> str | None:
    t = (text or "").lower()
    for flag in sorted(findings.get("flags", ())):
        if re.search(FINDING_TEXT[flag], t):
            return flag.replace("_", " ")
    for med in findings.get("medications", ()):
        if re.search(rf"\b{re.escape(med)}", t) or any(c.lower() in t for c in _classes(med)):
            return f"taking {med}"
    return None


# ---------- drug vocabulary and term detection ----------

BUILTIN_DRUGS = """beta blockers; ACE inhibitors; angiotensin receptor blockers; nitrates; nitroglycerin; glyceryl trinitrate;
isosorbide dinitrate; morphine; opioids; diuretics; loop diuretics; thiazide diuretics; furosemide; calcium channel blockers;
verapamil; diltiazem; NSAIDs; aspirin; heparin; enoxaparin; warfarin; anticoagulants; thrombolytics; fibrinolytics;
alteplase; tenecteplase; streptokinase; digoxin; amiodarone; adenosine; atropine; dobutamine; dopamine; norepinephrine;
epinephrine; vasopressors; inotropes; vasodilators; sildenafil; tadalafil; PDE5 inhibitors; metformin; insulin; statins;
clopidogrel; ticagrelor; prasugrel; labetalol; hydralazine; magnesium sulfate; methyldopa; nifedipine; penicillin;
penicillins; amoxicillin; cephalosporins; sulfonamides; tetracyclines; doxycycline; fluoroquinolones; ciprofloxacin;
aminoglycosides; gentamicin; streptomycin; isotretinoin; valproate; phenytoin; carbamazepine; lithium; glucocorticoids;
corticosteroids; benzodiazepines; ketamine; propofol; succinylcholine; haloperidol; negative inotropes;
negative inotropic agents; spironolactone; potassium-sparing diuretics; methotrexate; misoprostol; ergometrine"""
BUILTIN_DRUGS = [d.strip() for d in BUILTIN_DRUGS.replace("\n", " ").split(";") if d.strip()]
NOT_DRUG_LABEL = re.compile(r"surgery|surgical|therapy|resection|transplant|\bpci\b|intervention|repair|ablation|support|"
                            r"management|care\b|monitoring|ventilation|dialysis|resuscitation|fluid|\brest\b|diet|exercise|"
                            r"oxygen|transfusion|counsel|education|cessation|saline|water|glucose|dextrose|electrolyte|"
                            r"nutrition|catheter|drainage|procedure|bypass|pacing|pacemaker|radiotherapy|vaccin", re.I)
# Local INN stems on top of ontology_facts.INN_STEMS (penicillin allergy -> amoxicillin; sildenafil -> PDE5 inhibitors).
EXTRA_STEMS = [(r"cillin$", ("Penicillins", "Penicillin")), (r"afil$", ("PDE5 inhibitors",)),
               (r"(?:parin)$", ("Heparins", "Heparin", "Anticoagulants")),
               (r"(?:nitroglycerin|nitrate)$", ("Nitrates",)),
               (r"^(?:morphine|diamorphine|fentanyl|pethidine|meperidine|oxycodone|codeine|tramadol)$", ("Opioids",))]


def _classes(word: str) -> tuple[str, ...]:
    w = (word or "").strip().lower().split()[-1] if word and word.strip() else ""
    return ontology_facts.drug_classes(word) + tuple(c for pat, cs in EXTRA_STEMS if re.search(pat, w) for c in cs)


def _wkey(text: str) -> str:
    """merge_key applied word by word, so a sentence and a drug label normalise the same way."""
    return " ".join(k for w in re.findall(r"[A-Za-z0-9]+", text or "") if (k := merge_key(w)))


@functools.cache
def _vocab() -> tuple[dict, "re.Pattern | None"]:
    """{surface (word-keyed) -> drug key} and one regex over all surfaces, longest first."""
    labels = list(BUILTIN_DRUGS)
    for f in ontology_facts.facts():
        if f.get("predicate") in ("TREATED_BY", "CONTRAINDICATES") and f.get("object_type") == "TherapeuticAgent":
            labels.append(f["object_label"])
    for _, classes in ontology_facts.INN_STEMS + EXTRA_STEMS:
        labels.extend(classes)
    surf: dict[str, str] = {}
    for lab in labels:
        s = _wkey(lab)
        if len(s) >= 4 and len(s.split()) <= 4 and not NOT_DRUG_LABEL.search(lab):
            surf.setdefault(s, merge_key(lab))
    if not surf:
        return {}, None
    alt = "|".join(re.escape(s) for s in sorted(surf, key=len, reverse=True))
    return surf, re.compile(rf"(?<![a-z0-9])(?:{alt})(?![a-z0-9])")


@functools.cache
def _vocab_keys() -> frozenset:
    surf, _ = _vocab()
    return frozenset(surf) | frozenset(surf.values())


def drug_terms(text: str) -> dict[str, str]:
    """{drug key: surface as written} for every drug or drug class named in text (vocabulary + INN stems)."""
    surf, rx = _vocab()
    out: dict[str, str] = {}
    norm = _wkey(text)
    if rx is not None:
        for m in rx.finditer(norm):
            out.setdefault(surf[m.group(0)], m.group(0))
    for w in re.findall(r"[A-Za-z][A-Za-z\-]{3,}", text or ""):
        if _classes(w):
            out.setdefault(merge_key(w), w.lower())
    return out


def _expand(key: str) -> set[str]:
    """A drug's own key plus its classes' keys (metoprolol -> beta blocker); a class key plus its synonyms."""
    keys = {key}
    for c in _classes(key):
        keys.add(merge_key(c))
    for _, classes in ontology_facts.INN_STEMS + EXTRA_STEMS:
        ck = {merge_key(c) for c in classes}
        if key in ck:
            keys |= ck
    return keys


# ---------- 2. What this answer / patient rules out ----------

AVOID_LABEL = re.compile(r"^\s*(?:[-*•>]\s*)*(?:\*\*|__)?\s*(?:⚠️?\s*)?(avoid|warnings?|contraindications?|contraindicated)"
                         r"\b[^:\n]{0,40}?:", re.I)
BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
ALT_CLAUSE = re.compile(r"\b(instead|prefer(?:red)?|use|give|safe|safer|alternative|recommended)\b", re.I)
WARN_FACT = re.compile(r"^WARNING[^:]*:\s*(.+?)\s+is\s+(strictly\s+)?contraindicated\b(.*)$", re.I | re.S)


def _lines(text: str) -> list[tuple[str, bool]]:
    """(line, is_avoid_line). A bare 'Avoid:' header makes the bullets right under it avoid lines too."""
    out, in_block = [], False
    for line in (text or "").split("\n"):
        m = AVOID_LABEL.match(line)
        if m:
            rest = re.sub(r"[\s*_:]+", "", line[m.end():])
            out.append((line, True))
            in_block = not rest
        elif in_block and BULLET.match(line):
            out.append((line, True))
        else:
            in_block = False
            out.append((line, False))
    return out


def avoid_set(answer_text: str, plan=None, findings: dict | None = None) -> dict[str, str]:
    """{drug key: reason}. Sources: the answer's own Avoid/Warnings lines; WARNING graph facts that are strict or
    name one of this patient's findings; certified ontology CONTRAINDICATES for the plan's conditions whose
    population/rationale names a finding; and stated allergies. Class synonyms are added (beta blocker =
    beta adrenergic blocker)."""
    findings = findings or {"flags": set(), "allergies": [], "medications": []}
    avoid: dict[str, str] = {}

    def add(key: str, reason: str) -> None:
        for k in _expand(key):
            avoid.setdefault(k, reason)

    for line, is_avoid in _lines(answer_text):
        if not is_avoid:
            continue
        for clause in re.split(r";", AVOID_LABEL.sub("", line, count=1) if AVOID_LABEL.match(line) else line):
            if ALT_CLAUSE.search(clause) and not NEGATION.search(clause):
                continue
            for key in drug_terms(clause):
                add(key, "the answer's own Avoid/Warnings line")
    for fact in getattr(plan, "graph_facts", None) or []:
        m = WARN_FACT.match(fact.strip())
        if not m:
            continue
        hit = "strictly contraindicated" if m.group(2) else _matching_finding(m.group(3), findings)
        if hit:
            for key in drug_terms(m.group(1)) or {merge_key(m.group(1)): m.group(1)}:
                add(key, f"WARNING graph fact ({hit})")
    if ontology_facts.available():
        for cond in getattr(plan, "conditions", None) or []:
            for f in ontology_facts.contraindications_for(cond):
                fc = f["clinical_facets"]
                hit = _matching_finding(f"{fc.get('population') or ''} {fc.get('rationale') or ''}", findings)
                if hit:
                    add(merge_key(f["object_label"]), f"textbook contraindication in {f['subject_label']} ({hit})")
    for a in findings.get("allergies", ()):
        add(merge_key(a), f"stated allergy to {a}")
    return avoid


# ---------- 3. Sentences that still recommend an avoided drug ----------

NEGATION = re.compile(
    r"\b(avoid|avoided|avoiding|do not|don't|does not|should not|must not|never|contraindicat\w*|harmful|"
    r"not recommended|withh(?:e|o)ld\w*|hold|refrain|toxic\w*|caution\w*|discontinu\w*|stop\w*|prohibited|"
    r"not (?:in|for) this patient|not (?:given|used|indicated|appropriate|suitable)|only (?:once|after|when|if)|"
    r"after (?:stabili[sz]\w*|resuscitation|the (?:bp|blood pressure))|once\b.*\b(?:stable|stabili[sz]ed|resolved|"
    r"restored|recovers?|recovered|corrected)|until|unless|instead of|rather than|deferred?|delay\w*|"
    r"if (?:bp|blood pressure|systolic|sbp|hr|heart rate)|worsen\w*|precipitat\w*)\b",
    re.I)
SPLIT = re.compile(r"(?<=[.!?;])\s+")


def _units(text: str) -> list[tuple[int, str, bool]]:
    """(line index, sentence, is_avoid_line) for every sentence of every line."""
    out = []
    for i, (line, is_avoid) in enumerate(_lines(text)):
        for s in SPLIT.split(line):
            if s.strip():
                out.append((i, s, is_avoid))
    return out


def conflicts(answer_text: str, avoid: dict[str, str]) -> list[dict]:
    """[{drug, key, sentence, reason}]: sentences outside the Avoid/Warnings lines that name an avoided drug (or a
    drug whose class is avoided) without negating or qualifying it."""
    if not avoid:
        return []
    out, seen = [], set()
    for _, sent, is_avoid in _units(answer_text):
        if is_avoid or NEGATION.search(sent):
            continue
        for key, surface in drug_terms(sent).items():
            hit = key if key in avoid else next((k for k in sorted(_expand(key)) if k in avoid), None)
            if hit and (sent, hit) not in seen:
                seen.add((sent, hit))
                out.append({"drug": surface, "key": hit, "sentence": sent.strip(), "reason": avoid[hit]})
    return out


# ---------- 4. Fix: one LLM rewrite, validated; otherwise drop the sentences ----------

REVISE_SYSTEM = """You fix one problem in a medical study answer: some sentences recommend a drug that the same answer
(or the patient's findings) rules out for THIS patient. Rewrite ONLY the listed sentences so the drug is not
recommended for this patient: delete the drug from the sentence, or say it is avoided here / only after the stated
contraindication resolves. Keep every other line exactly as it is, and keep every citation marker like [3] or [G2]
exactly. Add no new facts, drugs or citations. Return the full corrected answer and nothing else."""

CITE = re.compile(r"\[([G\d,\s]+)\]")


def _cites(text: str) -> set[str]:
    return {x for grp in CITE.findall(text or "") for x in re.findall(r"G?\d+", grp)}


def drop_sentences(text: str, sentences: set[str]) -> str:
    """Remove those sentences; a line left with only a bullet, markup or citation markers is removed too."""
    want = {s.strip() for s in sentences}
    lines_out = []
    for line, _ in _lines(text):
        parts = SPLIT.split(line)
        kept = [p for p in parts if p.strip() not in want]
        if len(kept) == len(parts):
            lines_out.append(line)
            continue
        new = " ".join(kept)
        if re.sub(r"[\s\-*•_>#:]|\[[G\d,\s]+\]|^\d+[.)]", "", new):
            lines_out.append(new)
    return "\n".join(lines_out)


def _valid_revision(original: str, revised: str) -> bool:
    if not revised or len(revised) < 0.5 * len(original):
        return False
    if not _cites(revised) <= _cites(original):
        return False
    return set(drug_terms(revised)) <= set(drug_terms(original))


def revise(answer_text: str, found: list[dict], plan=None, avoid: dict[str, str] | None = None) -> tuple[str, str]:
    """(new text, how): how = "none" | "rewrite" | "rewrite+drop" | "drop". At most one chat call."""
    if not found:
        return answer_text, "none"
    avoid = avoid if avoid is not None else {c["key"]: c["reason"] for c in found}
    listing = "\n".join(f"{i}. {c['sentence']}\n   drug: {c['drug']} | why not for this patient: {c['reason']}"
                        for i, c in enumerate(found, 1))
    revised = ""
    try:
        from rag.backends import chat
        revised = chat(REVISE_SYSTEM, f"Answer:\n{answer_text}\n\nSentences to fix:\n{listing}\n\nCorrected answer:",
                       temperature=0, max_tokens=1400, purpose="Patient safety rewrite").strip()
    except Exception:
        revised = ""
    if _valid_revision(answer_text, revised):
        left = conflicts(revised, avoid)
        if not left:
            return revised, "rewrite"
        return drop_sentences(revised, {c["sentence"] for c in left}), "rewrite+drop"
    return drop_sentences(answer_text, {c["sentence"] for c in found}), "drop"


def check(question: str, answer_text: str, plan=None) -> str:
    """The whole check; returns the (possibly) corrected text. Never raises."""
    try:
        findings = patient_findings(question)
        avoid = avoid_set(answer_text, plan, findings)
        found = conflicts(answer_text, avoid)
        if not found:
            trace.record("safety", "Patient safety check: no conflicts",
                         f"{len(avoid)} drug/class key(s) ruled out for this patient"
                         + (f" (findings: {', '.join(sorted(findings['flags']))})" if findings["flags"] else "")
                         + "; no other sentence recommends one.")
            return answer_text
        new, how = revise(answer_text, found, plan, avoid)
        trace.record("safety", f"Patient safety check: {len(found)} conflicts fixed",
                     "Recommended although ruled out for this patient: "
                     + "; ".join(f"{c['drug']} ({c['reason']})" for c in found[:5])
                     + {"rewrite": ". Sentences rewritten.", "rewrite+drop": ". Rewritten; leftovers removed.",
                        "drop": ". Sentences removed."}[how],
                     status="warn", conflicts=found, how=how)
        return new
    except Exception as e:                       # a safety-check bug must never break answering
        trace.record("safety", "Patient safety check skipped", f"error: {e}"[:200], status="warn")
        return answer_text
