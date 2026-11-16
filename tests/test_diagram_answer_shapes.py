"""R1 Flowchart validator on the answer shapes textbooks produce (PRD 4.R1, cite-or-decline).

Each acceptance has an adversarial twin that must still decline: list context never invents a parent, a narrower
evidence unit never hides a negation/antonym/reversal in the clause that holds the boxes, and nothing is bridged."""
import json

from api import diagram, diagram_validate as V


def run(answer, graph, ns=(1, 2, 3, 4, 5, 6)):
    return V.validate(graph, answer_text=answer, passage_ns=set(ns), fact_ns=set())


def g(kind, nodes, edges):
    """nodes: [(id, label, cites)], edges: [(from, to, label, cites)]"""
    return {"kind": kind, "title": None,
            "nodes": [{"id": i, "label": lb, "cites": list(c)} for i, lb, c in nodes],
            "edges": [{"from": a, "to": b, "label": lb, "cites": list(c)} for a, b, lb, c in edges]}


def labels(res):
    lab = {n["id"]: n["label"] for n in res.graph["nodes"]}
    return {(lab[e["from"]], lab[e["to"]]) for e in res.graph["edges"]}


# ---------------------------------------------------------------- a lead-in line introduces a list (facial nerve)

FACIAL = """The facial nerve [VII] gives off the following branches:
- **Greater petrosal nerve** - given off at the geniculate ganglion [6]
- **Nerve to stapedius** - arises in the facial canal [1]
- **Chorda tympani** - leaves the facial canal above the stylomastoid foramen [1]
- **Posterior auricular nerve** - arises just after the stylomastoid foramen [1]"""

FACIAL_G = g("classification",
             [("r", "Facial nerve [VII] branches", "1"), ("a", "Greater petrosal nerve", "6"),
              ("b", "Nerve to stapedius", "1"), ("c", "Chorda tympani", "1"), ("d", "Posterior auricular nerve", "1")],
             [("r", "a", "includes", "6"), ("r", "b", "includes", "1"), ("r", "c", "includes", "1"),
              ("r", "d", "includes", "1")])


def test_lead_in_parent_reaches_its_list_items():
    res = run(FACIAL, FACIAL_G)
    assert res.ok and len(res.graph["edges"]) == 4, res.notes
    assert res.graph["nodes"][0]["label"] == "Facial nerve [VII] branches"        # "[VII]" is text, not a marker


def test_negated_lead_in_still_declines():
    res = run(FACIAL.replace("gives off the following", "does not give off these"), FACIAL_G)
    assert not res.ok


def test_lead_in_never_crosses_into_another_list():
    two = ("Penicillin acts as follows:\n- Inhibits transpeptidases [1]\n- Blocks cross-linking of peptidoglycan [1]\n"
           "Gentamicin is different.\nGentamicin acts as follows:\n- Binds the 30S ribosome [2]\n- Causes misreading of mRNA [2]")
    graph = g("classification",
              [("p", "Penicillin", "1"), ("p1", "Inhibits transpeptidases", "1"), ("p2", "Blocks cross-linking", "1"),
               ("g", "Gentamicin", "2"), ("g1", "Binds the 30S ribosome", "2")],
              [("p", "p1", "", "1"), ("p", "p2", "", "1"), ("g", "g1", "", "2"), ("p", "g1", "", "2")])
    res = run(two, graph)
    assert res.ok and ("Penicillin", "Binds the 30S ribosome") not in labels(res)  # the invented bridge is dropped


# ---------------------------------------------------------------- a heading governs its bullets (beta blockers)

BB = """β blockers are classified as follows:
**Nonselective (β1 and β2)**
- Without intrinsic sympathomimetic activity: propranolol, sotalol, timolol [3]
- With intrinsic sympathomimetic activity: pindolol [3]
**Cardioselective (β1)**
- Metoprolol, atenolol, acebutolol, bisoprolol [3]"""


