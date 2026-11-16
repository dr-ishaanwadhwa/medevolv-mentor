"""R1 Flowchart red team, round 2 (PRD 4.R1 D-1/D-2, cite-or-decline).

Every BAD case below is an adversarial graph that api.diagram_validate.validate ACCEPTED on 2026-11-16 (HEAD db72c88)
against a real answer streamed from mentor.medevolv.in the same day (FACIAL, SOF, BETA_BLOCKERS, METFORMIN; COMPARISON
is round 1's live answer). Each draws a box or arrow the answer does not state. They are plain asserts, not xfail: the
validator must be fixed until each bad box/arrow is declined. "Declined" means the whole diagram declines OR the bad
box/arrow is absent from the accepted graph (dropped, never bridged). The CONTROL cases pass today and must keep
passing, so a fix cannot simply decline everything.
"""
from api import diagram_validate as V
from tests.test_diagram_redteam import COMPARISON

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

FACIAL = """The facial nerve [VII] gives off the following branches:

- **Within the temporal bone (facial canal):** the greater petrosal nerve (mainly preganglionic parasympathetic GVE fibers), the nerve to the stapedius, and the chorda tympani (taste SA fibers from the anterior two-thirds of the tongue and preganglionic GVE fibers to the submandibular ganglion) [6].
- **At the stylomastoid foramen:** the posterior auricular nerve, which supplies the occipital belly of occipitofrontalis and the posterior auricular muscle [1].
- **After the posterior auricular nerve:** a branch to the posterior belly of the digastric and the stylohyoid [1][3].
- **Within the parotid gland:** the main stem divides into upper (temporofacial) and lower (cervicofacial) branches, which may branch further or form the parotid plexus [1].
- **Five terminal groups emerging from the parotid gland** [1][5]:
  - Temporal branches — temple, forehead, supra-orbital area
  - Zygomatic branches — infra-orbital area, lateral nasal area, upper lip
  - Buccal branches — cheek, upper lip, corner of the mouth
  - Marginal mandibular branches — lower lip and chin
  - Cervical branches — platysma

The facial nerve also innervates the platysma overlying the anterior triangle [3]."""

SOF = """The superior orbital fissure transmits [1]:

- Superior and inferior branches of the oculomotor nerve [III]
- Trochlear nerve [IV]
- Abducent nerve [VI]
- Lacrimal, frontal, and nasociliary branches of the ophthalmic nerve [V1]
- Superior ophthalmic vein

The figure labels also show the inferior ophthalmic vein at the inferior orbital fissure [3], and the inferior ophthalmic vein may pass through the superior orbital fissure on its own to reach the cavernous sinus [4]."""

BETA_BLOCKERS = """β blockers are classified as follows:

**Nonselective (β1 and β2)**
- Without intrinsic sympathomimetic activity: propranolol, sotalol, timolol [3]
- With intrinsic sympathomimetic activity: pindolol [3]
- With additional α-blocking property: labetalol, carvedilol [3]

**Cardioselective (β1)**
- Metoprolol, atenolol, acebutolol, bisoprolol, esmolol, betaxolol, celiprolol, nebivolol [3]

Additional points:
- All β blockers are competitive antagonists; propranolol blocks β1 and β2 with weak β3 activity and is also an inverse agonist [3].
- Cardioselectivity is only relative and is lost at high doses [1].
- Partial agonistic (intrinsic sympathomimetic) activity is seen in pindolol, celiprolol, and acebutolol [1].
- In HFrEF, beta blocker use should ideally be restricted to carvedilol, bisoprolol, and metoprolol succinate, which have proven survival benefit; agents with intrinsic sympathomimetic activity (e.g., xamoterol) and bucindolol have not shown survival benefit [2].
- Third-generation beta blockers are cardioselective with additional vasodilatory properties (nebivolol) or combined α-receptor blockade (carvedilol) [4][5].

The sources do not provide a single unified classification scheme beyond the groupings above."""

