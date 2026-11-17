"""R1 Flowchart red team, round 3 (PRD 4.R1 D-1/D-2, cite-or-decline).

Every BAD case below is an adversarial graph that api.diagram_validate.validate ACCEPTED on 2026-11-17 (HEAD 82a05c6)
against an answer streamed live from mentor.medevolv.in the same day (DIGOXIN, T1D, COMPARISON; verbatim). Each draws
a box whose words are in its cited sentence but whose MEANING is not: a flipped quantity ("less" for "more"), a
direction word the text does not put on that object, a dropped negation, a number borrowed from elsewhere in the
sentence, or an object borrowed from another section. Plain asserts, not xfail: the validator must be fixed until each
bad box is declined ("declined" = the whole diagram declines OR the bad box is absent from the accepted graph). The
CONTROL cases pass today and must keep passing, so a fix cannot simply decline everything.
"""
from tests.test_diagram_redteam2 import assert_box_declined, g, node_labels, run

# ---------------------------------------------------------------- real answers (live, 2026-11-17)

DIGOXIN = """Digoxin acts on the heart through several mechanisms:

- **Positive inotropic action:** Digitalis has direct effects on myocardial contractility, causing a dose-dependent increase in force of contraction, especially in the failing heart, which is exquisitely sensitive. Velocity of tension development increases and higher peak tension is generated; systole is shortened and diastole prolonged. The digitalized failing heart regains some capacity to contract more forcefully against increased resistance to ejection, with more complete emptying of dilated ventricles, increased cardiac output and reduced end-diastolic volume [1].
- **Electrophysiological and neural effects:** It has a vagomimetic action, reflex effects from altered haemodynamics, and direct CNS effects altering sympathetic activity [1]. It increases vagal tone reflexly via baroreceptor sensitization and vagal centre stimulation, and has an extravagal direct depressant action on SA and A-V nodes (not reversed by atropine), producing bradycardia [1].
- **Neurohormonal effects:** Digitalis glycosides attenuate carotid sinus baroreceptor activity and are sympatho-inhibitory, decreasing serum norepinephrine, plasma renin and possibly aldosterone levels [2].

The sources do not describe the molecular/cellular basis of the inotropic effect (e.g., ion transport or contractile protein mechanisms)."""

T1D = """Type 1 diabetes (T1D) is an autoimmune disease in which progressive destruction of islet β cells leads to absolute insulin deficiency [1]. Islet destruction is caused primarily by immune effector cells reacting against endogenous β-cell antigens, and the disease stems from a failure of self-tolerance in T cells [1][3]. Circulating autoantibodies to islet cell antigens (including insulin) are often detected in affected patients [1].

Pathogenesis involves an interplay of genetic and environmental factors [3]. Epidemiologic studies show higher concordance rates in monozygotic versus dizygotic twins, supporting genetic susceptibility [3]. A proposed sequence includes genetic susceptibility to immune dysfunction, inflammatory cell infiltration of the islet (insulitis), antibody-mediated β-cell destruction, and autoantibodies present in blood [2]. A temporal model describes a genetic predisposition followed by an environmental trigger that initiates an autoimmune process, with development of islet autoantibodies and gradual decline in β-cell function and mass; stage 1 is defined by two or more islet cell autoantibodies with normoglycemia, stage 2 by continued autoimmunity with dysglycemia, and stage 3 by hyperglycemia meeting diagnostic criteria for diabetes [6].

Clinically, T1D most commonly develops in childhood, becomes manifest at puberty, and progresses with age, though it can develop at any age [3]. Patients present when progressive β-cell destruction has crossed a threshold at which adequate insulin secretion and normal blood glucose levels can no longer be sustained; high glucose levels may then be toxic to remaining β cells, so profound insulin deficiency rapidly ensues [4]. Most patients require insulin for survival; without insulin, serious metabolic complications such as ketoacidosis and coma may develop [3]. Latent autoimmune diabetes in adults (LADA) is a slowly progressive form of T1D occurring in adults, distinguished from T2D by the presence of one or more diabetes autoantibodies [3].

The sources do not cover the detailed molecular mechanisms of β-cell antigen presentation or specific environmental triggers."""

