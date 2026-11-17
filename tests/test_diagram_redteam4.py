"""R1 Flowchart red team, round 4 (engineer's own adversarial pass after fixing round 3).

Same families as round 3, new boxes, against answers streamed live from mentor.medevolv.in on 2026-11-16 (the eval's
saved *_v1 answers, verbatim) plus round 3's T1D answer: a direction or amount word the text does not put on that
object, a dropped negation (also "not A or B"), a number moved to another item, a word borrowed from another section,
and a reversed or contradicted arrow. Each BAD box/arrow must be declined (the diagram declines, or the box/arrow is
absent); each case has a CONTROL with the answer's own wording on the same skeleton that must still draw, so a fix
cannot pass by declining everything.
"""
import pytest

from tests.test_diagram_redteam2 import edge_labels, g, node_labels, run
from tests.test_diagram_redteam3 import T1D as T1D_R3

# ---------------------------------------------------------------- real answers (live, 2026-11-16)

METFORMIN = """Metformin's mechanism is not fully defined, but the key features are:

- It does not stimulate pancreatic β cells or cause insulin release, though insulin must be present for it to act; it is ineffective in pancreatectomized animals and type 1 diabetics [1].
- Activation of AMP-dependent protein kinase (AMPK) is recognized as playing a crucial role, though this appears to be an indirect consequence of interference with cellular respiration and lowering of intracellular ATP [1].
- It suppresses hepatic gluconeogenesis and glucose output from the liver — the major action lowering blood glucose [1]. It reduces hepatic glucose production [2][3].
- It enhances insulin-mediated glucose uptake and disposal in skeletal muscle and fat, overcoming insulin resistance; this leads to glycogen storage in skeletal muscle and reduced lipogenesis with enhanced fatty acid oxidation in adipose tissue [1]. It may also increase insulin-mediated glucose uptake [2] and improves peripheral glucose utilization slightly [3].
- It interferes with the mitochondrial respiratory chain and promotes peripheral glucose utilization through anaerobic glycolysis [1]. At the molecular level it acts as a weak inhibitor of mitochondrial respiration, increasing intracellular AMP and reducing ATP [2].
- It retards intestinal absorption of glucose, other hexoses, amino acids and vitamin B12 [1]; it also has effects on gut glucose uptake and utilisation [2].

Note: sources differ on the centrality of AMPK — metformin remains effective in mice lacking AMPK, and AMPK-independent mechanisms have been proposed [2]; Harrison's also states the mechanism remains incompletely defined [3]."""

DIGOXIN = """Digoxin's aglycone has a steroid (cyclopentanoperhydrophenanthrene) ring with an attached 5- or 6-membered unsaturated lactone ring [1]. All digitalis glycosides act qualitatively similarly, with digoxin as the prototype [1].

- **Cardiac effects:** Digoxin has direct effects on myocardial contractility and electrophysiological properties, plus vagomimetic action, reflex haemodynamic effects, and direct CNS effects altering sympathetic activity [1].
- **Positive inotropy:** It causes a dose-dependent increase in force of contraction, especially in the failing heart, with increased velocity of tension development and higher peak tension; systole is shortened and diastole prolonged [1]. The digitalized failing heart regains some capacity to contract more forcefully against increased resistance to ejection, with more complete emptying of dilated ventricles, increased cardiac output, and reduced end-diastolic volume [1].
- **Rate slowing:** Heart rate is decreased, more markedly in CHF patients, partly because improved circulation restores diminished vagal tone and abolishes sympathetic overactivity; digitalis also slows the heart by vagal and extravagal actions [1]. Vagal tone is increased reflexly via baroreceptor sensitization and vagal centre stimulation, while the extravagal component is a direct depressant action on SA and A-V nodes not reversed by atropine [1].
- **Neurohormonal effects:** Digitalis glycosides exert a mild inotropic effect, attenuate carotid sinus baroreceptor activity, and are sympatho-inhibitory, decreasing serum norepinephrine, plasma renin, and possibly aldosterone levels [2].

The sources do not describe the molecular/cellular mechanism (e.g., Na⁺/K⁺-ATPase inhibition or calcium handling) underlying these effects."""

