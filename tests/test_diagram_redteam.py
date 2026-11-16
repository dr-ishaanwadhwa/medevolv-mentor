"""R1 Flowchart red team, round 1 (PRD 4.R1 D-1/D-2, cite-or-decline).

Each case is an adversarial graph the validator ACCEPTED on 2026-11-16 (HEAD 53118e9) against a real answer streamed
from mentor.medevolv.in. Every one draws a box or arrow the answer does not state (wrong number, wrong direction,
reversed cause, bridged comparison, wrong parent, negation flipped). They are plain asserts, not xfail: the validator
must be fixed until each bad box/arrow is declined. "Declined" means the whole diagram declines OR the bad box/arrow is
absent from the accepted graph (dropped, never bridged).
"""
from api import diagram_validate as V

NS = {1, 2, 3, 4, 5, 6}


def g(kind, nodes, edges):
    """nodes: [(id, label, cites)], edges: [(from, to, label, cites)]"""
    return {"kind": kind, "title": None,
            "nodes": [{"id": i, "label": lb, "cites": list(c)} for i, lb, c in nodes],
            "edges": [{"from": a, "to": b, "label": lb, "cites": list(c)} for a, b, lb, c in edges]}


def run(answer, graph):
    return V.validate(graph, answer_text=answer, passage_ns=NS, fact_ns=set())


def node_labels(res):
    return {n["label"] for n in res.graph["nodes"]} if res.ok else set()


def edge_labels(res):
    if not res.ok:
        return set()
    lab = {n["id"]: n["label"] for n in res.graph["nodes"]}
    return {(lab[e["from"]], lab[e["to"]]) for e in res.graph["edges"]}


def assert_box_declined(res, box):
    assert box not in node_labels(res), f"unsupported box drawn: {box!r} in {res.graph}"


def assert_arrow_declined(res, src, tgt):
    assert (src, tgt) not in edge_labels(res), f"unsupported arrow drawn: {src!r} -> {tgt!r} in {res.graph}"


# ---------------------------------------------------------------- real answers (live, 2026-11-16)

DIGOXIN = """Digoxin's aglycone has a steroid (cyclopentanoperhydrophenanthrene) ring bearing a 5- or 6-membered unsaturated lactone ring, and all digitalis glycosides act qualitatively similarly, with digoxin as the prototype [1].

- **Cardiac effects:** Digoxin has direct effects on myocardial contractility and electrophysiological properties, plus vagomimetic action, reflex haemodynamic effects, and direct CNS effects altering sympathetic activity [1].
- **Positive inotropy:** It causes a dose-dependent increase in force of contraction, especially in the failing heart, with increased velocity of tension development and higher peak tension; systole is shortened and diastole prolonged [1]. The digitalized failing heart regains some capacity to contract more forcefully against increased resistance to ejection, with more complete emptying of dilated ventricles, increased cardiac output and reduced end-diastolic volume; therapeutic doses do not increase resting tension [1].
- **Rate slowing:** Heart rate is decreased, more markedly in CHF patients, because improved circulation restores diminished vagal tone and abolishes sympathetic overactivity; digitalis also slows the heart by vagal and extravagal actions [1]. Vagal tone is increased reflexly via baroreceptor sensitization and by stimulation of the vagal centre; the extravagal component is a direct depressant action on SA and A-V nodes that is not reversed by atropine [1].
- **Neurohormonal effects:** Digitalis glycosides exert a mild inotropic effect, attenuate carotid sinus baroreceptor activity, and are sympatho-inhibitory, decreasing serum norepinephrine, plasma renin and possibly aldosterone levels [2].

The sources do not describe the molecular/cellular mechanism (e.g., Na⁺-K⁺-ATPase inhibition) underlying these effects."""

METFORMIN = """Metformin's mechanism is incompletely defined, but key features include:

- **AMPK activation** plays a crucial role; this appears to be an indirect consequence of interference with the mitochondrial respiratory chain, lowering intracellular ATP and raising AMP [1][2].
- **Suppresses hepatic gluconeogenesis and hepatic glucose output** — the major action lowering blood glucose in diabetics [1][3].
- **Enhances insulin-mediated glucose uptake and disposal** in skeletal muscle and fat, overcoming insulin resistance; leads to glycogen storage in skeletal muscle, reduced lipogenesis in adipose tissue and enhanced fatty acid oxidation [1][2].
- **Interferes with the mitochondrial respiratory chain** and promotes peripheral glucose utilization through anaerobic glycolysis [1].
- **Retards intestinal absorption** of glucose, other hexoses, amino acids and vitamin B12 [1]; also has effects on gut glucose uptake and utilisation [2].
- It does **not stimulate pancreatic β cells** and does not cause insulin release, but insulin must be present for its action (ineffective in pancreatectomised animals and type 1 diabetics) [1].
- Metformin is still effective in mice lacking AMPK, and AMPK-independent mechanisms have been proposed [2].
- In cancer cell biology, metformin inhibits gluconeogenesis and may act on tumour cells by activating AMPK (downstream of LKB1), inhibiting mTORC1 and thereby decreasing protein synthesis and proliferation [6].

Note: the sources do not give a single precisely defined molecular mechanism; all describe it as incompletely understood [2][3]."""