def bb_graph(wrong_parent=False):
    return g("classification",
             [("r", "β blockers", "3"), ("ns", "Nonselective (β1 and β2)", "3"), ("cs", "Cardioselective (β1)", "3"),
              ("a", "Without intrinsic sympathomimetic activity: propranolol", "3"), ("b", "Pindolol", "3"), ("c", "Metoprolol, atenolol", "3")],
             [("r", "ns", "includes", "3"), ("r", "cs", "includes", "3"), ("ns", "a", "includes", "3"),
              ("ns", "b", "includes", "3"), ("ns" if wrong_parent else "cs", "c", "includes", "3")])


def test_heading_boxes_and_their_items_are_supported():
    res = run(BB, bb_graph())
    assert res.ok and res.dropped == 0 and len(res.graph["edges"]) == 5, res.notes
    assert "Nonselective (β1 and β2)" in {n["label"] for n in res.graph["nodes"]}  # balanced parens survive


def test_item_under_the_wrong_heading_is_never_attached_to_it():
    res = run(BB, bb_graph(wrong_parent=True))           # metoprolol is not under "Nonselective": no arrow, no bridge
    assert not res.ok or ("Nonselective (β1 and β2)", "Metoprolol, atenolol") not in labels(res)
    assert not res.ok or "Metoprolol, atenolol" not in {n["label"] for n in res.graph["nodes"]}   # left out, not floating


def test_negated_heading_reaches_its_items():
    res = run(BB.replace("**Cardioselective (β1)**", "**Not cardioselective (β1)**"), bb_graph())
    assert not res.ok


def test_heading_words_never_top_up_an_item_box():
    """An item box must be supported by the item's own words, not by a blend with its heading's words."""
    a = ("**Aminoglycosides inhibit protein synthesis**\n- They bind the 30S ribosome [1]\n- Misreading of mRNA follows [1]\n"
         "- Membrane integrity is lost [1]")
    graph = g("sequence", [("a", "Bind the 30S ribosome", "1"), ("b", "Misreading of mRNA", "1"),
                           ("x", "Ribosome inhibit protein synthesis", "1")],
              [("a", "b", "", "1"), ("b", "x", "", "1")])
    res = run(a, graph)
    assert not res.ok or "Ribosome inhibit protein synthesis" not in {n["label"] for n in res.graph["nodes"]}


# ---------------------------------------------------------------- a cited lead-in cites its items (orbital fissure)

SOF = """The superior orbital fissure transmits [1]:

- Trochlear nerve [IV]
- Abducent nerve [VI]
- Lacrimal, frontal, and nasociliary branches of the ophthalmic nerve [V1]
- Superior ophthalmic vein

The inferior ophthalmic vein may also pass through the superior orbital fissure to the cavernous sinus [4]."""

SOF_G = g("classification",
          [("r", "Superior orbital fissure", "1"), ("a", "Trochlear nerve [IV]", "1"), ("b", "Abducent nerve [VI]", "1"),
           ("c", "Branches of the ophthalmic nerve [V1]", "1"), ("d", "Superior ophthalmic vein", "1")],
          [("r", x, "includes", "1") for x in "abcd"])


def test_items_inherit_the_marker_of_a_cited_lead_in():
    allowed = {("passage", 1), ("passage", 4)}
    assert sum(1 for s in V.sentences(SOF) if V.markers_in(s) & allowed) >= diagram.MIN_CITED_SENTENCES
    res = run(SOF, SOF_G)
    assert res.ok and res.dropped == 0, res.notes                              # "[V1]" keeps its "1": no new number


def test_uncited_lead_in_gives_its_items_nothing():
    a = SOF.replace("transmits [1]:", "transmits:")
    allowed = {("passage", 1), ("passage", 4)}
    assert sum(1 for s in V.sentences(a) if V.markers_in(s) & allowed) < diagram.MIN_CITED_SENTENCES


def test_invented_list_item_is_dropped_even_when_half_its_words_match():
    graph = json.loads(json.dumps(SOF_G))
    graph["nodes"].append({"id": "x", "label": "Optic nerve", "cites": ["1"]})      # "nerve" alone is in every item
    graph["edges"].append({"from": "r", "to": "x", "label": "includes", "cites": ["1"]})
    res = run(SOF, graph)
    assert "Optic nerve" not in {n["label"] for n in (res.graph or {"nodes": []})["nodes"]}


# ---------------------------------------------------------------- the evidence unit is the ";"-clause (pathogenesis)