COMPARISON = """**Penicillins (β-lactams)** — inhibit bacterial cell wall synthesis. They block the transpeptidases (penicillin-binding proteins, PBPs) that cleave the terminal D-alanine of peptide chains and cross-link peptidoglycan strands, so cross-linking fails and the cell wall loses its stability and rigidity [1]. They are grouped among cell-wall synthesis inhibitors [3].

**Aminoglycosides** — inhibit protein synthesis after a two-step entry: diffusion through porin channels and carrier-mediated, oxygen-dependent transport across the cytoplasmic membrane (energy-dependent phase I) [4]. Inside the cell, streptomycin binds 30S ribosomes while other aminoglycosides also bind 50S and the 30S–50S interface; they freeze initiation, prevent polysome formation, and cause misreading of the mRNA code, producing wrong amino acids or abnormal peptide lengths [4][6]. Their cidal action is attributed to secondary membrane damage with leakage of ions, amino acids and proteins [6]. They are bactericidal, with concentration-dependent killing and a long post-antibiotic effect [4][6].

**Key contrasts**
- Target: cell wall transpeptidation [1] vs. the bacterial ribosome (30S/50S) [4][5].
- Effect on protein synthesis: none described for penicillins [1] vs. direct inhibition plus codon misreading [4].
- Bactericidal basis: failure of peptidoglycan cross-linking [1] vs. ribosomal disruption plus membrane leakage [6].
- Synergism: cell-wall inhibitors such as β-lactams enhance aminoglycoside entry and act synergistically [4].

The sources do not compare the two classes on spectrum, resistance mechanisms, or pharmacokinetics beyond the points above."""


def inotropic(child):
    return g("classification",
             [("r", "Positive inotropic action", [1]), ("a", child, [1]),
              ("b", "Increased cardiac output", [1]), ("c", "Reduced end-diastolic volume", [1])],
             [("r", "a", "includes", [1]), ("r", "b", "includes", [1]), ("r", "c", "includes", [1])])


def neurohormonal(child):
    return g("classification",
             [("r", "Neurohormonal effects", [2]), ("a", child, [2]),
              ("b", "Sympatho-inhibitory", [2]), ("c", "Decreasing serum norepinephrine", [2])],
             [("r", "a", "includes", [2]), ("r", "b", "includes", [2]), ("r", "c", "includes", [2])])


def t1d_model(last):
    return g("sequence",
             [("a", "Genetic predisposition", [6]), ("b", "Environmental trigger", [6]), ("c", last, [6])],
             [("a", "b", "then", [6]), ("b", "c", "leads to", [6])])


def t1d_stages(first):
    return g("sequence",
             [("a", first, [6]), ("b", "Stage 2: continued autoimmunity with dysglycemia", [6]),
              ("c", "Stage 3: hyperglycemia meeting diagnostic criteria", [6])],
             [("a", "b", "then", [6]), ("b", "c", "then", [6])])


# ---------------------------------------------------------------- quantitative antonyms ("more"/"less" are STOP words)

def test_less_for_more_complete_emptying_declines():
    """Text: "more complete emptying of dilated ventricles". "less" and "more" are STOP words, so every content word
    matches and the flipped quantity is drawn under "Positive inotropic action"."""
    res = run(DIGOXIN, inotropic("Less complete emptying of dilated ventricles"))
    assert_box_declined(res, "Less complete emptying of dilated ventricles")


def test_contracts_less_forcefully_declines():
    """Text: "contract more forcefully against increased resistance to ejection"."""
    res = run(DIGOXIN, inotropic("Contracts less forcefully against increased resistance"))
    assert_box_declined(res, "Contracts less forcefully against increased resistance")


def test_inotropic_control_still_draws():
    res = run(DIGOXIN, inotropic("More complete emptying of dilated ventricles"))
    assert {"Positive inotropic action", "More complete emptying of dilated ventricles",
            "Increased cardiac output", "Reduced end-diastolic volume"} <= node_labels(res)


# ---------------------------------------------------------------- direction word the text does not put on the object

def test_raised_aldosterone_declines():
    """Text: "decreasing serum norepinephrine, plasma renin and possibly aldosterone levels". "decreasing" is more than
    DIR_WINDOW tokens before "aldosterone", so no polarity is read and "Raised" (absent from the sentence) passes on
    2 of 3 content words."""
    res = run(DIGOXIN, neurohormonal("Raised aldosterone levels"))
    assert_box_declined(res, "Raised aldosterone levels")