COMPARISON = """**Penicillins (β-lactams) — cell wall synthesis inhibition**
- All β-lactams interfere with bacterial cell wall synthesis [1].
- They inhibit transpeptidases, the enzymes that cleave the terminal D-alanine of peptide chains and cross-link peptidoglycan strands of neighbouring residues; blocking this cross-linking prevents the close-knit, rigid cell wall structure from forming [1].
- These enzymes and related proteins constitute the penicillin binding proteins (PBPs), located in the bacterial cell membrane; each organism has several PBPs [1].
- Listed under "inhibit cell wall synthesis" along with cephalosporins, cycloserine, vancomycin and bacitracin [3].

**Aminoglycosides — inhibition of protein synthesis (with membrane effects)**
- Bactericidal; action occurs in two steps: transport through the cell wall and cytoplasmic membrane, then binding to ribosomes inhibiting protein synthesis [4].
- Transport: diffuse across the gram-negative outer coat via porin channels; entry across the cytoplasmic membrane is carrier-mediated and linked to the electron transport chain, so it is oxygen- and energy-dependent (EDP1) and is inactivated under anaerobic conditions [4].
- Streptomycin binds 30S ribosomes; other aminoglycosides also bind 50S sites and the 30S–50S interface [4]. They freeze initiation of protein synthesis, prevent polysome formation and promote disaggregation to monosomes [4].
- Binding at the 30S–50S juncture distorts mRNA codon recognition → misreading of the code, wrong amino acids incorporated and/or abnormal peptide lengths [4][6].
- Cidal action is based on secondary changes in bacterial cell membrane integrity (leakage of ions, amino acids, proteins), unlike static protein-synthesis inhibitors (tetracyclines, chloramphenicol, erythromycin); this also augments energy-dependent phase II (EDP2) entry [6].
- Killing is concentration dependent (peak/MIC ratio) with a long post-antibiotic effect [6].
- Harrison's: aminoglycosides bind the 30S subunit and inhibit protein synthesis [5].

**Key contrasts**
- Target: cell wall transpeptidation/PBPs [1] vs 30S (and 50S/interface) ribosome [4][5].
- Effect on protein synthesis: none described for penicillins [1]; aminoglycosides block initiation and cause mRNA misreading [4][6].
- Membrane: penicillins act at the membrane-located PBPs on wall assembly [1]; aminoglycosides secondarily disrupt membrane integrity, which is linked to their cidal action [6].
- Synergism: cell wall inhibitors (β-lactams, vancomycin) enhance aminoglycoside entry and show synergism [4].

The sources do not cover a direct comparison of the two classes' resistance mechanisms beyond the general statements above."""

T1D = """Type 1 diabetes (T1D) is an autoimmune disease in which progressive destruction of islet β cells leads to absolute insulin deficiency [1]. Islet destruction is caused primarily by immune effector cells reacting against endogenous β-cell antigens, and the disease stems from a failure of self-tolerance in T cells [1][3]. Circulating autoantibodies to islet cell antigens (including insulin) are often detected in affected patients [1]; autoantibody-mediated β-cell destruction with autoantibodies present in blood is part of the proposed sequence of events [2].

Pathogenesis involves an interplay of genetic and environmental factors [3]. Genetic susceptibility is supported by epidemiologic studies showing higher concordance rates in monozygotic versus dizygotic twins [3]; risk among first-degree relatives ranges from 1–4% (mother) to 30–50% (identical twin), yet 80–85% of new cases present with no known family history [2]. A temporal model proposes that genetically predisposed individuals are exposed to a trigger initiating an autoimmune process, with development of islet autoantibodies and gradual decline in β-cell function and mass; stage 1 is autoantibody positivity with normoglycemia, stage 2 adds dysglycemia, and stage 3 is hyperglycemia meeting diagnostic criteria [6].

Clinically, T1D most commonly develops in childhood, becomes manifest at puberty, and progresses with age; it can develop at any age, so the term "juvenile-onset diabetes" is no longer used [3]. Most patients require insulin for survival; without insulin, ketoacidosis and coma may occur [3]. Latent autoimmune diabetes in adults (LADA) is a slowly progressive adult form distinguished from T2D by one or more diabetes autoantibodies [3]. Patients present when β-cell destruction crosses a threshold at which adequate insulin secretion and normal glucose levels can no longer be sustained; high glucose may be toxic to remaining β cells, so profound insulin deficiency rapidly ensues [4].

The sources do not specify the particular environmental triggers (they are referred to as "described in the text" without being listed) [2]."""