METFORMIN = """Metformin's mechanism is incompletely defined, but the key features described are:

- **Hepatic gluconeogenesis suppression** — reduces hepatic glucose production/glucose output from the liver; this is the major action lowering blood glucose [1][2][3].
- **AMPK activation** — activation of AMP-dependent protein kinase (AMPK) is recognized as playing a crucial role; it appears to be an indirect consequence of interference with cellular respiration and lowering of intracellular ATP and other energy sources [1][2]. At the molecular level, metformin acts as a weak inhibitor of mitochondrial respiration, increasing intracellular AMP and reducing ATP, which affects flux through gluconeogenesis and activates AMPK [2]. However, metformin is still effective in mice lacking AMPK, and AMPK-independent mechanisms have been proposed [2].
- **Increased insulin-mediated glucose uptake/disposal** in skeletal muscle and fat, overcoming insulin resistance — leading to glycogen storage in skeletal muscle, reduced lipogenesis in adipose tissue and enhanced fatty acid oxidation [1][2].
- **Interference with the mitochondrial respiratory chain**, promoting peripheral glucose utilization through anaerobic glycolysis [1].
- **Retarded intestinal absorption** of glucose, other hexoses, amino acids and vitamin B12 [1]; effects on gut glucose uptake and utilisation are also described [2].
- It does **not** stimulate pancreatic β cells or cause insulin release, but the presence of insulin is essential for its action (not effective in pancreatectomized animals or type 1 diabetics) [1].

Note: the sources do not give a single precise, fully established molecular mechanism — all three major texts state the mechanism "has not been precisely defined"/"details are not clear" [1][2][3]."""


# ---------------------------------------------------------------- invented / reworded boxes (V4 is a bag of words)

def test_box_swapping_anterior_for_posterior_is_declined():
    """"taste SA fibers from the anterior two-thirds of the tongue": 3 of 4 words match, the one that differs is the
    meaning. Fix: a box word missing from its sentence must not be the antonym of a sentence word (anterior/posterior,
    superior/inferior, upper/lower, strong/weak, retained/lost, proven/not shown, selective/nonselective ...)."""
    res = run(FACIAL, g("pathway",
                        [("a", "Chorda tympani", [6]), ("b", "Taste from posterior two-thirds of tongue", [6]),
                         ("c", "Submandibular ganglion", [6])],
                        [("a", "b", "supplies", [6]), ("a", "c", "passes to", [6])]))
    assert_box_declined(res, "Taste from posterior two-thirds of tongue")


def test_spelled_number_not_in_the_answer_is_declined():
    """"Five terminal groups emerging from the parotid gland": the number check reads digits only, so "Six" passes.
    Fix: spelled cardinals/ordinals (one..twenty, first..tenth, "second-generation") are numbers too and must be in the
    supporting sentence (as a word or a digit)."""
    res = run(FACIAL, g("pathway",
                        [("p", "Six terminal groups emerging from parotid gland", [1]),
                         ("t", "Temporal branches", [1]), ("z", "Zygomatic branches", [1])],
                        [("p", "t", "branches to", [1]), ("p", "z", "branches to", [1])]))
    assert_box_declined(res, "Six terminal groups emerging from parotid gland")


def test_wrong_generation_ordinal_is_declined():
    """"Third-generation beta blockers are cardioselective ..." drawn as "Second-generation"."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Second-generation beta blockers", [4]), ("a", "Nebivolol", [4]),
                                ("b", "Carvedilol", [4])],
                               [("r", "a", "includes", [4]), ("r", "b", "includes", [4])]))
    assert_box_declined(res, "Second-generation beta blockers")


def test_strong_where_the_answer_says_weak_is_declined():
    """"propranolol blocks β1 and β2 with weak β3 activity": the box says strong."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Competitive antagonists", [3]), ("a", "Propranolol has strong β3 activity", [3]),
                                ("b", "Inverse agonist", [3])],
                               [("r", "a", "includes", [3]), ("r", "b", "includes", [3])]))
    assert_box_declined(res, "Propranolol has strong β3 activity")


