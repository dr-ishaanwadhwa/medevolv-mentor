"""R1 Flowchart, engineer round 3: each acceptance the validator gained this round, next to the adversarial graph that
must still decline (PRD 4.R1 D-1/D-2, cite-or-decline). Answers are trimmed from live mentor.medevolv.in answers
(2026-11-16)."""
from api import diagram_validate as V
from tests.test_diagram_redteam2 import (BETA_BLOCKERS, METFORMIN, assert_arrow_declined, assert_box_declined,
                                         edge_labels, g, node_labels, run)

# ---------------------------------------------------------------- a lead-in whose first clause carries a "not"

MET_LEAD = """Metformin's mechanism is not fully defined, but the key features are:

- **Hepatic gluconeogenesis suppression** — the major action lowering blood glucose; it reduces hepatic glucose production [1][2].
- **AMPK activation** — considered crucial in mediating its actions [1].
- **Retarded intestinal absorption** of glucose, other hexoses, amino acids and vitamin B12 [1]."""


def test_lead_in_negation_about_another_clause_does_not_block_its_list():
    """"... is not fully defined, but the key features are:": the "not" belongs to the first clause; the list is
    introduced by "the key features are", so the lead -> item arrows are stated."""
    res = run(MET_LEAD, g("classification",
                          [("r", "Key features", [1]), ("a", "Hepatic gluconeogenesis suppression", [1]),
                           ("b", "AMPK activation", [1]), ("c", "Retarded intestinal absorption", [1])],
                          [("r", "a", "includes", [1]), ("r", "b", "includes", [1]), ("r", "c", "includes", [1])]))
    assert {("Key features", "AMPK activation"), ("Key features", "Retarded intestinal absorption")} <= edge_labels(res)


def test_negation_in_the_clause_that_introduces_the_list_still_blocks():
    ans = MET_LEAD.replace("Metformin's mechanism is not fully defined, but the key features are:",
                           "Metformin is well studied, but the following are not its key features:")
    res = run(ans, g("classification",
                     [("r", "Key features", [1]), ("a", "Hepatic gluconeogenesis suppression", [1]),
                      ("b", "AMPK activation", [1]), ("c", "Retarded intestinal absorption", [1])],
                     [("r", "a", "includes", [1]), ("r", "b", "includes", [1]), ("r", "c", "includes", [1])]))
    assert_arrow_declined(res, "Key features", "AMPK activation")


def test_bold_lead_with_a_dash_heads_its_clauses():
    """"- **Hepatic gluconeogenesis suppression** — ...; it reduces hepatic glucose production": the bold lead heads the
    later clause too (the "; it ..." clause does not need to point back)."""
    res = run(MET_LEAD, g("classification",
                          [("r", "Key features", [1]), ("a", "Hepatic gluconeogenesis suppression", [1, 2]),
                           ("b", "Reduces hepatic glucose production", [1, 2])],
                          [("r", "a", "includes", [1]), ("a", "b", "includes", [1, 2])]))
    assert ("Hepatic gluconeogenesis suppression", "Reduces hepatic glucose production") in edge_labels(res)