T1D = """Type 1 diabetes (T1D) is an autoimmune disease in which progressive destruction of islet β cells leads to absolute insulin deficiency [1]. Islet destruction is caused primarily by immune effector cells reacting against endogenous β-cell antigens, and the disease stems from a failure of self-tolerance in T cells [1][3]. Circulating autoantibodies to islet-cell antigens (including insulin) are often detected in affected patients [1]; autoantibody-mediated β-cell destruction with autoantibodies present in blood is part of the proposed sequence of events [2].

Pathogenesis involves an interplay of genetic and environmental factors [3]. Epidemiologic evidence includes higher concordance rates in monozygotic versus dizygotic twins [3], and risk is elevated in first-degree relatives (e.g., 30–50% in identical twins, 16% in HLA-identical siblings, 10% in children of fathers with T1D), although 80–85% of new cases occur with no known family history [2].

Clinically, T1D most commonly develops in childhood, becomes manifest at puberty, and progresses with age; it can develop at any age [3]. A temporal model describes a genetic predisposition followed by a trigger initiating autoimmunity, with islet autoantibodies and gradual decline in β-cell function and mass: Stage 1 = two or more islet autoantibodies with normoglycemia; Stage 2 = continued autoimmunity with dysglycemia; Stage 3 = hyperglycemia meeting diagnostic criteria [6]. A "honeymoon" phase with reduced insulin requirements may occur in the first 1–2 years after onset [6]. Most patients require insulin for survival; without it, ketoacidosis and coma may develop [3]. Latent autoimmune diabetes in adults (LADA) is a slowly progressive adult form distinguished from T2D by presence of one or more diabetes autoantibodies [3].

The sources do not detail the specific environmental triggers (they are only referred to as described in the text) [2]."""

COMPARISON = """**Penicillins (β-lactams)**
- Interfere with bacterial cell wall synthesis [1].
- Specifically inhibit transpeptidases, the enzymes that cleave terminal D-alanine and cross-link peptidoglycan strands; these enzymes and related proteins are the penicillin-binding proteins (PBPs) located in the bacterial cell membrane [1].
- Blocking cross-linking prevents the close-knit, rigid cell wall structure from forming [1].
- Classified under "inhibit cell wall synthesis" along with cephalosporins, cycloserine, vancomycin, bacitracin [3].

**Aminoglycosides**
- Bactericidal; act in two steps: transport into the bacterial cell, then binding to ribosomes to inhibit protein synthesis [4].
- Diffuse through gram-negative porin channels; carrier-mediated entry across the cytoplasmic membrane is linked to the electron transport chain and requires a polarized membrane and oxygen-dependent active processes (energy-dependent phase I) [4].
- Streptomycin binds 30S ribosomes; other aminoglycosides also bind 50S subunit and the 30S–50S interface [4].
- Freeze initiation of protein synthesis, prevent polysome formation and promote disaggregation to monosomes; binding at the 30S–50S juncture distorts mRNA codon recognition, causing misreading and abnormal peptides [4][6].
- Cidal action is attributed to secondary changes in membrane integrity (leakage of ions, amino acids, proteins), with defective proteins incorporated into the cell membrane; this augments energy-dependent phase II entry [6].
- Killing is concentration dependent, with a long postantibiotic effect [6].
- Classified under "cause misreading of m-RNA code and affect permeability" [3].

**Key contrast**
- Site: cell wall synthesis (transpeptidation/PBPs) [1] vs. ribosomal protein synthesis (30S/50S) with secondary membrane damage [4][6].
- Penicillin action is at the final cross-linking step of peptidoglycan assembly [1]; aminoglycoside action requires oxygen-dependent, energy-dependent transport and is inactive under anaerobic conditions [4].
- Aminoglycoside entry is enhanced by cell wall inhibitors (β-lactams, vancomycin), producing synergism [4].

The sources do not cover a direct comparison of resistance mechanisms for the two classes beyond the general statements in [2]."""