def test_retained_where_the_answer_says_lost_is_declined():
    """"Cardioselectivity is only relative and is lost at high doses"."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Additional points", [1]), ("a", "Cardioselectivity retained at high doses", [1]),
                                ("b", "Partial agonistic activity in pindolol", [1])],
                               [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert_box_declined(res, "Cardioselectivity retained at high doses")


def test_greek_letter_is_part_of_the_box():
    """"It does not stimulate pancreatic β cells": tokens() drops Greek letters, so "α cells" == "β cells". Fix: keep
    α/β/γ/δ/κ/μ (as alpha/beta/...) as tokens and require them in the supporting sentence like numbers."""
    res = run(METFORMIN, g("classification",
                           [("r", "Key features of metformin mechanism", [1]),
                            ("a", "Does not stimulate pancreatic α cells", [1]),
                            ("b", "Retarded intestinal absorption of glucose", [1])],
                           [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert_box_declined(res, "Does not stimulate pancreatic α cells")


def test_box_that_drops_the_clauses_negation_is_declined():
    """"...metoprolol succinate, which have proven survival benefit; agents with ISA (e.g., xamoterol) and bucindolol
    have not shown survival benefit": the box blends both clauses and drops the "not"; its arrow then finds the first
    clause (no negation, no bucindolol) as a unit. Fix: V4 support per independent clause, with E3 negation counting
    on that clause; the classification arrow's unit must support the child by node_supported on that clause."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Additional points", [1, 2, 3]),
                                ("a", "Bucindolol has proven survival benefit", [2]),
                                ("b", "Cardioselectivity is only relative", [1])],
                               [("r", "a", "includes", [2]), ("r", "b", "includes", [1])]))
    assert_box_declined(res, "Bucindolol has proven survival benefit")


# ---------------------------------------------------------------- invented arrows

def test_items_of_one_list_are_not_linked():
    """"the greater petrosal nerve (...), the nerve to the stapedius, and the chorda tympani (taste SA fibers from the
    anterior two-thirds of the tongue ...)": both boxes are in one sentence, in order, so E1/E2 pass. Fix: a
    directional arrow needs a linking word BETWEEN the two boxes (the verb's synonym, "to", "into", "via", "→",
    "which", a step opener); boxes separated only by list separators (",", "and", "or", a parenthetical) are siblings."""
    res = run(FACIAL, g("pathway",
                        [("a", "Greater petrosal nerve", [6]), ("b", "Nerve to the stapedius", [6]),
                         ("c", "Anterior two-thirds of the tongue", [6])],
                        [("a", "b", "branches to", [6]), ("a", "c", "supplies", [6])]))
    assert_arrow_declined(res, "Greater petrosal nerve", "Anterior two-thirds of the tongue")
    assert_arrow_declined(res, "Greater petrosal nerve", "Nerve to the stapedius")


def test_sibling_consequences_are_not_a_chain():
    """"— leading to glycogen storage in skeletal muscle, reduced lipogenesis in adipose tissue and enhanced fatty acid
    oxidation": three parallel results, drawn as a chain labelled "leads to" (the "leading" sits BEFORE both boxes).
    Fix: the verb synonym that confirms an arrow must lie between the source and the target."""
    res = run(METFORMIN, g("sequence",
                           [("a", "Glycogen storage in skeletal muscle", [1]),
                            ("b", "Reduced lipogenesis in adipose tissue", [1]),
                            ("c", "Enhanced fatty acid oxidation", [1])],
                           [("a", "b", "leads to", [1]), ("b", "c", "leads to", [1])]))
    assert_arrow_declined(res, "Glycogen storage in skeletal muscle", "Reduced lipogenesis in adipose tissue")
    assert_arrow_declined(res, "Reduced lipogenesis in adipose tissue", "Enhanced fatty acid oxidation")


