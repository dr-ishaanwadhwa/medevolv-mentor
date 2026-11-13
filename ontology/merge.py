"""Deterministic entity merging: one node per concept, whichever book or spelling it came from.

Two mentions are merged only when they are the same name after normalisation (case, punctuation, hyphens,
apostrophes, a plural last word) and the same type. One type rule: a name that is mostly used as a drug
(TherapeuticAgent) is a drug everywhere, so 'Vancomycin' as an EtiologicalAgent (drug-induced disease)
joins the drug node. Nothing fuzzier than that: 'Asthma' and 'Acute asthma' stay apart on purpose.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter, defaultdict

_KEEP_S = ("ss", "us", "is", "as", "os", "ys")

# British/INN vs US names and spellings (general lists, not tuned to any test set)
DRUG_SYNONYMS = {
    "salbutamol": "albuterol", "paracetamol": "acetaminophen", "rifampicin": "rifampin", "frusemide": "furosemide",
    "adrenaline": "epinephrine", "noradrenaline": "norepinephrine", "lignocaine": "lidocaine",
    "glibenclamide": "glyburide", "phenobarbitone": "phenobarbital", "thyroxine": "levothyroxine",
    "pethidine": "meperidine", "isoprenaline": "isoproterenol", "cyclosporin": "cyclosporine",
    "amoxycillin": "amoxicillin", "cefalexin": "cephalexin", "sulphasalazine": "sulfasalazine",
    "valproic acid": "valproate", "sodium valproate": "valproate", "co trimoxazole": "trimethoprim sulfamethoxazole",
    "cotrimoxazole": "trimethoprim sulfamethoxazole", "bendrofluazide": "bendroflumethiazide",
    "chlorpheniramine": "chlorphenamine", "dothiepin": "dosulepin", "methotrimeprazine": "levomepromazine",
}
_SPELLING = [(r"haem", "hem"), (r"oedema", "edema"), (r"anaem", "anem"), (r"oesophag", "esophag"),
             (r"diarrhoea", "diarrhea"), (r"ischaem", "ischem"), (r"foet", "fet"), (r"tumour", "tumor"),
             (r"leukaem", "leukem"), (r"oestrogen", "estrogen"), (r"sulph", "sulf"), (r"aetiolog", "etiolog"),
             (r"paediatr", "pediatr"), (r"glycaem", "glycem"), (r"lipaem", "lipem"), (r"uraem", "urem"),
             (r"septicaem", "septicem"), (r"colour", "color"), (r"fibre", "fiber")]


def merge_key(label: str) -> str:
    """'Graves’ disease' == 'graves disease'; 'Deep-venous thrombosis' == 'deep venous thrombosis';
    'Glucocorticoids' == 'glucocorticoid'; 'Salbutamol' == 'albuterol'; 'Haemorrhage' == 'hemorrhage'."""
    s = unicodedata.normalize("NFKD", label or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"['’`]s\b", "", s)                     # possessive 's
    for a, b in _SPELLING:
        s = s.replace(a, b)
    s = " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())
    s = re.sub(r"^iv ", "intravenous ", s)                  # common clinical abbreviations / variants
    s = re.sub(r"\b(x ray|xray)\b", "radiograph", s).replace("radiography", "radiograph")
    s = re.sub(r" (replacement|administration)$", "", s)
    s = re.sub(r"\bdiabetes mellitus\b", "diabetes", s)    # 'diabetes' means mellitus unless 'insipidus' is said
    s = DRUG_SYNONYMS.get(s, s).split()
    if s:
        w = s[-1]
        if len(w) > 5 and w.endswith("ies"):
            s[-1] = w[:-3] + "y"
        elif len(w) > 4 and w.endswith("s") and not w.endswith(_KEEP_S):
            s[-1] = w[:-1]
    return " ".join(s)


def _is_minted(node_id: str) -> bool:
    return node_id.startswith("MED:OKF/")


def plan_merges(facts) -> tuple[dict[str, tuple[str, str, str]], list[dict]]:
    """Decide merges over all facts. Returns ({old_id: (new_id, new_label, new_type)}, report rows)."""
    uses: Counter = Counter()
    label_of: dict[str, Counter] = defaultdict(Counter)
    type_of: dict[str, str] = {}
    drug_uses: Counter = Counter()
    agent_uses: Counter = Counter()
    for f in facts:
        for side in ("subject", "object"):
            nid, lab, typ = getattr(f, f"{side}_id"), getattr(f, f"{side}_label"), getattr(f, f"{side}_type").value
            uses[nid] += 1
            label_of[nid][lab] += 1
            type_of[nid] = typ
            if typ == "TherapeuticAgent":
                drug_uses[merge_key(lab)] += 1
            elif typ == "EtiologicalAgent":
                agent_uses[merge_key(lab)] += 1

    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    retype: dict[str, str] = {}
    for nid in uses:
        lab = label_of[nid].most_common(1)[0][0]
        key, typ = merge_key(lab), type_of[nid]
        if typ == "EtiologicalAgent" and drug_uses[key] > agent_uses[key]:   # mostly used as a drug
            retype[nid] = typ = "TherapeuticAgent"
        groups[(key, typ)].append(nid)

    mapping: dict[str, tuple[str, str, str]] = {}
    report: list[dict] = []
    for (key, typ), ids in groups.items():
        if not key:
            continue
        external = [i for i in ids if not _is_minted(i)]
        if len(set(external)) > 1:                       # two different BODHI concepts: leave them alone
            continue
        if len(ids) == 1 and ids[0] not in retype and len(label_of[ids[0]]) == 1:
            continue                                     # (one id with several spellings still gets one label)
        canon = external[0] if external else max(ids, key=lambda i: (uses[i], label_of[i].most_common(1)[0][0]))
        canon_label = label_of[canon].most_common(1)[0][0]
        if _is_minted(canon) and typ != type_of[canon]:  # retyped drug: its id carries the type
            canon = f"MED:OKF/{typ.lower()}/{canon.rsplit('/', 1)[-1]}"
        for i in ids:
            mapping[i] = (canon, canon_label, typ)
        report.append({"canonical_id": canon, "canonical_label": canon_label, "type": typ,
                       "merged": sorted(f"{label_of[i].most_common(1)[0][0]} [{type_of[i]}] x{uses[i]}" for i in ids)})
    return mapping, report


def apply_merges(facts, mapping):
    """Facts with subject/object ids, labels and types rewritten to their canonical node."""
    from ontology.reconciler import check_direction
    from ontology.schema import EntityType
    out = []
    for f in facts:
        upd = {}
        for side in ("subject", "object"):
            m = mapping.get(getattr(f, f"{side}_id"))
            if m:
                upd.update({f"{side}_id": m[0], f"{side}_label": m[1], f"{side}_type": EntityType(m[2])})
        g = f.model_copy(update=upd) if upd else f
        if upd and check_direction(g.predicate, g.subject_type, g.object_type) != "ok":
            g = f                                        # a retype must not break the predicate's type rule
        out.append(g)
    return out