BETA_BLOCKERS = """β blockers can be classified as follows:

**Nonselective (β1 and β2)**
- Without intrinsic sympathomimetic activity: propranolol, sotalol, timolol [3]
- With intrinsic sympathomimetic activity: pindolol [3]
- With additional α-blocking property: labetalol, carvedilol [3]

**Cardioselective (β1)**
- Metoprolol, atenolol, acebutolol, bisoprolol, esmolol, betaxolol, celiprolol, nebivolol [3]

Additional points:
- All β blockers are competitive antagonists; propranolol blocks β1 and β2 with weak β3 activity and is also an inverse agonist [3].
- Cardioselectivity is only relative and is lost at high doses [1].
- Partial agonistic (intrinsic sympathomimetic) action occurs in pindolol, celiprolol, and acebutolol [1].
- In HFrEF, beta blocker use should ideally be restricted to carvedilol, bisoprolol, and metoprolol succinate, which have proven survival benefit; agents with intrinsic sympathomimetic activity (e.g., xamoterol) and bucindolol have not shown survival benefit [2].
- Third-generation beta blockers are cardioselective with additional vasodilatory properties (nebivolol), used alone or with α-receptor blockade (carvedilol) [4][5].

The sources do not provide a single unified classification scheme beyond these groupings."""


def cls(root, rc, kids):
    """A parent box with "includes" arrows to each (label, cites) child."""
    return g("classification", [("r", root, rc)] + [(f"k{i}", lb, c) for i, (lb, c) in enumerate(kids)],
             [("r", f"k{i}", "includes", c) for i, (lb, c) in enumerate(kids)])


MET_LEAD = "Metformin's mechanism is not fully defined, but the key features are"
MET_KIDS = [("It suppresses hepatic gluconeogenesis", [1]), ("Interferes with the mitochondrial respiratory chain", [1])]
RATE_KIDS = [("Heart rate is decreased", [1]), ("Digitalis also slows the heart by vagal and extravagal actions", [1])]
AMINO_KIDS = [("Streptomycin binds 30S ribosomes", [4]), ("Diffuse through gram-negative porin channels", [4])]


def stages(first, answer_style):
    if answer_style == "v1":
        return g("sequence", [("a", first, [6]), ("b", "Stage 2 = continued autoimmunity with dysglycemia", [6]),
                              ("c", "Stage 3 = hyperglycemia meeting diagnostic criteria", [6])],
                 [("a", "b", "then", [6]), ("b", "c", "then", [6])])
    return g("sequence", [("a", first, [6]), ("b", "Stage 2 by continued autoimmunity with dysglycemia", [6]),
                          ("c", "Stage 3 by hyperglycemia meeting diagnostic criteria", [6])],
             [("a", "b", "then", [6]), ("b", "c", "then", [6])])