def test_locator_lead_is_not_the_source_of_a_branch():
    """"- **After the posterior auricular nerve:** a branch to the posterior belly of the digastric and the stylohyoid":
    the bold lead says WHERE the next branch of the facial nerve arises, not that the posterior auricular nerve gives it.
    Fix: a box supported only by the list context may be a directional SOURCE only when that context carries the
    verb's synonym ("gives off the following branches", "emerging from"), never a locator ("After", "Within", "At")."""
    res = run(FACIAL, g("pathway",
                        [("a", "Posterior auricular nerve", [1]), ("b", "Posterior belly of digastric", [1]),
                         ("c", "Stylohyoid", [1])],
                        [("a", "b", "supplies", [1]), ("a", "c", "supplies", [1])]))
    assert_arrow_declined(res, "Posterior auricular nerve", "Stylohyoid")
    assert_arrow_declined(res, "Posterior auricular nerve", "Posterior belly of digastric")


def test_classification_arrow_does_not_cross_clauses_of_a_contrast():
    """"Membrane: penicillins act at the membrane-located PBPs on wall assembly [1]; aminoglycosides secondarily disrupt
    membrane integrity ... [6]": _clauses_linked is skipped for classification, so "Penicillins includes
    Aminoglycosides" is drawn. Fix: run the clause check for every kind (or require a parent->child cue: ":", "such
    as", "e.g.", "includes", a parenthesis, or the item's heading)."""
    res = run(COMPARISON, g("classification",
                            [("p", "Penicillins", [1]), ("a", "Aminoglycosides", [1]),
                             ("m", "Membrane integrity disruption", [6])],
                            [("p", "a", "includes", [1]), ("a", "m", "includes", [6])]))
    assert_arrow_declined(res, "Penicillins", "Aminoglycosides")


def test_child_goes_under_its_own_parent_in_one_sentence():
    """"cardioselective with additional vasodilatory properties (nebivolol) or combined α-receptor blockade
    (carvedilol)": nebivolol is put under α-receptor blockade. Fix: a parenthesised child belongs to the phrase right
    before its parenthesis; reject a parent separated from the child by another coordinated phrase ("or", "and")."""
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Third-generation beta blockers", [4]), ("a", "Combined α-receptor blockade", [4]),
                                ("b", "Nebivolol", [4]), ("c", "Additional vasodilatory properties", [4])],
                               [("r", "a", "includes", [4]), ("r", "c", "includes", [4]),
                                ("a", "b", "includes", [4])]))
    assert_arrow_declined(res, "Combined α-receptor blockade", "Nebivolol")


def test_increases_is_not_borrowed_from_the_next_object():
    """"increasing intracellular AMP and reducing ATP, which affects flux through gluconeogenesis and activates AMPK":
    _target_polarity reads "activates" (3 tokens after "gluconeogenesis", across "and") as the direction on
    gluconeogenesis. The answer only says "affects" (and elsewhere "suppression"). Fix: a direction word after the
    object must not cross a coordinator ("and", "or", ","), and a direction verb arrow is kept only when the unit
    positively puts that direction on the target (polarity == want), not merely when no antonym is found."""
    res = run(METFORMIN, g("sequence",
                           [("a", "Weak inhibitor of mitochondrial respiration", [2]), ("b", "Intracellular AMP", [2]),
                            ("c", "Flux through gluconeogenesis", [2])],
                           [("a", "b", "increases", [2]), ("a", "c", "increases", [2])]))
    assert_arrow_declined(res, "Weak inhibitor of mitochondrial respiration", "Flux through gluconeogenesis")


def test_box_words_scattered_across_the_sentence_do_not_place_it():
    """"the inferior ophthalmic vein may pass through the superior orbital fissure on its own to reach the cavernous
    sinus [4]": "Superior ophthalmic vein" is matched by "superior" (of the fissure) + "ophthalmic vein" (the inferior
    one), so an arrow superior ophthalmic vein -> cavernous sinus is drawn that the answer never states. Fix: inside an
    edge's unit a box must match as a phrase (its matched words in order within len(label)+2 tokens), not a bag."""
    res = run(SOF, g("pathway",
                     [("f", "Superior orbital fissure", [1]), ("v", "Superior ophthalmic vein", [1, 4]),
                      ("c", "Cavernous sinus", [4])],
                     [("f", "v", "passes to", [1]), ("v", "c", "passes to", [4])]))
    assert_arrow_declined(res, "Superior ophthalmic vein", "Cavernous sinus")