BETA_BLOCKERS = """β blockers are classified as follows:

**Nonselective (β1 and β2)**
- Without intrinsic sympathomimetic activity: propranolol, sotalol, timolol [3]
- With intrinsic sympathomimetic activity: pindolol [3]
- With additional α-blocking property: labetalol, carvedilol [3]

**Cardioselective (β1)**
- Metoprolol, atenolol, acebutolol, bisoprolol, esmolol, betaxolol, celiprolol, nebivolol [3]

Additional points:
- All β blockers are competitive antagonists; propranolol blocks β1 and β2 with weak activity on β3 and is also an inverse agonist [3].
- Cardioselectivity is only relative and is lost at high doses [1].
- Partial agonistic (intrinsic sympathomimetic) activity is seen in pindolol, celiprolol, and acebutolol [1].
- In heart failure with reduced ejection fraction, beta blocker use should ideally be restricted to carvedilol, bisoprolol, and metoprolol succinate, as these have proven survival benefit; agents with intrinsic sympathomimetic activity (e.g., xamoterol) and bucindolol have not shown survival benefit [2].
- Third-generation beta blockers are cardioselective with additional vasodilatory properties (nebivolol), used alone or with α-receptor blockade (carvedilol) [4][5].

The sources do not provide a single unified classification scheme beyond the groupings above."""


# ---------------------------------------------------------------- numbers

def test_number_not_in_the_supporting_sentence():
    """Text has stage 1, 2, 3 only. "4" comes from "1–4% (mother)" in an unrelated [2] sentence; the number check runs
    on the union of every sentence carrying any of the box's cites."""
    res = run(T1D, g("sequence",
                     [("a", "Stage 1 autoantibody positivity", [6]), ("b", "Stage 2 dysglycemia", [6]),
                      ("c", "Stage 4 hyperglycemia", [6, 2])],
                     [("a", "b", "then", [6]), ("b", "c", "then", [6])]))
    assert_box_declined(res, "Stage 4 hyperglycemia")


# ---------------------------------------------------------------- bridging compared items

def test_vs_does_not_link_the_two_compared_items():
    """"Target: cell wall transpeptidation/PBPs [1] vs 30S ... ribosome [4][5]" contrasts, it does not cause."""
    res = run(COMPARISON, g("sequence",
                            [("a", "Cell wall transpeptidation PBPs", [1]), ("b", "30S ribosome", [4]),
                             ("c", "Misreading of mRNA code", [4])],
                            [("a", "b", "causes", [1, 4]), ("b", "c", "leads to", [4])]))
    assert_arrow_declined(res, "Cell wall transpeptidation PBPs", "30S ribosome")


def test_unlike_does_not_link_the_contrasted_drugs():
    """"... membrane integrity ..., unlike static protein-synthesis inhibitors (tetracyclines, ...); this also augments
    EDP2 entry": the aminoglycoside augments entry, tetracyclines are the contrast."""
    res = run(COMPARISON, g("sequence",
                            [("a", "Tetracyclines, chloramphenicol, erythromycin", [6]),
                             ("b", "Augments energy-dependent phase II entry", [6]),
                             ("c", "Secondary changes in membrane integrity", [6])],
                            [("a", "b", "causes", [6]), ("c", "b", "causes", [6])]))
    assert_arrow_declined(res, "Tetracyclines, chloramphenicol, erythromycin", "Augments energy-dependent phase II entry")


# ---------------------------------------------------------------- reversed order