# (answer, graph builder, BAD box, CONTROL box with the answer's own wording)
BOXES = {
    # ---- direction / amount word the text does not put on that object
    "raising ATP (text: reducing ATP)": (
        METFORMIN, lambda x: cls(MET_LEAD, [1, 2], [(x, [2])] + MET_KIDS),
        "Increasing intracellular AMP and raising ATP", "Increasing intracellular AMP and reducing ATP"),
    "enhances intestinal absorption (text: retards)": (
        METFORMIN, lambda x: cls(MET_LEAD, [1], [(x, [1])] + MET_KIDS),
        "It enhances intestinal absorption of glucose", "It retards intestinal absorption of glucose"),
    "increased lipogenesis (text: reduced)": (
        METFORMIN, lambda x: cls(MET_LEAD, [1], [(x, [1])] + MET_KIDS),
        "Increased lipogenesis in adipose tissue", "Reduced lipogenesis in adipose tissue"),
    "vagal tone decreased reflexly (text: increased)": (
        DIGOXIN, lambda x: cls("Rate slowing", [1], [(x, [1])] + RATE_KIDS),
        "Vagal tone is decreased reflexly", "Vagal tone is increased reflexly"),
    "less markedly in CHF (text: more markedly)": (
        DIGOXIN, lambda x: cls("Rate slowing", [1], [(x, [1]), ("Vagal tone is increased reflexly", [1]), RATE_KIDS[1]]),
        "Heart rate is decreased, less markedly in CHF patients", "Heart rate is decreased, more markedly in CHF patients"),
    "lower peak tension (text: higher)": (
        DIGOXIN, lambda x: cls("Positive inotropy", [1], [(x, [1]), ("Dose-dependent increase in force of contraction", [1]),
                                                          ("Reduced end-diastolic volume", [1])]),
        "Lower peak tension", "Higher peak tension"),
    "raised plasma renin (text: decreasing ... plasma renin)": (
        DIGOXIN, lambda x: cls("Neurohormonal effects", [2], [(x, [2]), ("Attenuate carotid sinus baroreceptor activity", [2]),
                                                              ("Sympatho-inhibitory", [2])]),
        "Raised plasma renin", "Decreasing serum norepinephrine, plasma renin"),
    "increased sympathetic overactivity (text: abolishes)": (
        DIGOXIN, lambda x: cls("Rate slowing", [1], [(x, [1])] + RATE_KIDS),
        "Increased sympathetic overactivity", "Abolishes sympathetic overactivity"),
    "entry reduced by cell wall inhibitors (text: enhanced)": (
        COMPARISON, lambda x: cls("Key contrast", [4], [(x, [4]), (
            "Aminoglycoside action requires oxygen-dependent, energy-dependent transport", [4])]),
        "Aminoglycoside entry is reduced by cell wall inhibitors", "Aminoglycoside entry is enhanced by cell wall inhibitors"),
    "cardioselectivity maintained at high doses (text: lost)": (
        BETA_BLOCKERS, lambda x: cls("Additional points", [1], [
            (x, [1]), ("Partial agonistic (intrinsic sympathomimetic) action occurs in pindolol", [1])]),
        "Cardioselectivity is maintained at high doses", "Cardioselectivity is lost at high doses"),
    "active under anaerobic conditions (text: inactive)": (
        COMPARISON, lambda x: cls("Key contrast", [4], [(x, [4]), (
            "Aminoglycoside entry is enhanced by cell wall inhibitors", [4])]),
        "Aminoglycoside action is active under anaerobic conditions",
        "Aminoglycoside action is inactive under anaerobic conditions"),
    "prevent disaggregation (text: promote disaggregation)": (
        COMPARISON, lambda x: cls("Aminoglycosides", [4], [(x, [4])] + AMINO_KIDS),
        "Prevent polysome formation and prevent disaggregation to monosomes",
        "Prevent polysome formation and promote disaggregation to monosomes"),
    "promote initiation (text: freeze initiation)": (
        COMPARISON, lambda x: cls("Aminoglycosides", [4], [(x, [4])] + AMINO_KIDS),
        "Promote initiation of protein synthesis", "Freeze initiation of protein synthesis"),
    # ---- the opposite word (antonym, or the text's word with a negating prefix)
    "concentration independent (text: dependent)": (
        COMPARISON, lambda x: cls("Aminoglycosides", [4], [(x, [6])] + AMINO_KIDS),
        "Killing is concentration independent", "Killing is concentration dependent"),
    "short postantibiotic effect (text: long)": (
        COMPARISON, lambda x: cls("Aminoglycosides", [4], [(x, [6])] + AMINO_KIDS),
        "Killing is concentration dependent, with a short postantibiotic effect",
        "Killing is concentration dependent, with a long postantibiotic effect"),
    "develops in adulthood (text: childhood)": (
        T1D, lambda x: cls("Clinically", [3], [(x, [3]), ("Becomes manifest at puberty", [3])]),
        "T1D most commonly develops in adulthood", "T1D most commonly develops in childhood"),
    "marked inotropic effect (text: mild)": (
        DIGOXIN, lambda x: cls("Neurohormonal effects", [2], [(x, [2]), ("Sympatho-inhibitory", [2])]),
        "Digitalis glycosides exert a marked inotropic effect", "Digitalis glycosides exert a mild inotropic effect"),
    "baroreceptor desensitization (text: sensitization)": (
        DIGOXIN, lambda x: cls("Rate slowing", [1], [(x, [1])] + RATE_KIDS),
        "Vagal tone is increased reflexly via baroreceptor desensitization",
        "Vagal tone is increased reflexly via baroreceptor sensitization"),
    "ineffective in mice lacking AMPK (text: effective)": (
        METFORMIN, lambda x: cls("Note", [2], [(x, [2]), ("AMPK-independent mechanisms have been proposed", [2])]),
        "Metformin remains ineffective in mice lacking AMPK", "Metformin remains effective in mice lacking AMPK"),
    "AMPK-dependent mechanisms (text: AMPK-independent)": (
        METFORMIN, lambda x: cls("Note", [2], [(x, [2]), ("Metformin remains effective in mice lacking AMPK", [2])]),
        "AMPK-dependent mechanisms have been proposed", "AMPK-independent mechanisms have been proposed"),
    # ---- dropped negation
    "cause insulin release (text: does not stimulate β cells or cause insulin release)": (
        METFORMIN, lambda x: cls(MET_LEAD, [1], [(x, [1])] + MET_KIDS),
        "Cause insulin release", "It does not stimulate pancreatic β cells or cause insulin release"),
    "reversed by atropine (text: not reversed, no bracket)": (
        DIGOXIN, lambda x: cls("Rate slowing", [1], [(x, [1]), ("Heart rate is decreased", [1]),
                                                     ("Vagal tone is increased reflexly", [1])]),
        "Direct depressant action on SA and A-V nodes reversed by atropine",
        "Direct depressant action on SA and A-V nodes not reversed by atropine"),
    # ---- numbers moved to another item
    "Stage 2 = two or more autoantibodies (text: Stage 1 = ...; Stage 2 = ...)": (
        T1D, lambda x: stages(x, "v1"),
        "Stage 2 = two or more islet autoantibodies with normoglycemia",
        "Stage 1 = two or more islet autoantibodies with normoglycemia"),
    "Stage 2: two or more ... (text: stage 1 is defined by two or more ..., stage 2 by ...)": (
        T1D_R3, lambda x: stages(x, "r3"),
        "Stage 2: two or more islet cell autoantibodies with normoglycemia",
        "Stage 1: two or more islet cell autoantibodies with normoglycemia"),
    "Stage 2 with no count (text: stage 1 ... with normoglycemia, stage 2 by ...)": (
        T1D_R3, lambda x: stages(x, "r3"),
        "Stage 2: islet cell autoantibodies with normoglycemia", "Stage 1: islet cell autoantibodies with normoglycemia"),
    "blocks β3 with weak β1 (text: blocks β1 and β2 with weak β3)": (
        BETA_BLOCKERS, lambda x: cls("Additional points", [3], [(x, [3]), ("Propranolol is also an inverse agonist", [3]),
                                                                 ("All β blockers are competitive antagonists", [3])]),
        "Propranolol blocks β3 with weak β1 activity", "Propranolol blocks β1 and β2 with weak β3 activity"),
    # ---- a word borrowed from the other section
    "penicillins inhibit ribosomal protein synthesis": (
        COMPARISON, lambda x: cls("Penicillins (β-lactams)", [1], [(x, [1]), ("Interfere with bacterial cell wall synthesis", [1]),
                                                                    ("Specifically inhibit transpeptidases", [1])]),
        "Penicillins inhibit ribosomal protein synthesis",
        "Blocking cross-linking prevents the rigid cell wall structure from forming"),
    "aminoglycosides inhibit cell wall synthesis": (
        COMPARISON, lambda x: cls("Aminoglycosides", [4], [(x, [4])] + AMINO_KIDS),
        "Aminoglycosides inhibit cell wall synthesis", "Binding to ribosomes to inhibit protein synthesis"),
}