# ---------------------------------------------------------------- controls: declined today, and must stay declined

def test_marker_not_in_the_answer_declines():
    res = V.validate(g("pathway",
                       [("f", "Superior orbital fissure", [7]), ("t", "Trochlear nerve", ["G1"]),
                        ("a", "Abducent nerve", [7])],
                       [("f", "t", "passes to", [7]), ("f", "a", "passes to", ["G1"])]),
                     answer_text=SOF, passage_ns=NS, fact_ns={1})
    assert not res.ok


def test_more_than_three_chains_declines():
    res = run(FACIAL, g("pathway",
                        [("a", "Posterior auricular nerve", [1]), ("a2", "Occipital belly of occipitofrontalis", [1]),
                         ("b", "Temporal branches", [1]), ("b2", "Temple", [1]),
                         ("c", "Cervical branches", [1]), ("c2", "Platysma", [1]),
                         ("d", "Marginal mandibular branches", [1]), ("d2", "Lower lip and chin", [1])],
                        [("a", "a2", "supplies", [1]), ("b", "b2", "supplies", [1]), ("c", "c2", "supplies", [1]),
                         ("d", "d2", "supplies", [1])]))
    assert not res.ok


def test_reversed_consequence_declines():
    """"it appears to be an indirect consequence of interference with cellular respiration and lowering of ATP"."""
    res = run(METFORMIN, g("sequence",
                           [("a", "AMPK activation", [1]), ("b", "Lowering of intracellular ATP", [1]),
                            ("c", "Interference with cellular respiration", [1])],
                           [("a", "b", "causes", [1]), ("a", "c", "causes", [1])]))
    assert_arrow_declined(res, "AMPK activation", "Lowering of intracellular ATP")


def test_lone_unsupported_box_is_not_drawn():
    res = run(SOF, g("pathway",
                     [("f", "Superior orbital fissure", [1]), ("t", "Trochlear nerve", [1]),
                      ("a", "Abducent nerve", [1]), ("x", "Optic canal", [1])],
                     [("f", "t", "passes to", [1]), ("f", "a", "passes to", [1])]))
    assert_box_declined(res, "Optic canal")


# ---------------------------------------------------------------- controls: accepted today, and must stay accepted

def test_fissure_transmits_its_listed_nerves():
    res = run(SOF, g("pathway",
                     [("f", "Superior orbital fissure", [1]), ("t", "Trochlear nerve", [1]),
                      ("a", "Abducent nerve", [1])],
                     [("f", "t", "passes to", [1]), ("f", "a", "passes to", [1])]))
    assert {("Superior orbital fissure", "Trochlear nerve"), ("Superior orbital fissure", "Abducent nerve")} \
        <= edge_labels(res)


def test_heading_includes_its_listed_drugs():
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Cardioselective (β1)", [3]), ("a", "Metoprolol", [3]), ("b", "Atenolol", [3])],
                               [("r", "a", "includes", [3]), ("r", "b", "includes", [3])]))
    assert {("Cardioselective (β1)", "Metoprolol"), ("Cardioselective (β1)", "Atenolol")} <= edge_labels(res)


def test_terminal_groups_emerge_from_the_parotid():
    res = run(FACIAL, g("pathway",
                        [("p", "Five terminal groups emerging from the parotid gland", [1]),
                         ("t", "Temporal branches", [1]), ("z", "Zygomatic branches", [1])],
                        [("p", "t", "branches to", [1]), ("p", "z", "branches to", [1])]))
    assert {("Five terminal groups emerging from the parotid gland", "Temporal branches")} <= edge_labels(res)