def test_bold_lead_with_a_dash_does_not_lend_its_words_to_a_negated_clause():
    ans = "- **Penicillins** — do not inhibit protein synthesis; they inhibit cell wall synthesis [1].\n- Other [1]."
    res = run(ans, g("classification",
                     [("r", "Penicillins", [1]), ("a", "Inhibit protein synthesis", [1]),
                      ("b", "Inhibit cell wall synthesis", [1])],
                     [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert_arrow_declined(res, "Penicillins", "Inhibit protein synthesis")
    assert_box_declined(res, "Inhibit protein synthesis")


# ---------------------------------------------------------------- a negation inside an unrelated bracket

RATE = ("- **Rate slowing:** Heart rate is decreased, partly via restored vagal tone, and partly by extravagal actions "
        "(direct depressant action on SA and A-V nodes, not reversed by atropine) [1].\n"
        "- **Neurohormonal effects:** decreasing serum norepinephrine and plasma renin [2].")


def test_negation_inside_a_bracket_about_something_else_does_not_block():
    res = run(RATE, g("classification",
                      [("r", "Rate slowing", [1]), ("a", "Heart rate is decreased", [1]),
                       ("b", "Restored vagal tone", [1])],
                      [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert ("Rate slowing", "Heart rate is decreased") in edge_labels(res)


def test_negation_inside_the_bracket_that_holds_the_box_still_blocks():
    res = run(RATE, g("classification",
                      [("r", "Rate slowing", [1]), ("a", "Heart rate is decreased", [1]),
                       ("b", "Direct depressant action on SA and A-V nodes", [1])],
                      [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert_arrow_declined(res, "Rate slowing", "Direct depressant action on SA and A-V nodes")


def test_bracket_right_after_a_box_qualifies_that_box():
    ans = "- **Rate slowing:** Heart rate is decreased (not in patients with sinus rhythm), vagal tone is restored [1]."
    res = run(ans, g("classification",
                     [("r", "Rate slowing", [1]), ("a", "Heart rate is decreased", [1]),
                      ("b", "Vagal tone is restored", [1])],
                     [("r", "a", "includes", [1]), ("r", "b", "includes", [1])]))
    assert_arrow_declined(res, "Rate slowing", "Heart rate is decreased")


# ---------------------------------------------------------------- list order the answer announces as steps

SEQ = ("A proposed sequence includes genetic susceptibility to immune dysfunction, inflammatory cell infiltration of the "
       "islet (insulitis), antibody-mediated β-cell destruction, and autoantibodies present in blood [2].")


def _seq_graph(answer_lead=SEQ):
    return run(answer_lead, g("sequence",
                              [("a", "Genetic susceptibility to immune dysfunction", [2]),
                               ("b", "Inflammatory cell infiltration of the islet", [2]),
                               ("c", "Antibody-mediated β-cell destruction", [2])],
                              [("a", "b", "", [2]), ("b", "c", "", [2])]))


def test_list_the_answer_calls_a_sequence_is_ordered():
    assert {("Genetic susceptibility to immune dysfunction", "Inflammatory cell infiltration of the islet"),
            ("Inflammatory cell infiltration of the islet", "Antibody-mediated β-cell destruction")} \
        <= edge_labels(_seq_graph())


def test_same_list_as_features_is_not_a_chain():
    res = _seq_graph(SEQ.replace("A proposed sequence includes", "Associated features include"))
    assert_arrow_declined(res, "Genetic susceptibility to immune dysfunction",
                          "Inflammatory cell infiltration of the islet")


def test_announced_sequence_is_not_reversed():
    res = run(SEQ, g("sequence",
                     [("a", "Genetic susceptibility to immune dysfunction", [2]),
                      ("b", "Inflammatory cell infiltration of the islet", [2]),
                      ("c", "Antibody-mediated β-cell destruction", [2])],
                     [("b", "a", "", [2]), ("c", "b", "", [2])]))
    assert not res.ok


def test_two_step_entry_orders_its_two_steps():
    ans = ("Aminoglycosides inhibit protein synthesis after a two-step entry: diffusion through porin channels and "
           "carrier-mediated transport across the cytoplasmic membrane [4].")
    fwd = run(ans, g("sequence",
                     [("a", "Aminoglycosides inhibit protein synthesis", [4]),
                      ("b", "Diffusion through porin channels", [4]),
                      ("c", "Carrier-mediated transport across the cytoplasmic membrane", [4])],
                     [("b", "c", "", [4]), ("a", "b", "", [4])]))
    assert ("Diffusion through porin channels", "Carrier-mediated transport across the cytoplasmic membrane") \
        in edge_labels(fwd)
    rev = run(ans, g("sequence",
                     [("a", "Aminoglycosides inhibit protein synthesis", [4]),
                      ("b", "Diffusion through porin channels", [4]),
                      ("c", "Carrier-mediated transport across the cytoplasmic membrane", [4])],
                     [("c", "b", "", [4]), ("a", "c", "", [4])]))
    assert_arrow_declined(rev, "Carrier-mediated transport across the cytoplasmic membrane",
                          "Diffusion through porin channels")


# ---------------------------------------------------------------- participle consequence vs list of participles

def test_participle_after_the_source_is_its_consequence():
    ans = "Metformin acts as a weak inhibitor of mitochondrial respiration, increasing intracellular AMP and reducing ATP [2]."
    res = run(ans, g("sequence",
                     [("a", "Weak inhibitor of mitochondrial respiration", [2]), ("b", "Intracellular AMP", [2]),
                      ("c", "Reducing ATP", [2])],
                     [("a", "b", "increases", [2]), ("a", "c", "decreases", [2]), ("b", "c", "", [2])]))
    assert ("Weak inhibitor of mitochondrial respiration", "Intracellular AMP") in edge_labels(res)
    assert_arrow_declined(res, "Intracellular AMP", "Reducing ATP")      # "... AMP and reducing ATP": a second item


# ---------------------------------------------------------------- box-level checks, accepted forms

def test_spelled_number_and_greek_letter_that_the_sentence_has_are_kept():
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Third-generation beta blockers", [4]),
                                ("a", "Additional vasodilatory properties", [4]), ("b", "Nebivolol", [4])],
                               [("r", "a", "includes", [4]), ("a", "b", "includes", [4])]))
    assert {"Third-generation beta blockers", "Nebivolol"} <= node_labels(res)
    assert ("Additional vasodilatory properties", "Nebivolol") in edge_labels(res)


def test_box_from_the_clause_that_says_it_is_kept():
    res = run(BETA_BLOCKERS, g("classification",
                               [("r", "Additional points", [1, 2, 3]),
                                ("a", "Bucindolol have not shown survival benefit", [2]),
                                ("b", "Cardioselectivity is only relative", [1])],
                               [("r", "a", "includes", [2]), ("r", "b", "includes", [1])]))
    assert "Bucindolol have not shown survival benefit" in node_labels(res)


def test_exact_marks():
    assert V.exact_marks("Five terminal groups") == {"5"}
    assert V.exact_marks("Third-generation β blockers") == {"3", "g:beta"}
    assert V.exact_marks("beta1 and α2") >= {"g:alpha", "1", "2"}
    assert V.exact_marks("Both branches") == set()


def test_metformin_live_answer_key_features_hub():
    res = run(METFORMIN, g("classification",
                           [("r", "Key features described", [1]), ("a", "Hepatic gluconeogenesis suppression", [1]),
                            ("b", "AMPK activation", [1]), ("c", "Retarded intestinal absorption", [1])],
                           [("r", "a", "includes", [1]), ("r", "b", "includes", [1]), ("r", "c", "includes", [1])]))
    assert res.ok and len(res.graph["edges"]) == 3


# ---------------------------------------------------------------- tightenings found in the round-3 live audit

def test_arrow_reads_only_the_part_of_the_sentence_its_marker_cites():
    """"... the inferior ophthalmic vein at the inferior orbital fissure [3], and the inferior ophthalmic vein may pass
    through the superior orbital fissure ... [4]": an arrow citing [3] cannot borrow the fissure from the [4] part."""
    from tests.test_diagram_redteam2 import SOF
    res = run(SOF, g("classification",
                     [("f", "The superior orbital fissure transmits", [1]), ("t", "Trochlear nerve", [1]),
                      ("a", "Abducent nerve", [1]),
                      ("v", "Inferior ophthalmic vein at the inferior orbital fissure", [3])],
                     [("f", "t", "includes", [1]), ("f", "a", "includes", [1]), ("f", "v", "includes", [3])]))
    assert_arrow_declined(res, "The superior orbital fissure transmits",
                          "Inferior ophthalmic vein at the inferior orbital fissure")
    ok = run(SOF, g("classification",
                    [("f", "Superior orbital fissure", [1, 4]), ("t", "Trochlear nerve", [1]),
                     ("v", "Inferior ophthalmic vein", [4])],
                    [("f", "t", "includes", [1]), ("f", "v", "includes", [4])]))
    assert ("Superior orbital fissure", "Inferior ophthalmic vein") in edge_labels(ok)


def test_box_is_not_placed_by_words_it_shares_with_the_other_box():
    """"act in two steps: transport into the bacterial cell, then binding to ribosomes to inhibit protein synthesis":
    "Freeze initiation of protein synthesis" is not in this sentence; its only matches ("protein synthesis") belong to
    the source box."""
    ans = ("- Bactericidal; act in two steps: transport into the bacterial cell, then binding to ribosomes to inhibit "
           "protein synthesis [4].\n- Freeze initiation of protein synthesis and prevent polysome formation [4].")
    res = run(ans, g("sequence",
                     [("a", "Transport into the bacterial cell", [4]),
                      ("b", "Binding to ribosomes to inhibit protein synthesis", [4]),
                      ("c", "Freeze initiation of protein synthesis", [4])],
                     [("a", "b", "then", [4]), ("b", "c", "", [4])]))
    assert_arrow_declined(res, "Binding to ribosomes to inhibit protein synthesis", "Freeze initiation of protein synthesis")


def test_shown_verb_is_the_answers_word_between_the_boxes():
    ans = "Binding at the 30S-50S juncture distorts mRNA codon recognition → misreading of the code [4]."
    res = run(ans, g("sequence",
                     [("a", "Binding at the 30S-50S juncture", [4]), ("b", "Distorts mRNA codon recognition", [4]),
                      ("c", "Causing misreading of the code", [4])],
                     [("a", "b", "", [4]), ("b", "c", "causes", [4])]))
    shown = {(e["from"], e["to"]): e["label"] for e in res.graph["edges"]} if res.ok else {}
    assert "causes" not in shown.values()          # "causing" is the box's word, not the answer's