T1D = ("Secretion can no longer be sustained; high glucose is toxic to remaining β cells, which leads to profound insulin "
       "deficiency [4]. Profound insulin deficiency causes hyperglycemia and ketoacidosis [4].")
T1D_G = g("sequence", [("a", "High glucose toxic to remaining β cells", "4"), ("b", "Profound insulin deficiency", "4"),
                       ("c", "Hyperglycemia and ketoacidosis", "4")],
          [("a", "b", "leads to", "4"), ("b", "c", "causes", "4")])


def test_negation_in_another_clause_does_not_block_the_arrow():
    res = run(T1D, T1D_G)
    assert res.ok and len(res.graph["edges"]) == 2, res.notes


def test_negation_in_the_clause_that_holds_the_boxes_still_declines():
    a = T1D.replace("which leads to profound", "which does not lead to profound")
    assert not run(a, T1D_G).ok


def test_synonym_in_another_clause_does_not_confirm_the_verb():
    a = ("Insulin decreases hepatic glucose output; glucagon raises ketone production [1]. "
         "Hepatic glucose output determines fasting glucose [1]. Fasting glucose is measured in the morning [1].")
    graph = g("sequence", [("a", "Insulin", "1"), ("b", "Hepatic glucose output", "1"), ("c", "Fasting glucose", "1")],
              [("a", "b", "increases", "1"), ("b", "c", "", "1")])
    assert not run(a, graph).ok                            # "raises" belongs to glucagon's clause: antonym, declines


# ---------------------------------------------------------------- order: backward connectives and reversed arrows

MET = ("Metformin interferes with the mitochondrial respiratory chain, lowering ATP and raising AMP [1]. "
       "AMPK activation is a consequence of lowering ATP and raising AMP [1]. "
       "AMPK activation suppresses hepatic gluconeogenesis [2].")


def met_graph(rev=False):
    e = ("c", "b", "activates", "1") if rev else ("b", "c", "activates", "1")
    return g("sequence", [("a", "Mitochondrial respiratory chain", "1"), ("b", "Lowering ATP, raising AMP", "1"),
                          ("c", "AMPK activation", "1"), ("d", "Suppresses hepatic gluconeogenesis", "2")],
             [("a", "b", "", "1"), e, ("c", "d", "", "2")])


def test_consequence_of_states_the_causal_direction():
    res = run(MET, met_graph())
    assert res.ok and ("Lowering ATP, raising AMP", "AMPK activation") in labels(res), res.notes


def test_arrow_against_consequence_of_is_never_drawn():
    res = run(MET, met_graph(rev=True))
    assert not res.ok or ("AMPK activation", "Lowering ATP, raising AMP") not in labels(res)
    s = V.parse_answer(MET)
    assert V._contradicted("activates", {"label": "AMPK activation"}, {"label": "Lowering ATP, raising AMP"},
                           V._carriers({("passage", 1)}, s), "sequence")


def test_because_is_never_drawn_effect_to_cause():
    a = ("Heart rate is decreased because improved circulation restores vagal tone [1]. "
         "This leads to slowing of the SA node [1]. A slower SA node lengthens diastole [1].")
    bad = g("sequence", [("a", "Heart rate decreased", "1"), ("b", "Improved circulation restores vagal tone", "1"),
                         ("c", "Slowing of the SA node", "1")], [("a", "b", "leads to", "1"), ("b", "c", "", "1")])
    assert not run(a, bad).ok
    good = g("sequence", [("b", "Improved circulation restores vagal tone", "1"), ("a", "Heart rate decreased", "1"),
                          ("c", "Slowing of the SA node", "1")], [("b", "a", "", "1"), ("b", "c", "", "1")])
    assert run(a, good).ok


def test_reversed_order_in_one_sentence_is_a_contradiction():
    s = V.parse_answer("Insulin deficiency leads to hyperglycaemia [1].")
    cs = V._carriers({("passage", 1)}, s)
    assert V._contradicted("", {"label": "Hyperglycaemia"}, {"label": "Insulin deficiency"}, cs, "sequence")
    assert not V._contradicted("", {"label": "Insulin deficiency"}, {"label": "Hyperglycaemia"}, cs, "sequence")