def test_based_on_reverses_the_cause():
    """"Cidal action is based on secondary changes in membrane integrity": the membrane change causes cidal action."""
    res = run(COMPARISON, g("sequence",
                            [("a", "Cidal action", [6]), ("b", "Secondary changes in membrane integrity", [6]),
                             ("c", "Leakage of ions, amino acids, proteins", [6])],
                            [("a", "b", "causes", [6]), ("b", "c", "leads to", [6])]))
    assert_arrow_declined(res, "Cidal action", "Secondary changes in membrane integrity")


def test_is_caused_by_is_not_a_next_step():
    """"Islet destruction is caused primarily by immune effector cells" follows the insulin-deficiency sentence. The
    cross-sentence fallback reads "caused" in the first four words as "next step" and draws deficiency -> effector
    cells, the reverse of the answer's causality."""
    res = run(T1D, g("sequence",
                     [("a", "Destruction of islet β cells", [1]), ("b", "Absolute insulin deficiency", [1]),
                      ("c", "Immune effector cells", [1])],
                     [("a", "b", "leads to", [1]), ("b", "c", "leads to", [1])]))
    assert_arrow_declined(res, "Absolute insulin deficiency", "Immune effector cells")


# ---------------------------------------------------------------- direction (increase vs decrease)

def test_increases_when_the_object_is_lowered():
    """"lowering intracellular ATP and raising AMP": "raising" (for AMP) satisfies the "increases" synonym check, so the
    arrow is shown labelled "increases" onto ATP."""
    res = run(METFORMIN, g("sequence",
                           [("a", "Interference with mitochondrial respiratory chain", [1]),
                            ("b", "Intracellular ATP", [1]), ("c", "AMPK activation", [1])],
                           [("a", "b", "increases", [1]), ("a", "c", "leads to", [1])]))
    lab = {n["id"]: n["label"] for n in res.graph["nodes"]} if res.ok else {}
    shown = {(lab[e["from"]], lab[e["to"]], e["label"]) for e in res.graph["edges"]} if res.ok else set()
    assert ("Interference with mitochondrial respiratory chain", "Intracellular ATP", "increases") not in shown


def test_box_says_increased_where_answer_says_reduced():
    """"... increased cardiac output and reduced end-diastolic volume": "increased" belongs to cardiac output."""
    res = run(DIGOXIN, g("sequence",
                         [("a", "Digitalized failing heart", [1]), ("b", "Increased end-diastolic volume", [1]),
                          ("c", "Increased cardiac output", [1])],
                         [("a", "b", "leads to", [1]), ("a", "c", "leads to", [1])]))
    assert_box_declined(res, "Increased end-diastolic volume")


def test_box_says_increases_heart_rate_where_answer_says_decreased():
    """"Heart rate is decreased, more markedly in CHF patients": a 5-word box passes at 3/5 words (heart, rate, CHF)."""
    res = run(DIGOXIN, g("sequence",
                         [("a", "Improved circulation", [1]), ("b", "Digoxin increases heart rate in CHF", [1]),
                          ("c", "Restores diminished vagal tone", [1])],
                         [("a", "b", "causes", [1]), ("a", "c", "causes", [1])]))
    assert_box_declined(res, "Digoxin increases heart rate in CHF")


# ---------------------------------------------------------------- negation

def test_negation_in_a_box_does_not_license_a_positive_arrow():
    """"It does not stimulate pancreatic β cells and does not cause insulin release". A box that carries "not" switches
    E3 off for the whole arrow, so "Does not stimulate pancreatic β cells" --causes--> "Insulin release" is drawn."""
    res = run(METFORMIN, g("sequence",
                           [("a", "Does not stimulate pancreatic β cells", [1]), ("b", "Insulin release", [1]),
                            ("c", "Does not cause insulin release", [1])],
                           [("a", "b", "causes", [1]), ("a", "c", "causes", [1])]))
    assert_arrow_declined(res, "Does not stimulate pancreatic β cells", "Insulin release")


# ---------------------------------------------------------------- classification parent

def test_without_isa_does_not_include_pindolol():
    """"Without intrinsic sympathomimetic activity: propranolol, sotalol, timolol" / "With intrinsic sympathomimetic
    activity: pindolol". "without" is a content word that the pindolol line lacks, but 3 of 4 words still pass."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Nonselective (β1 and β2)", [3]),
                                ("a", "Without intrinsic sympathomimetic activity", [3]),
                                ("b", "Pindolol", [3]), ("c", "Propranolol, sotalol, timolol", [3])],
                               [("r", "a", "includes", [3]), ("a", "b", "includes", [3]), ("a", "c", "includes", [3])]))
    assert_arrow_declined(res, "Without intrinsic sympathomimetic activity", "Pindolol")