@pytest.mark.parametrize("case", list(BOXES))
def test_bad_box_declines(case):
    answer, build, bad, _good = BOXES[case]
    assert bad not in node_labels(run(answer, build(bad))), f"drew {bad!r}"


@pytest.mark.parametrize("case", list(BOXES))
def test_control_box_still_draws(case):
    answer, build, _bad, good = BOXES[case]
    res = run(answer, build(good))
    assert good in node_labels(res), res.notes


# ---------------------------------------------------------------- arrows: reversed causation, contradicted direction

def test_increases_onto_atp_declines():
    """"a weak inhibitor of mitochondrial respiration, increasing intracellular AMP and reducing ATP"."""
    res = run(METFORMIN, g("sequence", [("a", "Weak inhibitor of mitochondrial respiration", [2]), ("b", "Intracellular AMP", [2]),
                                        ("c", "ATP", [2])],
                           [("a", "b", "increases", [2]), ("a", "c", "increases", [2])]))
    assert ("Weak inhibitor of mitochondrial respiration", "ATP") not in edge_labels(res)


def test_ampk_activation_before_respiration_declines():
    """AMPK activation is "an indirect consequence of interference with cellular respiration": the arrow is reversed."""
    res = run(METFORMIN, g("sequence", [("a", "Activation of AMP-dependent protein kinase (AMPK)", [1]),
                                        ("b", "Interference with cellular respiration", [1]),
                                        ("c", "Lowering of intracellular ATP", [1])],
                           [("a", "b", "leads to", [1]), ("b", "c", "leads to", [1])]))
    assert ("Activation of AMP-dependent protein kinase (AMPK)", "Interference with cellular respiration") \
        not in edge_labels(res)