# ---------------------------------------------------------------- cross-sentence steps only where the answer orders them

def test_bullets_of_a_features_list_are_not_steps():
    a = ("Key features include:\n- Activates AMPK [1]\n- Interferes with mitochondrial respiration [1]\n"
         "- Retards intestinal absorption of glucose [2]")
    graph = g("sequence", [("a", "Activates AMPK", "1"), ("b", "Interferes with mitochondrial respiration", "1"),
                           ("c", "Retards intestinal absorption of glucose", "2")],
              [("a", "b", "", "1"), ("b", "c", "", "2")])
    assert not run(a, graph).ok                            # list position is not a causal claim


def test_numbered_steps_and_step_openers_are_steps():
    numbered = "1. The drug enters the cell [1]\n2. It binds the ribosome [1]\n3. Protein synthesis stops [1]"
    graph = g("sequence", [("a", "Drug enters the cell", "1"), ("b", "Binds the ribosome", "1"),
                           ("c", "Protein synthesis stops", "1")], [("a", "b", "", "1"), ("b", "c", "", "1")])
    assert run(numbered, graph).ok
    opener = "The drug enters the cell [1]. This leads to binding of the ribosome [1]. Then protein synthesis stops [1]."
    assert run(opener, graph).ok


# ---------------------------------------------------------------- connectivity is checked once, after validation

def test_disconnected_reply_is_not_a_schema_error():
    graph = g("sequence", [("a", "Angiotensin II", "1"), ("b", "Aldosterone release", "1"),
                           ("c", "Sodium reabsorption", "1"), ("d", "Blood volume", "2")], [("a", "b", "", "1")])
    V.parse_graph(graph)                                   # no SchemaError: E4 runs in validate, as a decline


def test_unlinked_feature_box_is_left_out_not_bridged():
    a = ("Angiotensin II stimulates aldosterone release [1]. Aldosterone increases sodium reabsorption [1]. "
         "Sodium retention raises blood volume [2]. Angiotensin II is an octapeptide [2].")
    nodes = [("a", "Angiotensin II", "1"), ("b", "Aldosterone release", "1"), ("c", "Sodium reabsorption", "1"),
             ("d", "Blood volume", "2")]
    edges = [("a", "b", "activates", "1"), ("b", "c", "increases", "1"), ("c", "d", "increases", "2")]
    res = run(a, g("sequence", nodes + [("x", "Octapeptide", "2")], edges))
    assert res.ok and res.dropped == 1 and "Octapeptide" not in {n["label"] for n in res.graph["nodes"]}
    # a lone box whose arrow the answer contradicts is not quietly left out: the diagram declines
    bad = edges[:2] + [("d", "c", "increases", "2")]
    assert not run(a, g("sequence", nodes, bad)).ok
    # more lone boxes than the V6 ceiling allows: decline
    many = nodes + [("x", "Octapeptide", "2"), ("y", "Aldosterone", "1"), ("z", "Sodium retention", "2")]
    assert not run(a, g("sequence", many, edges[:1])).ok


def test_rules_version_is_part_of_the_cache_key(monkeypatch):
    k1 = diagram.cache_key("q", "a", [], [])
    monkeypatch.setattr(diagram, "RULES_VERSION", V.RULES_VERSION + 1)
    assert diagram.cache_key("q", "a", [], []) != k1


def test_classification_arrow_needs_more_than_one_generic_word():
    """'Cardiac effects' -> 'Neurohormonal effects' must not pass because both bullets say "effects"."""
    a = ("- **Cardiac effects:** Digitalis has direct effects on contractility [1].\n"
         "- **Neurohormonal effects:** Digitalis glycosides attenuate baroreceptor activity and have CNS effects [1].\n"
         "- **Rate slowing:** Heart rate is decreased [1].")
    graph = g("classification", [("a", "Cardiac effects", "1"), ("b", "Neurohormonal effects", "1"),
                                 ("c", "Attenuate baroreceptor activity", "1")],
              [("a", "b", "", "1"), ("b", "c", "", "1")])
    res = run(a, graph)
    assert not res.ok or ("Cardiac effects", "Neurohormonal effects") not in labels(res)