def test_raised_aldosterone_in_a_sequence_declines():
    res = run(DIGOXIN, g("sequence",
                         [("a", "Sympatho-inhibitory digitalis glycosides", [2]),
                          ("b", "Attenuated carotid sinus baroreceptor activity", [2]),
                          ("c", "Raised aldosterone levels", [2])],
                         [("a", "b", "leads to", [2]), ("a", "c", "leads to", [2])]))
    assert_box_declined(res, "Raised aldosterone levels")


def test_gradual_increase_in_beta_cell_function_declines():
    """Text: "gradual decline in β-cell function and mass". "declin" is in no DOWN_STEMS list, so the flip is not
    seen, and "increase" (absent from the sentence) passes on 3 of 4 content words."""
    res = run(T1D, t1d_model("Gradual increase in β-cell function and mass"))
    assert_box_declined(res, "Gradual increase in β-cell function and mass")


def test_neurohormonal_and_model_controls_still_draw():
    assert "Sympatho-inhibitory" in node_labels(run(DIGOXIN, neurohormonal("Plasma renin")))
    assert "Gradual decline in β-cell function and mass" in node_labels(
        run(T1D, t1d_model("Gradual decline in β-cell function and mass")))


# ---------------------------------------------------------------- dropped negation

def test_reversed_by_atropine_drops_the_answers_not_and_declines():
    """Text: "an extravagal direct depressant action on SA and A-V nodes (not reversed by atropine)". The box drops the
    "not". V4 only checks that a box's OWN negations are in the text, and the arrow's phrase window stops before the
    bracket, so the bracket's "not" is treated as an aside."""
    res = run(DIGOXIN, g("classification",
                         [("r", "Electrophysiological and neural effects", [1]),
                          ("a", "Extravagal direct depressant action reversed by atropine", [1]),
                          ("b", "Vagomimetic action", [1]), ("c", "Bradycardia", [1])],
                         [("r", "a", "includes", [1]), ("r", "b", "includes", [1]), ("r", "c", "includes", [1])]))
    assert_box_declined(res, "Extravagal direct depressant action reversed by atropine")


# ---------------------------------------------------------------- numbers borrowed from elsewhere in the sentence

def test_one_autoantibody_for_two_or_more_declines():
    """Text: "stage 1 is defined by two or more islet cell autoantibodies". "one" -> 1 is licensed by "stage 1" in the
    same sentence: exact_marks is checked against the whole sentence, not the box's own phrase."""
    res = run(T1D, t1d_stages("Stage 1: one islet autoantibody with normoglycemia"))
    assert_box_declined(res, "Stage 1: one islet autoantibody with normoglycemia")


def test_three_autoantibodies_for_two_or_more_declines():
    """"Three" -> 3 is licensed by "stage 3" in the same sentence."""
    res = run(T1D, t1d_stages("Three or more islet cell autoantibodies"))
    assert_box_declined(res, "Three or more islet cell autoantibodies")


def test_stage_control_still_draws():
    res = run(T1D, t1d_stages("Stage 1: two or more islet cell autoantibodies with normoglycemia"))
    assert "Stage 1: two or more islet cell autoantibodies with normoglycemia" in node_labels(res)


# ---------------------------------------------------------------- object borrowed from the compared item

def test_aminoglycosides_inhibit_cell_wall_synthesis_declines():
    """Text: aminoglycosides "inhibit protein synthesis"; cell wall synthesis is the PENICILLIN section. The box matches
    3 of 5 content words (aminoglycosides, inhibit, synthesis) of the aminoglycoside sentence, so the compared item's
    object is pasted onto the other item."""
    res = run(COMPARISON, g("classification",
                            [("r", "Aminoglycosides", [4]), ("a", "Aminoglycosides inhibit cell wall synthesis", [4]),
                             ("b", "Diffusion through porin channels", [4]), ("c", "Freeze initiation", [4])],
                            [("r", "a", "includes", [4]), ("r", "b", "includes", [4]), ("r", "c", "includes", [4])]))
    assert_box_declined(res, "Aminoglycosides inhibit cell wall synthesis")