def test_vagal_tone_causing_improved_circulation_declines():
    """"improved circulation restores diminished vagal tone": the cause is the circulation, not the vagal tone."""
    res = run(DIGOXIN, g("sequence", [("a", "Diminished vagal tone", [1]), ("b", "Improved circulation", [1]),
                                      ("c", "Heart rate is decreased", [1])],
                         [("a", "b", "causes", [1]), ("b", "c", "leads to", [1])]))
    assert ("Diminished vagal tone", "Improved circulation") not in edge_labels(res)


def test_misreading_before_codon_distortion_declines():
    """"binding at the 30S-50S juncture distorts mRNA codon recognition, causing misreading"."""
    res = run(COMPARISON, g("sequence", [("a", "Misreading and abnormal peptides", [4, 6]),
                                         ("b", "Distorts mRNA codon recognition", [4, 6]),
                                         ("c", "Binding at the 30S–50S juncture", [4, 6])],
                            [("a", "b", "causes", [4, 6]), ("c", "b", "causes", [4, 6])]))
    assert ("Misreading and abnormal peptides", "Distorts mRNA codon recognition") not in edge_labels(res)


def test_insulin_deficiency_before_destruction_declines():
    """"progressive destruction of islet β cells leads to absolute insulin deficiency"."""
    res = run(T1D, g("sequence", [("a", "Absolute insulin deficiency", [1]),
                                  ("b", "Progressive destruction of islet β cells", [1]), ("c", "Type 1 diabetes", [1])],
                     [("a", "b", "leads to", [1]), ("c", "a", "causes", [1])]))
    assert ("Absolute insulin deficiency", "Progressive destruction of islet β cells") not in edge_labels(res)


def test_forward_arrows_control_still_draw():
    res = run(T1D, g("sequence", [("a", "Progressive destruction of islet β cells", [1]),
                                  ("b", "Absolute insulin deficiency", [1]), ("c", "Type 1 diabetes", [1])],
                     [("a", "b", "leads to", [1]), ("c", "a", "", [1])]))
    assert ("Progressive destruction of islet β cells", "Absolute insulin deficiency") in edge_labels(res), res.notes
